import os
from decimal import Decimal
from tools.file_tool import FileIngestionTool
from runtime.reconciliation import ReconciliationEngine
from runtime.models import ERPInvoice, MatchStatus

def test_parse_bank_csv():
    tool = FileIngestionTool()
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data_fixtures", "bank_payouts_oct2026.csv")
    txns = tool.parse_bank_csv(csv_path)
    assert len(txns) == 5
    assert txns[0].amount == Decimal("450.00")
    assert txns[1].amount == Decimal("2450.00")
    assert txns[2].amount == Decimal("820.00")
    assert txns[3].amount == Decimal("125.03")

def test_reconciliation_engine_batch():
    tool = FileIngestionTool()
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data_fixtures", "bank_payouts_oct2026.csv")
    txns = tool.parse_bank_csv(csv_path)

    engine = ReconciliationEngine()

    erp_invoices = [
        ERPInvoice(id="INV-2026-001", vendor_id="VEND-101", vendor_name="CloudScale", gross_amount=Decimal("450.00"), tax_amount=Decimal("0.00"), net_amount=Decimal("450.00"), due_date="2026-10-15", status="Pending"),
        ERPInvoice(id="INV-2026-002", vendor_id="VEND-102", vendor_name="Apex Logistics", gross_amount=Decimal("2450.00"), tax_amount=Decimal("0.00"), net_amount=Decimal("2450.00"), due_date="2026-10-16", status="Pending"),
        ERPInvoice(id="INV-2026-003", vendor_id="VEND-103", vendor_name="CyberShield", gross_amount=Decimal("910.00"), tax_amount=Decimal("0.00"), net_amount=Decimal("910.00"), due_date="2026-10-17", status="Pending"),
        ERPInvoice(id="INV-2026-004", vendor_id="VEND-104", vendor_name="OfficeTech", gross_amount=Decimal("125.00"), tax_amount=Decimal("0.00"), net_amount=Decimal("125.00"), due_date="2026-10-18", status="Pending"),
        ERPInvoice(id="INV-2026-005", vendor_id="VEND-101", vendor_name="CloudScale", gross_amount=Decimal("380.00"), tax_amount=Decimal("0.00"), net_amount=Decimal("380.00"), due_date="2026-10-19", status="Pending"),
    ]

    matches = engine.reconcile_batch(txns, erp_invoices)
    assert len(matches) == 5

    # Check classifications
    assert matches[0].match_status == MatchStatus.AUTO_RECONCILED
    assert matches[1].match_status == MatchStatus.HITL_PENDING
    assert matches[2].match_status == MatchStatus.DISPUTED
    assert matches[3].match_status == MatchStatus.AUTO_RECONCILED
    assert matches[4].match_status == MatchStatus.AUTO_RECONCILED
