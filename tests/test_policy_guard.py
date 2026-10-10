import pytest
from decimal import Decimal
from runtime.models import BankTransaction, ERPInvoice, MatchStatus
from policy.guard import PolicyGuard

def test_tier_1_auto_approval():
    guard = PolicyGuard()
    payout = BankTransaction(
        payout_id="PO-001",
        bank_reference="TXN-1",
        vendor_id="VEND-101",
        vendor_name="CloudScale",
        amount=Decimal("450.00"),
        settlement_date="2026-10-06",
        payment_method="ACH",
        memo="Monthly hosting"
    )
    invoice = ERPInvoice(
        id="INV-001",
        vendor_id="VEND-101",
        vendor_name="CloudScale",
        gross_amount=Decimal("450.00"),
        tax_amount=Decimal("0.00"),
        net_amount=Decimal("450.00"),
        due_date="2026-10-15",
        status="Pending"
    )
    result = guard.evaluate(payout, invoice)
    assert result.match_status == MatchStatus.AUTO_RECONCILED
    assert result.requires_approval is False
    assert "SOP-FIN-001 §3" in result.reason

def test_tier_2_hitl_gate_for_large_payout():
    guard = PolicyGuard()
    payout = BankTransaction(
        payout_id="PO-002",
        bank_reference="TXN-2",
        vendor_id="VEND-102",
        vendor_name="Apex Logistics",
        amount=Decimal("2450.00"),
        settlement_date="2026-10-07",
        payment_method="WIRE",
        memo="Q3 Freight"
    )
    invoice = ERPInvoice(
        id="INV-002",
        vendor_id="VEND-102",
        vendor_name="Apex Logistics",
        gross_amount=Decimal("2450.00"),
        tax_amount=Decimal("0.00"),
        net_amount=Decimal("2450.00"),
        due_date="2026-10-16",
        status="Pending"
    )
    result = guard.evaluate(payout, invoice)
    assert result.match_status == MatchStatus.HITL_PENDING
    assert result.requires_approval is True
    assert "Tier 2" in result.policy_tier

def test_material_variance_dispute():
    guard = PolicyGuard()
    payout = BankTransaction(
        payout_id="PO-003",
        bank_reference="TXN-3",
        vendor_id="VEND-103",
        vendor_name="CyberShield",
        amount=Decimal("820.00"),
        settlement_date="2026-10-08",
        payment_method="ACH",
        memo="Renewal"
    )
    invoice = ERPInvoice(
        id="INV-003",
        vendor_id="VEND-103",
        vendor_name="CyberShield",
        gross_amount=Decimal("910.00"),
        tax_amount=Decimal("0.00"),
        net_amount=Decimal("910.00"),
        due_date="2026-10-17",
        status="Pending"
    )
    result = guard.evaluate(payout, invoice)
    assert result.match_status == MatchStatus.DISPUTED
    assert result.delta == Decimal("90.00")
    assert "Dispute ticket required" in result.reason

def test_rounding_variance_absorption():
    guard = PolicyGuard()
    payout = BankTransaction(
        payout_id="PO-004",
        bank_reference="TXN-4",
        vendor_id="VEND-104",
        vendor_name="OfficeTech",
        amount=Decimal("125.03"),
        settlement_date="2026-10-08",
        payment_method="ACH",
        memo="Supplies"
    )
    invoice = ERPInvoice(
        id="INV-004",
        vendor_id="VEND-104",
        vendor_name="OfficeTech",
        gross_amount=Decimal("125.00"),
        tax_amount=Decimal("0.00"),
        net_amount=Decimal("125.00"),
        due_date="2026-10-18",
        status="Pending"
    )
    result = guard.evaluate(payout, invoice)
    assert result.match_status == MatchStatus.AUTO_RECONCILED
    assert result.delta == Decimal("0.03")
    assert "9990-ROUNDING-VARIANCE" in result.reason
