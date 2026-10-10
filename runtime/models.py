"""
Core data models and schemas for LedgerGuard AI Employee Runtime.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, Field

class StepPhase(str, Enum):
    UNDERSTAND = "UNDERSTAND"
    PLAN = "PLAN"
    POLICY_CHECK = "POLICY_CHECK"
    EXECUTE = "EXECUTE"
    OBSERVE = "OBSERVE"
    ADAPT = "ADAPT"
    VERIFY = "VERIFY"
    COMPLETE = "COMPLETE"

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class MatchStatus(str, Enum):
    AUTO_RECONCILED = "AUTO_RECONCILED"
    HITL_PENDING = "HITL_PENDING"
    DISPUTED = "DISPUTED"
    UNRECOGNIZED = "UNRECOGNIZED"

class RiskTier(str, Enum):
    READ_ONLY = "READ_ONLY"
    MUTATING_LOW = "MUTATING_LOW"
    MUTATING_HIGH = "MUTATING_HIGH"

class BankTransaction(BaseModel):
    payout_id: str
    bank_reference: str
    vendor_id: str
    vendor_name: str
    amount: Decimal
    currency: str = "USD"
    settlement_date: str
    payment_method: str
    memo: str

class ERPInvoice(BaseModel):
    id: str
    vendor_id: str
    vendor_name: str
    gross_amount: Decimal
    tax_amount: Decimal
    net_amount: Decimal
    currency: str = "USD"
    due_date: str
    status: str
    match_reference: Optional[str] = None
    dispute_notes: Optional[str] = None
    settled_at: Optional[str] = None

class ReconciliationMatch(BaseModel):
    payout: BankTransaction
    invoice: Optional[ERPInvoice] = None
    delta: Decimal = Decimal("0.00")
    match_status: MatchStatus
    policy_tier: str
    reason: str
    requires_approval: bool = False
    dispute_reason: Optional[str] = None

class ApprovalRequest(BaseModel):
    approval_id: str
    task_id: str
    invoice_id: str
    payout_id: str
    vendor_name: str
    amount: Decimal
    discrepancy: Decimal
    policy_citation: str
    screenshot_path: Optional[str] = None
    status: TaskStatus = TaskStatus.WAITING_APPROVAL
    operator_decision: Optional[str] = None
    operator_notes: Optional[str] = None
    created_at: str
    decided_at: Optional[str] = None

class AuditRecord(BaseModel):
    step_number: int
    timestamp: str
    phase: StepPhase
    action: str
    actor: str  # "LedgerGuard Agent" or "Human Operator"
    target: str
    details: Dict[str, Any] = Field(default_factory=dict)
    screenshot: Optional[str] = None
    previous_hash: str
    current_hash: str

class VerificationResult(BaseModel):
    verified: bool
    total_bank_debits: Decimal
    total_settled_amount: Decimal
    total_disputed_amount: Decimal
    rounding_variance: Decimal
    unbalanced_delta: Decimal
    erp_ui_verified: bool
    invoices_verified_count: int
    audit_hash_verified: bool
    summary: str
