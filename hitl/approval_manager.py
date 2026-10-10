"""
Human-in-the-Loop (HITL) Approval Store & Gate for LedgerGuard.
Manages persistent suspension and resumption checkpoints when SOP policies require human sign-off.
"""

import sqlite3
import os
import json
from decimal import Decimal
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from runtime.models import ApprovalRequest, TaskStatus

from contextlib import contextmanager

class HITLApprovalManager:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "hitl_approvals.db"
        )
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS approval_requests (
                    approval_id TEXT PRIMARY KEY,
                    task_id TEXT,
                    invoice_id TEXT,
                    payout_id TEXT,
                    vendor_name TEXT,
                    amount TEXT,
                    discrepancy TEXT,
                    policy_citation TEXT,
                    screenshot_path TEXT,
                    status TEXT,
                    operator_decision TEXT,
                    operator_notes TEXT,
                    created_at TEXT,
                    decided_at TEXT
                )
            """)
            conn.commit()

    def create_request(
        self,
        task_id: str,
        invoice_id: str,
        payout_id: str,
        vendor_name: str,
        amount: Decimal,
        discrepancy: Decimal,
        policy_citation: str,
        screenshot_path: Optional[str] = None
    ) -> ApprovalRequest:
        """Creates and persists an approval gate request."""
        approval_id = f"APPR-{datetime.now().strftime('%M%S')}-{invoice_id[-3:]}"
        req = ApprovalRequest(
            approval_id=approval_id,
            task_id=task_id,
            invoice_id=invoice_id,
            payout_id=payout_id,
            vendor_name=vendor_name,
            amount=amount,
            discrepancy=discrepancy,
            policy_citation=policy_citation,
            screenshot_path=screenshot_path,
            status=TaskStatus.WAITING_APPROVAL,
            created_at=datetime.now(timezone.utc).isoformat()
        )

        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO approval_requests (
                    approval_id, task_id, invoice_id, payout_id, vendor_name,
                    amount, discrepancy, policy_citation, screenshot_path,
                    status, operator_decision, operator_notes, created_at, decided_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                req.approval_id, req.task_id, req.invoice_id, req.payout_id, req.vendor_name,
                str(req.amount), str(req.discrepancy), req.policy_citation, req.screenshot_path,
                req.status.value, None, None, req.created_at, None
            ))
            conn.commit()

        return req

    def get_pending_requests(self) -> List[ApprovalRequest]:
        """Returns all approval requests waiting for human intervention."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM approval_requests WHERE status = ?",
                (TaskStatus.WAITING_APPROVAL.value,)
            )
            rows = cursor.fetchall()
            return [self._row_to_model(r) for r in rows]

    def get_all_requests(self) -> List[ApprovalRequest]:
        """Returns all approval requests."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM approval_requests ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [self._row_to_model(r) for r in rows]

    def decide(self, approval_id: str, decision: str, notes: Optional[str] = None) -> Optional[ApprovalRequest]:
        """Records the human operator's decision (APPROVED or REJECTED)."""
        new_status = TaskStatus.APPROVED if decision.upper() == "APPROVE" else TaskStatus.REJECTED
        decided_at = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            conn.execute("""
                UPDATE approval_requests
                SET status = ?, operator_decision = ?, operator_notes = ?, decided_at = ?
                WHERE approval_id = ?
            """, (new_status.value, decision.upper(), notes, decided_at, approval_id))
            conn.commit()

        return self.get_request(approval_id)

    def get_request(self, approval_id: str) -> Optional[ApprovalRequest]:
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM approval_requests WHERE approval_id = ?", (approval_id,))
            row = cursor.fetchone()
            return self._row_to_model(row) if row else None

    def reset(self):
        """Clears all approval requests for demo reset."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM approval_requests")
            conn.commit()

    @staticmethod
    def _row_to_model(row: sqlite3.Row) -> ApprovalRequest:
        return ApprovalRequest(
            approval_id=row["approval_id"],
            task_id=row["task_id"],
            invoice_id=row["invoice_id"],
            payout_id=row["payout_id"],
            vendor_name=row["vendor_name"],
            amount=Decimal(row["amount"]),
            discrepancy=Decimal(row["discrepancy"]),
            policy_citation=row["policy_citation"],
            screenshot_path=row["screenshot_path"],
            status=TaskStatus(row["status"]),
            operator_decision=row["operator_decision"],
            operator_notes=row["operator_notes"],
            created_at=row["created_at"],
            decided_at=row["decided_at"]
        )
