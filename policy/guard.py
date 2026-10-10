"""
Policy Engine & Permission Guard for LedgerGuard.
Evaluates transactions against Company SOP memory (finance_sop.md).
Enforces authorization thresholds, variance tolerances, and HITL gate requirements.
"""

import os
from decimal import Decimal
from typing import Dict, Any, Optional
from runtime.models import BankTransaction, ERPInvoice, MatchStatus, ReconciliationMatch

class PolicyGuard:
    def __init__(self, sop_path: Optional[str] = None):
        self.sop_path = sop_path or os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "company_memory",
            "finance_sop.md"
        )
        self.tier_1_max = Decimal("1000.00")
        self.tier_2_max = Decimal("10000.00")
        self.rounding_tolerance = Decimal("0.05")
        self.sop_rules_summary = self._load_sop_rules()

    def _load_sop_rules(self) -> str:
        """Ingests and parses company SOP policy."""
        if os.path.exists(self.sop_path):
            with open(self.sop_path, "r", encoding="utf-8") as f:
                return f.read()
        return "Default Policy: Max Auto-Approve $1,000.00, Tolerance $0.05"

    def evaluate(self, payout: BankTransaction, invoice: Optional[ERPInvoice]) -> ReconciliationMatch:
        """
        Evaluates a payout and corresponding invoice against corporate governance rules.
        Returns a ReconciliationMatch with strict deterministic status and policy citation.
        """
        # Case 1: Unrecognized / Missing in ERP
        if invoice is None:
            return ReconciliationMatch(
                payout=payout,
                invoice=None,
                delta=payout.amount,
                match_status=MatchStatus.UNRECOGNIZED,
                policy_tier="Tier 2 (Exception)",
                reason="SOP-FIN-001 §4.4: Bank payout has no corresponding invoice in ERP. Escalated to Controllership.",
                requires_approval=True
            )

        delta = (invoice.net_amount - payout.amount).copy_abs()

        # Case 2: Material Discrepancy (Delta > $0.05)
        if delta > self.rounding_tolerance:
            return ReconciliationMatch(
                payout=payout,
                invoice=invoice,
                delta=delta,
                match_status=MatchStatus.DISPUTED,
                policy_tier="Tier 1 Dispute Protocol",
                reason=(
                    f"SOP-FIN-001 §4.3: Variance of ${delta:.2f} exceeds allowable tolerance (${self.rounding_tolerance:.2f}). "
                    f"Bank: ${payout.amount:.2f} vs ERP: ${invoice.net_amount:.2f}. Dispute ticket required."
                ),
                requires_approval=False,
                dispute_reason="Line Item Overbilling Variance"
            )

        # Case 3: Match with acceptable rounding tolerance (Delta <= $0.05)
        # Check authorization tier
        if payout.amount <= self.tier_1_max:
            tolerance_note = f" (Delta ${delta:.2f} absorbed into 9990-ROUNDING-VARIANCE)" if delta > 0 else ""
            return ReconciliationMatch(
                payout=payout,
                invoice=invoice,
                delta=delta,
                match_status=MatchStatus.AUTO_RECONCILED,
                policy_tier="Tier 1 (Autonomous Micro)",
                reason=f"SOP-FIN-001 §3 & §4.1: Amount ${payout.amount:.2f} <= ${self.tier_1_max:.2f}. Autonomous settlement authorized.{tolerance_note}",
                requires_approval=False
            )
        else:
            # Payout > $1,000.00 -> HITL Gate Required
            return ReconciliationMatch(
                payout=payout,
                invoice=invoice,
                delta=delta,
                match_status=MatchStatus.HITL_PENDING,
                policy_tier="Tier 2 (Manager Gate)",
                reason=(
                    f"SOP-FIN-001 §3: Payout of ${payout.amount:.2f} exceeds autonomous limit of ${self.tier_1_max:.2f}. "
                    "Mandatory human sign-off required prior to settlement."
                ),
                requires_approval=True
            )
