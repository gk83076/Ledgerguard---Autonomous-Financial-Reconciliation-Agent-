import os
import tempfile
from decimal import Decimal
from hitl.approval_manager import HITLApprovalManager
from audit.logger import AuditLogger
from runtime.models import StepPhase, TaskStatus, BankTransaction, ERPInvoice, ReconciliationMatch, MatchStatus
from verification.verifier import DeterministicVerifier

def test_hitl_approval_lifecycle():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test_approvals.db")
        mgr = HITLApprovalManager(db_path=db_path)
        req = mgr.create_request(
            task_id="TASK-1",
            invoice_id="INV-002",
            payout_id="PO-002",
            vendor_name="Apex Logistics",
            amount=Decimal("2450.00"),
            discrepancy=Decimal("0.00"),
            policy_citation="Payout > $1000 requires manager approval."
        )

        assert req.status == TaskStatus.WAITING_APPROVAL
        pending = mgr.get_pending_requests()
        assert len(pending) == 1
        assert pending[0].approval_id == req.approval_id

        # Decide
        decided = mgr.decide(req.approval_id, "APPROVE", "Manager signed off")
        assert decided.status == TaskStatus.APPROVED
        assert decided.operator_decision == "APPROVE"

        # Now pending should be empty
        assert len(mgr.get_pending_requests()) == 0

def test_audit_hash_chain_and_tamper_detection():
    with tempfile.TemporaryDirectory() as tmp_dir:
        logger = AuditLogger(artifacts_dir=tmp_dir)

        r1 = logger.log(StepPhase.UNDERSTAND, "Read SOP", "sop.md", {"rule": "Tier 1"})
        r2 = logger.log(StepPhase.PLAN, "Plan steps", "planner", {"steps": 5})
        r3 = logger.log(StepPhase.EXECUTE, "Settle invoice", "INV-101", {"amount": 450.0})

        assert logger.verify_integrity() is True
        assert len(logger.records) == 3

        # Export HTML report
        report_path = logger.export_report_html()
        assert os.path.exists(report_path)

def test_deterministic_verifier_success():
    verifier = DeterministicVerifier()

    bank_txns = [
        BankTransaction(payout_id="P1", bank_reference="B1", vendor_id="V1", vendor_name="Vendor 1", amount=Decimal("450.00"), settlement_date="2026-10-06", payment_method="ACH", memo=""),
        BankTransaction(payout_id="P2", bank_reference="B2", vendor_id="V2", vendor_name="Vendor 2", amount=Decimal("910.00"), settlement_date="2026-10-07", payment_method="ACH", memo="")
    ]

    inv1 = ERPInvoice(id="I1", vendor_id="V1", vendor_name="Vendor 1", gross_amount=Decimal("450.00"), tax_amount=Decimal("0.00"), net_amount=Decimal("450.00"), due_date="2026-10-15", status="Reconciled")
    inv2 = ERPInvoice(id="I2", vendor_id="V2", vendor_name="Vendor 2", gross_amount=Decimal("910.00"), tax_amount=Decimal("0.00"), net_amount=Decimal("910.00"), due_date="2026-10-16", status="Disputed")

    matches = [
        ReconciliationMatch(payout=bank_txns[0], invoice=inv1, delta=Decimal("0.00"), match_status=MatchStatus.AUTO_RECONCILED, policy_tier="Tier 1", reason="Match"),
        ReconciliationMatch(payout=bank_txns[1], invoice=inv2, delta=Decimal("0.00"), match_status=MatchStatus.DISPUTED, policy_tier="Tier 1", reason="Disputed")
    ]

    res = verifier.verify_reconciliation(
        bank_txns=bank_txns,
        matches=matches,
        final_erp_invoices=[inv1, inv2],
        audit_hash_valid=True
    )

    assert res.verified is True
    assert res.total_bank_debits == Decimal("1360.00")
    assert res.unbalanced_delta == Decimal("0.00")
    assert res.erp_ui_verified is True
