"""
OpenRouter LLM Integration for LedgerGuard AI Employee.
Uses OpenAI-compatible client configured for OpenRouter endpoints.
Provides fallback heuristic reasoning engine for offline/deterministic evaluation.
"""

import os
import json
from typing import Dict, Any, List, Optional
from openai import OpenAI

class OpenRouterClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1"
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url
        self.model = model or os.getenv("LEDGERGUARD_MODEL", "anthropic/claude-3.5-sonnet")
        self.client = None

        if self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                default_headers={
                    "HTTP-Referer": "https://github.com/ledgerguard/operator",
                    "X-Title": "LedgerGuard Autonomous AP Operator"
                }
            )

    def plan_reconciliation(self, goal: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates a structured execution plan from the goal, SOP rules, and banking transactions.
        If an OpenRouter API key is available, calls OpenRouter.
        Otherwise, uses the deterministic domain-specialized planner.
        """
        if self.client:
            try:
                system_prompt = (
                    "You are LedgerGuard, an autonomous enterprise AI employee specialized in financial operations. "
                    "Analyze the user's goal, the internal SOP policies, and the batch data. "
                    "Output a valid JSON execution plan with steps, tools to call, and policy gating."
                )
                user_content = json.dumps({
                    "goal": goal,
                    "sop_summary": context.get("sop_rules"),
                    "payouts_count": len(context.get("payouts", [])),
                    "vendors": context.get("vendors")
                }, indent=2)

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Create reconciliation plan for: {user_content}"}
                    ],
                    response_format={"type": "json_object"} if "gpt-4" in self.model else None,
                    temperature=0.1
                )
                raw_text = response.choices[0].message.content
                # Attempt to parse json
                try:
                    return json.loads(raw_text)
                except Exception:
                    pass
            except Exception as e:
                print(f"[OpenRouterClient] Remote call failed ({e}), falling back to deterministic planner.")

        # Deterministic Domain Planner
        return self._deterministic_plan(goal, context)

    def _deterministic_plan(self, goal: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Produces a deterministic, step-by-step financial operations plan."""
        return {
            "operator": "LedgerGuard Autonomous Operator",
            "goal": goal,
            "strategy": "Three-Way Deterministic Matching with Policy Gating",
            "phases": [
                {
                    "step_id": 1,
                    "name": "Context & Policy Ingestion",
                    "action": "Read company_memory/finance_sop.md and parse approval thresholds."
                },
                {
                    "step_id": 2,
                    "name": "Banking Ingestion",
                    "action": "Parse bank CSV export with cents-accurate decimal precision."
                },
                {
                    "step_id": 3,
                    "name": "ERP Inspection & Extraction",
                    "action": "Authenticate into enterprise ERP portal and extract live invoice records."
                },
                {
                    "step_id": 4,
                    "name": "Three-Way Reconciliation & Gating",
                    "action": "Compare transactions against invoices and classify into Tier 1 (Auto), Tier 2 (HITL), or Dispute."
                },
                {
                    "step_id": 5,
                    "name": "Execution & Human Sign-off",
                    "action": "Settle Tier 1 matches, file dispute tickets for variances, and pause at HITL gate for Tier 2."
                },
                {
                    "step_id": 6,
                    "name": "Deterministic Verification & Audit Generation",
                    "action": "Assert zero-delta double entry balance, verify DOM post-states, and export SHA-256 audit package."
                }
            ]
        }
