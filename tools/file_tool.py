"""
File and Data Ingestion Tools for LedgerGuard.
Handles CSV banking feeds, corporate memory JSON directories, and diff generation.
"""

import csv
import json
import os
from decimal import Decimal
from typing import List, Dict, Any, Optional
from runtime.models import BankTransaction, RiskTier
from tools.base import BaseTool

class FileIngestionTool(BaseTool):
    name = "file_ingestion_tool"
    description = "Parses bank transaction CSV exports and company memory documents with cents-accurate precision."
    risk_tier = RiskTier.READ_ONLY

    async def execute(self, **kwargs) -> Dict[str, Any]:
        action = kwargs.get("action")
        path = kwargs.get("path")

        if action == "parse_bank_csv":
            transactions = self.parse_bank_csv(path)
            return {
                "success": True,
                "count": len(transactions),
                "transactions": [t.model_dump() for t in transactions]
            }
        elif action == "load_vendor_directory":
            vendors = self.load_vendor_directory(path)
            return {"success": True, "vendors": vendors}
        else:
            raise ValueError(f"Unknown file action: {action}")

    def parse_bank_csv(self, file_path: str) -> List[BankTransaction]:
        """Parses bank payouts CSV ensuring Decimal currency values."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Bank CSV file not found: {file_path}")

        records: List[BankTransaction] = []
        with open(file_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                txn = BankTransaction(
                    payout_id=row["payout_id"].strip(),
                    bank_reference=row["bank_reference"].strip(),
                    vendor_id=row["vendor_id"].strip(),
                    vendor_name=row["vendor_name"].strip(),
                    amount=Decimal(str(row["amount"].strip())),
                    currency=row.get("currency", "USD").strip(),
                    settlement_date=row["settlement_date"].strip(),
                    payment_method=row["payment_method"].strip(),
                    memo=row.get("memo", "").strip()
                )
                records.append(txn)
        return records

    def load_vendor_directory(self, file_path: str) -> List[Dict[str, Any]]:
        """Loads known vendor directory metadata."""
        if not os.path.exists(file_path):
            return []
        with open(file_path, mode="r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def generate_diff(bank_txn: BankTransaction, erp_inv: Dict[str, Any]) -> Dict[str, Any]:
        """Generates a structured side-by-side reconciliation diff."""
        bank_amount = bank_txn.amount
        erp_amount = Decimal(str(erp_inv.get("net_amount", "0.00")))
        variance = (erp_amount - bank_amount).copy_abs()

        return {
            "invoice_id": erp_inv.get("id"),
            "payout_id": bank_txn.payout_id,
            "vendor_name": bank_txn.vendor_name,
            "bank_amount": float(bank_amount),
            "erp_amount": float(erp_amount),
            "variance": float(variance),
            "is_matched": variance <= Decimal("0.05"),
            "variance_type": "None" if variance == Decimal("0.00") else ("Rounding" if variance <= Decimal("0.05") else "Material Discrepancy")
        }
