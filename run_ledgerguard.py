"""
LedgerGuard Unified System Launcher
Starts both the Mock Enterprise ERP Portal (Port 8080) and the Real-Time Operator Console (Port 8500),
or executes autonomous golden test runs directly from the command line.

Usage:
  python run_ledgerguard.py         # Launches Web Ecosystem (ERP + Operator Console)
  python run_ledgerguard.py --cli   # Runs autonomous operator in headless CLI mode
  python run_ledgerguard.py --test  # Runs comprehensive unit & integration test suite
"""

import sys
import os
import time
import argparse
import asyncio
import threading
import uvicorn

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from erp_portal.server import app as erp_app
from web_console.server import app as console_app
from runtime.engine import LedgerGuardRuntime

def run_erp():
    uvicorn.run(erp_app, host="127.0.0.1", port=8080, log_level="warning")

def run_console():
    uvicorn.run(console_app, host="127.0.0.1", port=8500, log_level="info")

async def run_cli_mode(auto_approve: bool = True, headless: bool = True):
    print("=" * 70)
    print("🛡️  LEDGERGUARD: AUTONOMOUS FINANCIAL OPERATOR (CLI RUN)")
    print("=" * 70)

    # Start ERP server in background thread
    t_erp = threading.Thread(target=run_erp, daemon=True)
    t_erp.start()
    await asyncio.sleep(2)

    runtime = LedgerGuardRuntime(
        base_url="http://127.0.0.1:8080",
        artifacts_dir=os.path.join(BASE_DIR, "audit_artifacts")
    )

    goal = (
        "Reconcile vendor payouts from last week's CSV against internal ERP portal, "
        "flag discrepancies, draft dispute tickets, and process undisputed batches under $1,000."
    )
    csv_path = os.path.join(BASE_DIR, "data_fixtures", "bank_payouts_oct2026.csv")

    res = await runtime.run(
        goal=goal,
        csv_path=csv_path,
        auto_resume_approvals=auto_approve,
        headless=headless
    )

    print("\n" + "=" * 70)
    print(f"🏁 EXECUTION STATUS: {res['status']}")
    print(f"📊 Evaluated Matches: {res['matches_count']}")
    print(f"📜 Chained Audit Records: {res['audit_records_count']}")
    print(f"⚖️ Verification Summary: {res['verification']['summary']}")
    print(f"📑 Audit Report Generated at: {res['report_path']}")
    print("=" * 70)

def main():
    parser = argparse.ArgumentParser(description="LedgerGuard System Launcher")
    parser.add_argument("--cli", action="store_true", help="Run autonomous operator directly via CLI")
    parser.add_argument("--test", action="store_true", help="Run automated test suite")
    parser.add_argument("--auto-approve", action="store_true", default=True, help="Auto-approve HITL gates in CLI mode")
    parser.add_argument("--headed", action="store_true", help="Launch Playwright browser in headed mode")
    args = parser.parse_args()

    if args.test:
        import pytest
        sys.exit(pytest.main(["-v", "tests/"]))

    if args.cli:
        asyncio.run(run_cli_mode(auto_approve=args.auto_approve, headless=not args.headed))
    else:
        print("=" * 70)
        print("🚀 STARTING LEDGERGUARD ENTERPRISE ECOSYSTEM")
        print("=" * 70)
        print("🏢 Mock Enterprise ERP:      http://127.0.0.1:8080")
        print("🛡️  Operator Control Console: http://127.0.0.1:8500")
        print("=" * 70)
        print("Press Ctrl+C to terminate.")

        t_erp = threading.Thread(target=run_erp, daemon=True)
        t_erp.start()

        # Run console in main thread
        run_console()

if __name__ == "__main__":
    main()
