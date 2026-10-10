"""
LedgerGuard Real-Time Operator Console (Server)
FastAPI application with WebSockets for real-time AI Employee telemetry,
HITL approval governance, and audit verification inspection.
"""

import os
import asyncio
import json
from decimal import Decimal
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from runtime.engine import LedgerGuardRuntime
from runtime.models import TaskStatus, StepPhase
from hitl.approval_manager import HITLApprovalManager
from audit.logger import AuditLogger

app = FastAPI(title="LedgerGuard Operator Console", version="1.0.0")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
ROOT_DIR = os.path.dirname(BASE_DIR)
ARTIFACTS_DIR = os.path.join(ROOT_DIR, "audit_artifacts")
SCREENSHOTS_DIR = os.path.join(ARTIFACTS_DIR, "screenshots")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()
hitl_manager = HITLApprovalManager()
audit_logger = AuditLogger(artifacts_dir=ARTIFACTS_DIR)

active_runtime: Optional[LedgerGuardRuntime] = None
current_run_task: Optional[asyncio.Task] = None

class RunRequest(BaseModel):
    goal: str = "Reconcile vendor payouts from last week's CSV against internal ERP portal, flag discrepancies, draft dispute tickets, and process undisputed batches under $1,000."
    auto_approve: bool = False
    headless: bool = True

class DecisionRequest(BaseModel):
    decision: str  # "APPROVE" or "REJECT"
    notes: Optional[str] = "Approved via LedgerGuard Operator Console"

@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = os.path.join(STATIC_DIR, "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    # Send initial snapshot
    try:
        pending = hitl_manager.get_pending_requests()
        await websocket.send_text(json.dumps({
            "type": "INITIAL_STATE",
            "pending_approvals_count": len(pending),
            "audit_records_count": len(audit_logger.records)
        }))
        while True:
            # Keep socket alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

def handle_agent_event(event_data: Dict[str, Any]):
    """Callback triggered by LedgerGuard runtime on each execution step."""
    # Schedule broadcast onto the asyncio event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(
                manager.broadcast({"type": "AGENT_EVENT", "payload": event_data}),
                loop
            )
    except Exception:
        pass

@app.post("/api/run")
async def start_reconciliation_run(req: RunRequest):
    global active_runtime, current_run_task

    # Check if a run is already active
    if active_runtime and active_runtime.status == TaskStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="A reconciliation run is already in progress.")

    csv_path = os.path.join(ROOT_DIR, "data_fixtures", "bank_payouts_oct2026.csv")

    active_runtime = LedgerGuardRuntime(
        base_url="http://127.0.0.1:8080",
        artifacts_dir=ARTIFACTS_DIR,
        event_callback=handle_agent_event
    )

    async def run_worker():
        try:
            await active_runtime.run(
                goal=req.goal,
                csv_path=csv_path,
                auto_resume_approvals=req.auto_approve,
                headless=req.headless
            )
        except Exception as e:
            print(f"[OperatorConsole] Run failed: {e}")
            active_runtime.emit_event(StepPhase.COMPLETE, f"Run encountered exception: {e}", {}, TaskStatus.FAILED)

    current_run_task = asyncio.create_task(run_worker())

    return JSONResponse(content={
        "success": True,
        "message": "Autonomous reconciliation run initiated.",
        "task_id": active_runtime.task_id
    })

@app.get("/api/status")
async def get_system_status():
    pending_approvals = hitl_manager.get_pending_requests()
    all_approvals = hitl_manager.get_all_requests()
    audit_valid = audit_logger.verify_integrity()

    return JSONResponse(content={
        "status": active_runtime.status.value if active_runtime else "IDLE",
        "pending_approvals": [a.model_dump() for a in pending_approvals],
        "all_approvals": [a.model_dump() for a in all_approvals],
        "audit_count": len(audit_logger.records),
        "audit_integrity": audit_valid,
        "verification": active_runtime.verification_result.model_dump() if active_runtime and active_runtime.verification_result else None
    })

@app.get("/api/approvals")
async def list_approvals():
    return JSONResponse(content={
        "pending": [a.model_dump() for a in hitl_manager.get_pending_requests()],
        "all": [a.model_dump() for a in hitl_manager.get_all_requests()]
    })

@app.post("/api/approvals/{approval_id}/decision")
async def submit_approval_decision(approval_id: str, payload: DecisionRequest):
    req = hitl_manager.decide(approval_id, payload.decision, payload.notes)
    if not req:
        raise HTTPException(status_code=404, detail="Approval request not found.")

    # Broadcast event
    await manager.broadcast({
        "type": "APPROVAL_DECIDED",
        "payload": req.model_dump()
    })

    return JSONResponse(content={"success": True, "approval": req.model_dump()})

@app.get("/api/evidence/{filename}")
async def get_evidence_file(filename: str):
    file_path = os.path.join(SCREENSHOTS_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Evidence screenshot not found.")
    return FileResponse(file_path)

@app.get("/api/report")
async def get_latest_report():
    report_path = os.path.join(ARTIFACTS_DIR, "reconciliation_audit_report.html")
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Audit report not generated yet.")
    return FileResponse(report_path)

@app.post("/api/reset")
async def reset_all():
    hitl_manager.reset()
    return JSONResponse(content={"success": True, "message": "HITL store reset."})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web_console.server:app", host="127.0.0.1", port=8500, reload=True)
