"""
LedgerGuard Mock Enterprise ERP Portal (Server)
Simulates an enterprise Accounts Payable & Invoice Settlement web portal.
Features:
- Authentication & Session Cookies
- In-memory / persistent invoice state
- Action endpoints: Settle, Dispute, Reset
- Runtime 'Chaos Mode' for testing agent self-healing locator resilience
"""

import os
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Request, Response, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

app = FastAPI(title="LedgerGuard Mock Enterprise ERP", version="1.0.0")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

templates = Jinja2Templates(directory=TEMPLATES_DIR)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Mock Credentials
VALID_USERNAME = "ops_admin"
VALID_PASSWORD = "LedgerGuardSecure2026!"
AUTH_COOKIE_NAME = "erp_session_token"
AUTH_TOKEN_VALUE = "sess_mock_enterprise_ops_token_9901"

# Initial seed data
INITIAL_INVOICES = [
    {
        "id": "INV-2026-001",
        "vendor_id": "VEND-101",
        "vendor_name": "CloudScale Infrastructure Inc",
        "gross_amount": 450.00,
        "tax_amount": 0.00,
        "net_amount": 450.00,
        "currency": "USD",
        "due_date": "2026-10-15",
        "status": "Pending",
        "match_reference": None,
        "dispute_notes": None,
        "settled_at": None,
    },
    {
        "id": "INV-2026-002",
        "vendor_id": "VEND-102",
        "vendor_name": "Apex Logistics Global",
        "gross_amount": 2450.00,
        "tax_amount": 0.00,
        "net_amount": 2450.00,
        "currency": "USD",
        "due_date": "2026-10-16",
        "status": "Pending",
        "match_reference": None,
        "dispute_notes": None,
        "settled_at": None,
    },
    {
        "id": "INV-2026-003",
        "vendor_id": "VEND-103",
        "vendor_name": "CyberShield Security Ltd",
        "gross_amount": 910.00,
        "tax_amount": 0.00,
        "net_amount": 910.00,
        "currency": "USD",
        "due_date": "2026-10-17",
        "status": "Pending",
        "match_reference": None,
        "dispute_notes": None,
        "settled_at": None,
    },
    {
        "id": "INV-2026-004",
        "vendor_id": "VEND-104",
        "vendor_name": "OfficeTech Supplies Co",
        "gross_amount": 125.00,
        "tax_amount": 0.00,
        "net_amount": 125.00,
        "currency": "USD",
        "due_date": "2026-10-18",
        "status": "Pending",
        "match_reference": None,
        "dispute_notes": None,
        "settled_at": None,
    },
    {
        "id": "INV-2026-005",
        "vendor_id": "VEND-101",
        "vendor_name": "CloudScale Infrastructure Inc",
        "gross_amount": 380.00,
        "tax_amount": 0.00,
        "net_amount": 380.00,
        "currency": "USD",
        "due_date": "2026-10-19",
        "status": "Pending",
        "match_reference": None,
        "dispute_notes": None,
        "settled_at": None,
    },
]

# Database state & Chaos state
invoice_db: List[Dict[str, Any]] = [dict(inv) for inv in INITIAL_INVOICES]
dispute_tickets: List[Dict[str, Any]] = []
chaos_mode_enabled: bool = False

def get_authenticated_user(request: Request) -> Optional[str]:
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if token == AUTH_TOKEN_VALUE:
        return VALID_USERNAME
    return None

class SettleRequest(BaseModel):
    payout_id: str
    bank_reference: str
    reconciled_amount: float
    notes: Optional[str] = "Settled via LedgerGuard Autonomous Operator"

class DisputeRequest(BaseModel):
    reason: str
    expected_amount: float
    billed_amount: float
    discrepancy: float
    priority: str = "High"

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = get_authenticated_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "user": user,
            "invoices": invoice_db,
            "chaos_mode": chaos_mode_enabled,
        }
    )

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user = get_authenticated_user(request)
    if user:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": None}
    )

@app.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...)
):
    if username == VALID_USERNAME and password == VALID_PASSWORD:
        resp = RedirectResponse(url="/", status_code=302)
        resp.set_cookie(key=AUTH_COOKIE_NAME, value=AUTH_TOKEN_VALUE, httponly=True)
        return resp
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": "Invalid enterprise credentials. Please check username & password."}
    )

@app.get("/logout")
async def logout(response: Response):
    resp = RedirectResponse(url="/login", status_code=302)
    resp.delete_cookie(key=AUTH_COOKIE_NAME)
    return resp

# REST APIs for browser & agent interaction
@app.get("/api/invoices")
async def list_invoices(request: Request, vendor_id: Optional[str] = None):
    results = invoice_db
    if vendor_id:
        results = [inv for inv in results if inv["vendor_id"] == vendor_id]
    return JSONResponse(content={"invoices": results, "total": len(results)})

@app.get("/api/invoices/{invoice_id}")
async def get_invoice(invoice_id: str):
    for inv in invoice_db:
        if inv["id"] == invoice_id:
            return JSONResponse(content={"invoice": inv})
    raise HTTPException(status_code=404, detail="Invoice not found")

@app.post("/api/invoices/{invoice_id}/settle")
async def settle_invoice(invoice_id: str, payload: SettleRequest):
    for inv in invoice_db:
        if inv["id"] == invoice_id:
            inv["status"] = "Reconciled"
            inv["match_reference"] = payload.bank_reference
            inv["settled_at"] = "2026-10-10T12:00:00Z"
            inv["dispute_notes"] = payload.notes
            return JSONResponse(content={
                "success": True,
                "message": f"Invoice {invoice_id} successfully settled and marked Reconciled",
                "invoice": inv
            })
    raise HTTPException(status_code=404, detail="Invoice not found")

@app.post("/api/invoices/{invoice_id}/dispute")
async def dispute_invoice(invoice_id: str, payload: DisputeRequest):
    for inv in invoice_db:
        if inv["id"] == invoice_id:
            inv["status"] = "Disputed"
            inv["dispute_notes"] = f"Reason: {payload.reason} | Delta: ${payload.discrepancy:.2f}"
            ticket = {
                "ticket_id": f"DISP-{len(dispute_tickets)+101}",
                "invoice_id": invoice_id,
                "reason": payload.reason,
                "expected": payload.expected_amount,
                "billed": payload.billed_amount,
                "discrepancy": payload.discrepancy,
                "priority": payload.priority,
                "created_at": "2026-10-10T12:00:00Z"
            }
            dispute_tickets.append(ticket)
            return JSONResponse(content={
                "success": True,
                "message": f"Dispute ticket created for {invoice_id}",
                "ticket": ticket,
                "invoice": inv
            })
    raise HTTPException(status_code=404, detail="Invoice not found")

@app.post("/api/chaos/toggle")
async def toggle_chaos():
    global chaos_mode_enabled
    chaos_mode_enabled = not chaos_mode_enabled
    return JSONResponse(content={"chaos_mode": chaos_mode_enabled})

@app.get("/api/chaos/status")
async def chaos_status():
    return JSONResponse(content={"chaos_mode": chaos_mode_enabled})

@app.post("/api/reset")
async def reset_database():
    global invoice_db, dispute_tickets, chaos_mode_enabled
    invoice_db = [dict(inv) for inv in INITIAL_INVOICES]
    dispute_tickets = []
    chaos_mode_enabled = False
    return JSONResponse(content={"success": True, "message": "ERP Database restored to initial seed"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("erp_portal.server:app", host="127.0.0.1", port=8080, reload=True)
