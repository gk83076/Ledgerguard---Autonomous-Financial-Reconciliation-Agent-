"""
Deterministic Financial Reconciliation Engine for LedgerGuard.
Executes 3-way matching between Bank Transactions, ERP Invoices, and Corporate SOP Policies.
"""

from decimal import Decimal
from typing import List, Dict, Any, Tuple, Optional
from runtime.models import BankTransaction, ERPInvoice, ReconciliationMatch, MatchStatus
from policy.guard import PolicyGuard

class ReconciliationEngine:
    def __init__(self, policy_guard: Optional[PolicyGuard] = None):
        self.guard = policy_guard or PolicyGuard()

    def reconcile_batch(
        self,
        bank_txns: List[BankTransaction],
        erp_invoices: List[ERPInvoice]
    ) -> List[ReconciliationMatch]:
        """
        Correlates bank payouts against ERP invoices and generates evaluated matches.
        """
        # Index ERP invoices by invoice_id and vendor_id
        invoices_by_id: Dict[str, ERPInvoice] = {inv.id: inv for inv in erp_invoices}
        invoices_by_vendor: Dict[str, List[ERPInvoice]] = {}
        for inv in erp_invoices:
            invoices_by_vendor.setdefault(inv.vendor_id, []).append(inv)

        results: List[ReconciliationMatch] = []
        consumed_invoice_ids = set()

        for txn in bank_txns:
            matched_invoice: Optional[ERPInvoice] = None

            # 1. Exact match attempt by vendor and amount
            candidates = invoices_by_vendor.get(txn.vendor_id, [])
            for cand in candidates:
                if cand.id in consumed_invoice_ids:
                    continue
                # If amount matches within $0.05
                if (cand.net_amount - txn.amount).copy_abs() <= Decimal("0.05"):
                    matched_invoice = cand
                    consumed_invoice_ids.add(cand.id)
                    break

            # 2. If no exact match, look for vendor candidate with potential discrepancy
            if not matched_invoice:
                for cand in candidates:
                    if cand.id not in consumed_invoice_ids:
                        matched_invoice = cand
                        consumed_invoice_ids.add(cand.id)
                        break

            # 3. Evaluate match through Policy Guard
            match_outcome = self.guard.evaluate(txn, matched_invoice)
            results.append(match_outcome)

        return results
