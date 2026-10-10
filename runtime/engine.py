"""
Core AI Employee Runtime Engine for LedgerGuard.
Implements the autonomous operating loop:
Goal -> Understand -> Plan -> Policy Check -> Execute -> Observe -> Adapt -> Verify -> Complete
"""

import os
import asyncio
from decimal import Decimal
from typing import Dict, Any, List, Optional, Callable
from runtime.models import (
    StepPhase, TaskStatus, MatchStatus, BankTransaction,
    ERPInvoice, ReconciliationMatch, ApprovalRequest, VerificationResult
)
from runtime.llm_client import OpenRouterClient
from runtime.reconciliation import ReconciliationEngine
from policy.guard import PolicyGuard
from tools.file_tool import FileIngestionTool
from tools.browser_tool import ERPBrowserTool
from hitl.approval_manager import HITLApprovalManager
from verification.verifier import DeterministicVerifier
from audit.logger import AuditLogger

class LedgerGuardRuntime:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080",
        artifacts_dir: Optional[str] = None,
        event_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        self.base_url = base_url
        self.artifacts_dir = artifacts_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "audit_artifacts"
        )
        self.event_callback = event_callback

        # Initialize Subsystems
        self.llm = OpenRouterClient()
        self.policy_guard = PolicyGuard()
        self.reconciliation_engine = ReconciliationEngine(self.policy_guard)
        self.file_tool = FileIngestionTool()
        self.browser_tool = ERPBrowserTool(artifacts_dir=os.path.join(self.artifacts_dir, "screenshots"))
        self.hitl_manager = HITLApprovalManager()
        self.verifier = DeterministicVerifier()
        self.audit = AuditLogger(artifacts_dir=self.artifacts_dir)

        # Working Memory
        self.task_id = "TASK-RUN-2026-001"
        self.status = TaskStatus.PENDING
        self.bank_txns: List[BankTransaction] = []
        self.erp_invoices: List[ERPInvoice] = []
        self.matches: List[ReconciliationMatch] = []
        self.execution_plan: Dict[str, Any] = {}
        self.verification_result: Optional[VerificationResult] = None

    def emit_event(self, phase: StepPhase, action: str, details: Dict[str, Any], status: TaskStatus = TaskStatus.IN_PROGRESS):
        """Dispatches real-time event to event callback and UI bus."""
        event_payload = {
            "task_id": self.task_id,
            "phase": phase.value,
            "action": action,
            "status": status.value,
            "details": details
        }
        if self.event_callback:
            try:
                self.event_callback(event_payload)
            except Exception:
                pass

    async def run(
        self,
        goal: str,
        csv_path: str,
        auto_resume_approvals: bool = False,
        headless: bool = True
    ) -> Dict[str, Any]:
        """
        Executes the complete autonomous operator lifecycle.
        """
        self.status = TaskStatus.IN_PROGRESS
        print(f"[LedgerGuard] Starting autonomous run for Goal: '{goal}'")

        # -------------------------------------------------------------
        # STEP 1: UNDERSTAND (Ingest Goal & Company SOP Memory)
        # -------------------------------------------------------------
        self.emit_event(StepPhase.UNDERSTAND, "Ingesting Goal and SOP Memory", {"goal": goal})
        sop_content = self.policy_guard.sop_rules_summary
        self.audit.log(
            phase=StepPhase.UNDERSTAND,
            action="Ingest Company SOP Policies",
            target="company_memory/finance_sop.md",
            details={"rules_summary": "Tier 1: <=$1,000; Tier 2: >$1,000 (HITL); Tolerance: $0.05"}
        )

        # -------------------------------------------------------------
        # STEP 2: PLAN (Synthesize Execution Strategy via OpenRouter / Planner)
        # -------------------------------------------------------------
        self.emit_event(StepPhase.PLAN, "Synthesizing Execution Plan", {})
        context = {
            "sop_rules": sop_content[:300],
            "payouts_count": 5,
            "vendors": ["VEND-101", "VEND-102", "VEND-103", "VEND-104"]
        }
        self.execution_plan = self.llm.plan_reconciliation(goal, context)
        self.audit.log(
            phase=StepPhase.PLAN,
            action="Generate Structured Operations Plan",
            target="runtime/llm_client.py",
            details=self.execution_plan
        )

        # -------------------------------------------------------------
        # STEP 3: EXECUTE (Parse Bank Data Fixture)
        # -------------------------------------------------------------
        self.emit_event(StepPhase.EXECUTE, "Ingesting Banking Payout Clearinghouse Records", {"file": csv_path})
        self.bank_txns = self.file_tool.parse_bank_csv(csv_path)
        self.audit.log(
            phase=StepPhase.EXECUTE,
            action="Parse Bank Payouts CSV",
            target=csv_path,
            details={"record_count": len(self.bank_txns), "total_amount": float(sum(t.amount for t in self.bank_txns))}
        )

        # -------------------------------------------------------------
        # STEP 4: OBSERVE (Connect Browser to Mock ERP & Extract Live DOM)
        # -------------------------------------------------------------
        self.emit_event(StepPhase.OBSERVE, "Connecting Browser to Enterprise ERP Portal", {"url": self.base_url})
        await self.browser_tool.initialize(headless=headless)
        login_res = await self.browser_tool.login(
            url=f"{self.base_url}/login",
            username="ops_admin",
            password="LedgerGuardSecure2026!"
        )
        self.audit.log(
            phase=StepPhase.OBSERVE,
            action="Authenticate into ERP Portal",
            target=f"{self.base_url}/login",
            details=login_res,
            screenshot=login_res.get("screenshot")
        )

        self.erp_invoices = await self.browser_tool.extract_invoices()
        self.audit.log(
            phase=StepPhase.OBSERVE,
            action="Extract ERP Invoice Registry DOM",
            target=f"{self.base_url}/",
            details={"extracted_count": len(self.erp_invoices)}
        )

        # -------------------------------------------------------------
        # STEP 5: POLICY CHECK & 3-WAY RECONCILIATION
        # -------------------------------------------------------------
        self.emit_event(StepPhase.POLICY_CHECK, "Executing 3-Way Policy Reconciliation", {})
        self.matches = self.reconciliation_engine.reconcile_batch(self.bank_txns, self.erp_invoices)
        self.audit.log(
            phase=StepPhase.POLICY_CHECK,
            action="Evaluate Transactions Against SOP Governance Tiers",
            target="policy/guard.py",
            details={"evaluated_count": len(self.matches)}
        )

        # -------------------------------------------------------------
        # STEP 6: EXECUTION & ADAPTATION LOOP
        # -------------------------------------------------------------
        for match in self.matches:
            # Case A: Auto-Reconciliation (Tier 1 <= $1,000)
            if match.match_status == MatchStatus.AUTO_RECONCILED:
                self.emit_event(
                    StepPhase.EXECUTE,
                    f"Settling Tier 1 Invoice {match.invoice.id} (${match.payout.amount:.2f})",
                    {"invoice_id": match.invoice.id, "amount": float(match.payout.amount)}
                )
                try:
                    settle_res = await self.browser_tool.settle_invoice(
                        invoice_id=match.invoice.id,
                        payout_id=match.payout.payout_id,
                        bank_reference=match.payout.bank_reference
                    )
                    
                    # If adaptation was used (e.g. Chaos mode selector fallback)
                    if settle_res.get("adaptation_used"):
                        self.emit_event(
                            StepPhase.ADAPT,
                            f"Resilient Locator Adaptation Triggered for {match.invoice.id}",
                            {"strategy": settle_res["adaptation_used"]}
                        )
                        self.audit.log(
                            phase=StepPhase.ADAPT,
                            action="Heuristic Locator Fallback",
                            target=match.invoice.id,
                            details={"adaptation": settle_res["adaptation_used"]}
                        )

                    self.audit.log(
                        phase=StepPhase.EXECUTE,
                        action="Execute ERP Settle Action",
                        target=match.invoice.id,
                        details=settle_res,
                        screenshot=settle_res.get("screenshot")
                    )
                except Exception as e:
                    self.emit_event(StepPhase.ADAPT, f"Error settling invoice {match.invoice.id}: {e}", {})

            # Case B: Dispute (Variance > $0.05)
            elif match.match_status == MatchStatus.DISPUTED:
                self.emit_event(
                    StepPhase.EXECUTE,
                    f"Filing Vendor Dispute for {match.invoice.id} (Variance: ${match.delta:.2f})",
                    {"invoice_id": match.invoice.id, "variance": float(match.delta)}
                )
                dispute_res = await self.browser_tool.dispute_invoice(
                    invoice_id=match.invoice.id,
                    reason=match.dispute_reason or "Line Item Overbilling Variance",
                    expected_amount=float(match.payout.amount),
                    notes=match.reason
                )
                self.audit.log(
                    phase=StepPhase.EXECUTE,
                    action="File ERP Vendor Dispute Ticket",
                    target=match.invoice.id,
                    details=dispute_res,
                    screenshot=dispute_res.get("post_evidence")
                )

            # Case C: HITL Gate (Tier 2 > $1,000)
            elif match.match_status == MatchStatus.HITL_PENDING:
                self.emit_event(
                    StepPhase.POLICY_CHECK,
                    f"HITL Gate Triggered: {match.invoice.id} Payout of ${match.payout.amount:.2f} requires approval",
                    {"invoice_id": match.invoice.id, "amount": float(match.payout.amount)},
                    status=TaskStatus.WAITING_APPROVAL
                )
                # Capture current viewport as approval evidence
                screenshot_evidence = await self.browser_tool.capture_evidence(f"hitl_gate_{match.invoice.id}")
                
                # Persist approval request in SQLite
                approval_req = self.hitl_manager.create_request(
                    task_id=self.task_id,
                    invoice_id=match.invoice.id,
                    payout_id=match.payout.payout_id,
                    vendor_name=match.payout.vendor_name,
                    amount=match.payout.amount,
                    discrepancy=match.delta,
                    policy_citation=match.reason,
                    screenshot_path=screenshot_evidence
                )

                self.audit.log(
                    phase=StepPhase.POLICY_CHECK,
                    action="Suspend Execution at HITL Gate",
                    target=match.invoice.id,
                    details=approval_req.model_dump(),
                    screenshot=screenshot_evidence
                )

                if auto_resume_approvals:
                    # Automatically approve for unattended test runs
                    print(f"[LedgerGuard] Simulating operator approval for {approval_req.approval_id}...")
                    self.hitl_manager.decide(approval_req.approval_id, "APPROVE", "Pre-authorized demo run")
                    self.audit.log(
                        phase=StepPhase.POLICY_CHECK,
                        action="Record Operator Approval Sign-Off",
                        target=match.invoice.id,
                        actor="Human Operator (Simulated)",
                        details={"approval_id": approval_req.approval_id, "decision": "APPROVED"}
                    )
                    # Proceed to settle
                    settle_res = await self.browser_tool.settle_invoice(
                        invoice_id=match.invoice.id,
                        payout_id=match.payout.payout_id,
                        bank_reference=match.payout.bank_reference
                    )
                    match.match_status = MatchStatus.AUTO_RECONCILED
                    self.audit.log(
                        phase=StepPhase.EXECUTE,
                        action="Execute Approved Settle Action",
                        target=match.invoice.id,
                        details=settle_res,
                        screenshot=settle_res.get("screenshot")
                    )

        # -------------------------------------------------------------
        # STEP 7: DETERMINISTIC VERIFICATION & CROSS-CHECKS
        # -------------------------------------------------------------
        self.emit_event(StepPhase.VERIFY, "Executing Deterministic Verification & Cross-Checks", {})
        final_erp_invoices = await self.browser_tool.extract_invoices()
        audit_chain_valid = self.audit.verify_integrity()

        self.verification_result = self.verifier.verify_reconciliation(
            bank_txns=self.bank_txns,
            matches=self.matches,
            final_erp_invoices=final_erp_invoices,
            audit_hash_valid=audit_chain_valid
        )

        self.audit.log(
            phase=StepPhase.VERIFY,
            action="Perform Mathematical & UI Cross-Verification",
            target="verification/verifier.py",
            details=self.verification_result.model_dump()
        )

        # -------------------------------------------------------------
        # STEP 8: COMPLETE & EXPORT AUDIT ARTIFACTS
        # -------------------------------------------------------------
        report_html_path = self.audit.export_report_html(self.verification_result)
        self.status = TaskStatus.COMPLETED if self.verification_result.verified else TaskStatus.FAILED

        self.emit_event(
            StepPhase.COMPLETE,
            "Reconciliation Completed & Cryptographic Audit Generated",
            {"report_path": report_html_path, "verified": self.verification_result.verified},
            status=self.status
        )

        await self.browser_tool.close()

        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "verification": self.verification_result.model_dump(),
            "report_path": report_html_path,
            "matches_count": len(self.matches),
            "audit_records_count": len(self.audit.records)
        }
