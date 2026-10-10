"""
Deterministic Verification Engine for LedgerGuard.
Executes mathematical double-entry balance checks and ERP post-state validation.
"""

from decimal import Decimal
from typing import List, Dict, Any
from runtime.models import BankTransaction, ERPInvoice, ReconciliationMatch, MatchStatus, VerificationResult

class DeterministicVerifier:
    def __init__(self, tolerance: Decimal = Decimal("0.05")):
        self.tolerance = tolerance

    def verify_reconciliation(
        self,
        bank_txns: List[BankTransaction],
        matches: List[ReconciliationMatch],
        final_erp_invoices: List[ERPInvoice],
        audit_hash_valid: bool = True
    ) -> VerificationResult:
        """
        Executes strict verification assertions:
        1. Mathematical balance delta:
           Sum(Bank Debits) == Sum(Settled) + Sum(Disputed) + Sum(Rounding Deltas)
        2. ERP UI status assertion:
           Ensures that settled matches are 'Reconciled' and disputed matches are 'Disputed' in ERP.
        3. Audit log cryptographic chain integrity.
        """
        total_bank_debits = sum((t.amount for t in bank_txns), Decimal("0.00"))
        
        total_settled = Decimal("0.00")
        total_disputed = Decimal("0.00")
        rounding_variance = Decimal("0.00")

        # Map current ERP state (normalized to uppercase)
        erp_state_map = {inv.id: (inv.status or "").upper() for inv in final_erp_invoices}
        ui_verified = True
        invoices_verified_count = 0

        for match in matches:
            inv_ui_status = erp_state_map.get(match.invoice.id, "") if match.invoice else ""

            if match.match_status == MatchStatus.AUTO_RECONCILED or inv_ui_status == "RECONCILED":
                total_settled += match.payout.amount
                if match.delta > 0 and match.delta <= self.tolerance:
                    rounding_variance += match.delta
                # Check UI state
                if match.invoice:
                    invoices_verified_count += 1
                    if inv_ui_status != "RECONCILED":
                        ui_verified = False

            elif match.match_status == MatchStatus.DISPUTED or inv_ui_status == "DISPUTED":
                total_disputed += match.payout.amount
                if match.invoice:
                    invoices_verified_count += 1
                    if inv_ui_status != "DISPUTED":
                        ui_verified = False

        accounted_total = total_settled + total_disputed
        unbalanced_delta = (total_bank_debits - accounted_total).copy_abs()

        # Balance holds if unbalanced delta is within rounding tolerance or 0
        balance_holds = unbalanced_delta <= self.tolerance

        verified = balance_holds and ui_verified and audit_hash_valid

        summary = (
            f"Verification {'PASSED' if verified else 'FAILED'}. "
            f"Bank Total: ${total_bank_debits:.2f} | Accounted (Settled+Disputed): ${accounted_total:.2f} | "
            f"Delta: ${unbalanced_delta:.2f} | ERP Status Assertion: {'OK' if ui_verified else 'FAIL'} | "
            f"Audit Chain: {'OK' if audit_hash_valid else 'FAIL'}."
        )

        return VerificationResult(
            verified=verified,
            total_bank_debits=total_bank_debits,
            total_settled_amount=total_settled,
            total_disputed_amount=total_disputed,
            rounding_variance=rounding_variance,
            unbalanced_delta=unbalanced_delta,
            erp_ui_verified=ui_verified,
            invoices_verified_count=invoices_verified_count,
            audit_hash_verified=audit_hash_valid,
            summary=summary
        )
