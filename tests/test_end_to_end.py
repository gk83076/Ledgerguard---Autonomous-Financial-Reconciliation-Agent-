import os
import sys
import time
import asyncio
import threading
import pytest
import uvicorn
from decimal import Decimal

from erp_portal.server import app as erp_app, invoice_db, INITIAL_INVOICES
from runtime.engine import LedgerGuardRuntime
from runtime.models import TaskStatus

@pytest.fixture(scope="module")
def start_erp_server():
    """Starts the Mock ERP portal in a background daemon thread for testing."""
    # Reset seed
    invoice_db.clear()
    invoice_db.extend([dict(inv) for inv in INITIAL_INVOICES])

    server = uvicorn.Server(uvicorn.Config(erp_app, host="127.0.0.1", port=8080, log_level="error"))
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    time.sleep(1.5)
    yield
    server.should_exit = True

def test_full_autonomous_reconciliation_e2e(start_erp_server):
    """
    End-to-end integration test validating the entire autonomous lifecycle:
    Goal -> Understand -> Plan -> Execute -> Observe -> Adapt -> Verify -> Complete
    """
    async def _async_run():
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        csv_path = os.path.join(base_dir, "data_fixtures", "bank_payouts_oct2026.csv")
        artifacts_dir = os.path.join(base_dir, "audit_artifacts_test")

        runtime = LedgerGuardRuntime(
            base_url="http://127.0.0.1:8080",
            artifacts_dir=artifacts_dir
        )

        goal = (
            "Reconcile vendor payouts from last week's CSV against internal ERP portal, "
            "flag discrepancies, draft dispute tickets, and process undisputed batches under $1,000."
        )

        result = await runtime.run(
            goal=goal,
            csv_path=csv_path,
            auto_resume_approvals=True,
            headless=True
        )

        # Assertions
        assert result["status"] == TaskStatus.COMPLETED.value
        assert result["matches_count"] == 5
        assert result["audit_records_count"] >= 10

        # Verification assertions
        verif = result["verification"]
        assert verif["verified"] is True
        assert verif["erp_ui_verified"] is True
        assert verif["audit_hash_verified"] is True
        assert Decimal(str(verif["unbalanced_delta"])) <= Decimal("0.05")

        # Check report generation
        assert os.path.exists(result["report_path"])
        with open(result["report_path"], "r", encoding="utf-8") as f:
            html = f.read()
            assert "LedgerGuard Audit Trail" in html
            assert "Verification Status: PASSED" in html

    asyncio.run(_async_run())
