"""
Playwright Browser Automation Connector for LedgerGuard.
Operates the Enterprise ERP billing portal with deep DOM interaction,
resilient multi-tier locator fallbacks, session handling, and evidence screenshot capture.
"""

import os
import asyncio
from decimal import Decimal
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from runtime.models import ERPInvoice, RiskTier
from tools.base import BaseTool

class ERPBrowserTool(BaseTool):
    name = "erp_browser_tool"
    description = "Automates browser interactions with internal enterprise ERP portal, handling authentication, data extraction, settlement actions, and evidence capture."
    risk_tier = RiskTier.MUTATING_HIGH

    def __init__(self, artifacts_dir: Optional[str] = None):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.artifacts_dir = artifacts_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "audit_artifacts",
            "screenshots"
        )
        os.makedirs(self.artifacts_dir, exist_ok=True)

    async def initialize(self, headless: bool = True):
        """Launches Playwright Chromium browser."""
        if not self.playwright:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=headless,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 800}
            )
            self.page = await self.context.new_page()

    async def close(self):
        """Gracefully terminates browser session."""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self.page = None
        self.browser = None
        self.playwright = None

    async def execute(self, **kwargs) -> Dict[str, Any]:
        action = kwargs.get("action")
        if action == "login":
            return await self.login(
                kwargs.get("url", "http://127.0.0.1:8080/login"),
                kwargs.get("username", "ops_admin"),
                kwargs.get("password", "LedgerGuardSecure2026!")
            )
        elif action == "extract_invoices":
            invoices = await self.extract_invoices()
            return {"success": True, "count": len(invoices), "invoices": [inv.model_dump() for inv in invoices]}
        elif action == "settle_invoice":
            return await self.settle_invoice(
                kwargs.get("invoice_id"),
                kwargs.get("payout_id"),
                kwargs.get("bank_reference")
            )
        elif action == "dispute_invoice":
            return await self.dispute_invoice(
                kwargs.get("invoice_id"),
                kwargs.get("reason"),
                kwargs.get("expected_amount"),
                kwargs.get("notes")
            )
        elif action == "screenshot":
            path = await self.capture_evidence(kwargs.get("tag", "evidence"))
            return {"success": True, "screenshot_path": path}
        else:
            raise ValueError(f"Unknown browser action: {action}")

    async def login(self, url: str, username: str, password: str) -> Dict[str, Any]:
        """Authenticates into the ERP portal."""
        if not self.page:
            await self.initialize()

        await self.page.goto(url, wait_until="networkidle")

        # Fill credentials
        await self.page.fill("#username", username)
        await self.page.fill("#password", password)
        await self.page.click("#btn-login-submit")
        await self.page.wait_for_load_state("networkidle")

        # Verify login success by checking for dashboard elements
        is_logged_in = await self.page.locator("#invoices-table").is_visible()
        if not is_logged_in:
            raise RuntimeError("Authentication to Enterprise ERP failed.")

        screenshot_path = await self.capture_evidence("post_login_dashboard")
        return {
            "success": True,
            "status": "Authenticated",
            "user": username,
            "screenshot": screenshot_path
        }

    async def extract_invoices(self) -> List[ERPInvoice]:
        """Extracts all invoice records from the ERP DOM table."""
        if not self.page:
            raise RuntimeError("Browser not initialized.")

        # Ensure table is loaded
        await self.page.wait_for_selector("#invoices-table", timeout=5000)
        rows = await self.page.locator("#invoices-table-body tr.invoice-row").all()

        invoices: List[ERPInvoice] = []
        for row in rows:
            inv_id = (await row.locator(".invoice-code").inner_text()).strip()
            vendor_id = (await row.locator(".vendor-tag").inner_text()).strip()
            vendor_name = (await row.locator(".vendor-name").inner_text()).strip()
            
            # Amount extraction
            net_text = (await row.locator(".cell-net .amount-val").inner_text()).replace("$", "").strip()
            gross_text = (await row.locator("td:nth-child(3)").inner_text()).replace("$", "").strip()
            tax_text = (await row.locator("td:nth-child(4)").inner_text()).replace("$", "").strip()
            
            due_date = (await row.locator(".cell-date").inner_text()).strip()
            status = (await row.locator(".badge").inner_text()).strip()
            
            # Settlement details
            ref_el = row.locator(".ref-code")
            match_ref = (await ref_el.inner_text()).strip() if await ref_el.count() > 0 else None

            invoices.append(ERPInvoice(
                id=inv_id,
                vendor_id=vendor_id,
                vendor_name=vendor_name,
                gross_amount=Decimal(gross_text),
                tax_amount=Decimal(tax_text),
                net_amount=Decimal(net_text),
                currency="USD",
                due_date=due_date,
                status=status,
                match_reference=match_ref
            ))

        return invoices

    async def settle_invoice(self, invoice_id: str, payout_id: str, bank_reference: str) -> Dict[str, Any]:
        """
        Settles an invoice using multi-tier locator resilience.
        Attempts primary ID, then falls back to semantic text and row locators.
        """
        if not self.page:
            raise RuntimeError("Browser not initialized.")

        row_selector = f"#row-{invoice_id}"
        await self.page.wait_for_selector(row_selector, timeout=5000)

        # Multi-Tier Locator Fallback Strategy
        locator_candidates = [
            f"#btn-settle-{invoice_id}",                                    # 1. Primary ID
            f"{row_selector} button:has-text('Match & Settle')",           # 2. Semantic Text in Row
            f"{row_selector} button[aria-label*='Reconcile']",             # 3. ARIA attribute
            f"{row_selector} .action-settle",                              # 4. Class selector
            f"{row_selector} button.btn-success"                           # 5. Generic class
        ]

        clicked = False
        adaptation_used = None

        for idx, selector in enumerate(locator_candidates):
            btn = self.page.locator(selector)
            if await btn.count() > 0 and await btn.is_visible():
                if idx > 0:
                    adaptation_used = f"Fallback tier {idx+1}: {selector}"
                await btn.click()
                clicked = True
                break

        if not clicked:
            raise RuntimeError(f"Failed to locate settle button for invoice {invoice_id} across all 5 fallback tiers.")

        # Wait for status transition in DOM
        await self.page.wait_for_selector(f"#status-badge-{invoice_id}.badge-reconciled", timeout=5000)

        evidence_path = await self.capture_evidence(f"settled_{invoice_id}")
        return {
            "success": True,
            "invoice_id": invoice_id,
            "new_status": "Reconciled",
            "adaptation_used": adaptation_used,
            "screenshot": evidence_path
        }

    async def dispute_invoice(
        self,
        invoice_id: str,
        reason: str,
        expected_amount: float,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Opens dispute dialog in ERP, fills variance details, and submits ticket.
        """
        if not self.page:
            raise RuntimeError("Browser not initialized.")

        row_selector = f"#row-{invoice_id}"
        await self.page.wait_for_selector(row_selector, timeout=5000)

        # Multi-tier locator for Dispute button
        dispute_btn_candidates = [
            f"#btn-dispute-{invoice_id}",
            f"{row_selector} button:has-text('Dispute')",
            f"{row_selector} button[aria-label*='Dispute']",
            f"{row_selector} .action-dispute"
        ]

        clicked = False
        for selector in dispute_btn_candidates:
            btn = self.page.locator(selector)
            if await btn.count() > 0 and await btn.is_visible():
                await btn.click()
                clicked = True
                break

        if not clicked:
            raise RuntimeError(f"Could not locate dispute button for invoice {invoice_id}.")

        # Wait for modal dialog to appear
        await self.page.wait_for_selector("#dispute-modal:not(.hidden)", timeout=5000)

        # Fill modal form
        await self.page.fill("#modal-expected-amt", str(expected_amount))
        await self.page.select_option("#modal-reason", reason)
        if notes:
            await self.page.fill("#modal-notes", notes)

        # Capture evidence of filled dispute form before submission
        pre_submit_evidence = await self.capture_evidence(f"dispute_form_{invoice_id}")

        # Submit
        await self.page.click("#btn-submit-dispute")

        # Wait for row to update to Disputed
        await self.page.wait_for_selector(f"#status-badge-{invoice_id}.badge-disputed", timeout=5000)

        post_evidence = await self.capture_evidence(f"disputed_confirmed_{invoice_id}")
        return {
            "success": True,
            "invoice_id": invoice_id,
            "new_status": "Disputed",
            "reason": reason,
            "pre_evidence": pre_submit_evidence,
            "post_evidence": post_evidence
        }

    async def capture_evidence(self, tag: str) -> str:
        """Captures a timestamped viewport screenshot as proof-of-work evidence."""
        if not self.page:
            return ""
        import time
        timestamp = int(time.time() * 1000)
        filename = f"{tag}_{timestamp}.png"
        filepath = os.path.join(self.artifacts_dir, filename)
        await self.page.screenshot(path=filepath, full_page=False)
        return filepath
