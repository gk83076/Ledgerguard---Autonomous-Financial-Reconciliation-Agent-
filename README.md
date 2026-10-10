# 🛡️ LedgerGuard: Autonomous Financial Reconciliation & Dispute Operator
### *An Enterprise AI Employee for Deep Browser Automation, Policy Governance, and Deterministic Reconciliation*

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-Chromium-green.svg)](https://playwright.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-teal.svg)](https://fastapi.tiangolo.com/)
[![OpenRouter](https://img.shields.io/badge/LLM-OpenRouter%20%2F%20OpenAI--compatible-purple.svg)](https://openrouter.ai/)
[![Frontend](https://img.shields.io/badge/Frontend-Vanilla%20JS%20(ES6%2B)%20%2F%20CSS-yellow.svg)](https://developer.mozilla.org/)
[![Tests](https://img.shields.io/badge/Tests-10%20Passing-brightgreen.svg)](tests/)

---

## 1. Executive Summary & Problem Statement

Enterprises lose millions in revenue and hundreds of hours each week reconciling clearinghouse bank disbursements against billing portals and enterprise resource planning (ERP) systems. Operators must repeatedly match line items, interpret opaque Standard Operating Procedures (SOPs), draft dispute tickets, and solicit managerial approvals.

Simple chatbots and LLM assistants **cannot** solve this bottleneck: they explain what should be done without executing actions, lack organizational memory, hallucinate floating-point financial values, and cannot interact directly with internal web tools.

**LedgerGuard** is an autonomous AI employee that turns a high-level operational request into completed, verified work:
> *"Reconcile vendor payouts from last week's CSV against our internal ERP billing portal, flag discrepancies, draft dispute tickets, and process undisputed batches under $1,000."*

LedgerGuard operates across:
1. **Local File I/O:** Parses bank exports with cents-accurate decimal calculations.
2. **Company Memory:** Ingests internal Markdown Standard Operating Procedures (`company_memory/finance_sop.md`) to establish spending thresholds ($\le \$1,000$ auto-approved) and dispute tolerances ($\le \$0.05$).
3. **Deep Browser Automation:** Uses Playwright to navigate a mock enterprise ERP portal, log in, filter invoices, settle matched line items, and file dispute tickets.
4. **Human-in-the-Loop (HITL) Governance:** Suspends execution cleanly when high-value payouts ($> \$1,000$) or anomalies are detected, broadcasting WebSocket alerts to an Operator Console.
5. **Self-Healing Adaptability:** Survives altered DOM selectors and dynamic UI changes through multi-tier locator fallbacks.
6. **Deterministic Verification:** Enforces double-entry balance delta assertions ($\sum \text{Bank} = \sum \text{Settled} + \sum \text{Disputed} + \Delta_{\text{tol}}$), asserts post-action UI states, and produces a SHA-256 cryptographically chained audit package.

---

## 2. Core Autonomous Loop

LedgerGuard is architected around an 8-stage deterministic operating cycle:

```
Goal Spec ──► [1. Understand] ──► [2. Plan] ──► [3. Ingest] ──► [4. Connect ERP]
                   │                   │              │                │
                   ▼                   ▼              ▼                ▼
             Read SOP Memory     OpenRouter LLM   Bank CSV Parse   Playwright Auth
                   │                   │              │                │
                   └───────────────────┴──────────────┴────────────────┘
                                       │
                                       ▼
                              [5. Policy Gate]
                           (3-Way Deterministic Match)
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
             Tier 1 (<= $1k)     Tier 2 (> $1k)    Variance (> $0.05)
             Auto-Reconcile       HITL Gate          Dispute Ticket
                    │                  │                  │
                    └──────────────────┼──────────────────┘
                                       │
                                       ▼
                              [6. Execute & Adapt]
                          (Multi-Tier Locator Fallback)
                                       │
                                       ▼
                              [7. Verify & Prove]
                    (Double-Entry Ledger + ERP UI Check)
                                       │
                                       ▼
                             [8. Audit & Complete]
                    (SHA-256 Hash Chain + HTML/PDF Report)
```

---

## 3. System Architecture & Components

```
AI Employee/
├── company_memory/                 # Organizational Context & Procedural Rules
│   ├── finance_sop.md             # Standard Operating Procedure (SOP-FIN-001)
│   └── vendor_directory.json      # Corporate vendor registry and payment terms
├── data_fixtures/                  # Banking & Invoice Data Feeds
│   └── bank_payouts_oct2026.csv   # Real-world clearinghouse payout batch
├── erp_portal/                     # Mock Enterprise ERP Portal (FastAPI + HTML/JS)
│   ├── server.py                  # Standalone billing portal with auth & chaos toggle
│   ├── templates/                 # Login & Dashboard templates
│   └── static/                    # Vanilla CSS & Vanilla JS (NO TypeScript)
├── runtime/                        # Core AI Employee Operating Engine
│   ├── engine.py                  # Autonomous loop coordinator
│   ├── models.py                  # Pydantic typing & domain schemas
│   ├── llm_client.py              # OpenRouter OpenAI-compatible client & fallback
│   └── reconciliation.py          # Cents-accurate 3-way matching engine
├── policy/                         # Governance & Permission Boundaries
│   └── guard.py                   # Ingests SOP rules, evaluates authorization tiers
├── tools/                          # Pluggable Tool Connector Abstractions
│   ├── base.py                    # BaseTool abstract interface & RiskTier schema
│   ├── file_tool.py               # CSV ingestion and structured diff generator
│   └── browser_tool.py            # Playwright automation with resilient locators
├── hitl/                           # Human-in-the-Loop Governance State Machine
│   └── approval_manager.py        # SQLite persistent suspension/resumption store
├── verification/                   # Deterministic Assertion Engine
│   └── verifier.py                # Double-entry balance check & UI status assertions
├── audit/                          # Cryptographic Proof-of-Work & Reporting
│   └── logger.py                  # SHA-256 chained event log & HTML report export
├── web_console/                    # Real-time Operator Dashboard (UI)
│   ├── server.py                  # WebSocket event broadcaster & REST API
│   └── static/                    # Dark-mode dashboard (Vanilla JS + CSS)
├── tests/                          # Automated Unit & E2E Integration Test Suite
│   ├── test_policy_guard.py       # SOP authorization and tolerance rules
│   ├── test_file_and_reconciliation.py # CSV parser and 3-way matching logic
│   ├── test_audit_and_hitl.py     # SQLite persistence & SHA-256 hash chaining
│   └── test_end_to_end.py         # Full browser automation E2E integration test
├── requirements.txt                # Python dependencies
└── run_ledgerguard.py              # Unified System Launcher
```

---

## 4. Setup & Quickstart Guide

### Prerequisites
- Python 3.11 or higher
- Windows, macOS, or Linux

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ledgerguard/operator.git
   cd "AI Employee"
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Playwright Chromium browser:**
   ```bash
   playwright install chromium
   ```

4. *(Optional)* **Configure OpenRouter API Key:**
   ```bash
   # Set environment variable for remote LLM planning (defaults to claude-3.5-sonnet via OpenRouter)
   export OPENROUTER_API_KEY="sk-or-v1-..."
   # Note: If no API key is provided, LedgerGuard automatically falls back to its
   # deterministic domain planner, guaranteeing 100% offline functionality!
   ```

---

## 5. Running LedgerGuard

### Mode A: Interactive Real-Time Web Ecosystem (Recommended)

Launch both the Mock Enterprise ERP Portal and the Operator Console with one command:
```bash
python run_ledgerguard.py
```

- **Mock Enterprise ERP Portal:** [http://127.0.0.1:8080](http://127.0.0.1:8080)  
  *(Login: `ops_admin` / `LedgerGuardSecure2026!`)*
- **Real-Time Operator Console:** [http://127.0.0.1:8500](http://127.0.0.1:8500)

**Demonstration Steps in the Console:**
1. Select a pre-configured scenario button (e.g. **Scenario 1: Full Enterprise Run**).
2. Click **🚀 Deploy AI Employee**.
3. Watch the live 8-stage pipeline pulse as Playwright logs into the ERP portal in the background.
4. When the high-value payout ($2,450.00) triggers the **HITL Governance Gate**, observe the approval card appear in real-time with the exact SOP citation.
5. Click **✓ Authorize & Settle Payout** to sign off and resume execution.
6. Review the live verification results and click **📑 View Audit Report** to inspect the cryptographic SHA-256 proof-of-work report.

---

### Mode B: Direct Headless CLI Mode

Run the autonomous operator in headless CLI mode for automated workflows or CI/CD pipelines:
```bash
python run_ledgerguard.py --cli
```

*(To see Playwright interact with the browser visually on your screen, add `--headed`:)*
```bash
python run_ledgerguard.py --cli --headed
```

---

### Mode C: Automated Test Suite

Run all 10 unit and end-to-end integration tests:
```bash
python run_ledgerguard.py --test
# or
python -m pytest tests/ -v
```

---

## 6. The 4 Golden Operational Scenarios

| Scenario | Input Payout | ERP Invoice | Expected Outcome | Autonomous Mechanism |
| :--- | :--- | :--- | :--- | :--- |
| **1. Autonomous Micro Settle** | PO-001 ($450.00) | INV-001 ($450.00) | Auto-Reconciled | Payout $\le \$1,000$ limit. Matches cleanly, settled immediately with zero human intervention. |
| **2. Policy-Gated HITL Sign-Off** | PO-002 ($2,450.00) | INV-002 ($2,450.00) | Suspended $\rightarrow$ Approved | Payout $> \$1,000$. Policy Guard halts execution, saves checkpoint in SQLite, emits WebSocket event, resumes upon approval. |
| **3. Material Variance Dispute** | PO-003 ($820.00) | INV-003 ($910.00) | Disputed & On Hold | Delta = $\$90.00 > \$0.05$ tolerance. Agent halts payout, opens dispute modal in ERP, submits formal ticket citing line-item variance. |
| **4. Chaos Selector Self-Healing** | PO-005 ($380.00) | INV-005 ($380.00) | Resilient Settle | Chaos Mode scrambles primary button ID. Agent's multi-tier locator activates semantic fallback, succeeds, and logs `ADAPT` record. |

---

## 7. Important Technical & Design Decisions

1. **Vanilla JavaScript (ES6+) Frontend — Zero TypeScript Bloat:**  
   The UI is built with pure, modern Vanilla JavaScript, semantic HTML5, and pure Vanilla CSS. This avoids complicated Node.js compilation pipelines, build steps, and `node_modules` dependency friction while delivering instant reload speed and a rich dark-mode aesthetic.

2. **OpenRouter LLM Client with Deterministic Offline Fallback:**  
   Configured for OpenRouter (`base_url="https://openrouter.ai/api/v1"`). If an API key is provided, it uses high-capability reasoning models (`anthropic/claude-3.5-sonnet` or `openai/gpt-4o`). If no key is set or network is unavailable, it falls back to a deterministic domain planner so evaluation is 100% reproducible.

3. **Cents-Accurate Decimal Arithmetic:**  
   Standard IEEE 754 floating-point numbers (`0.1 + 0.2 != 0.3`) cause disastrous inaccuracies in financial systems. LedgerGuard strictly uses Python's `decimal.Decimal` across the file parser, policy engine, and verifier.

4. **Multi-Tier Locator Fallback for DOM Resilience:**  
   Browser automation typically breaks when UI markup changes. `ERPBrowserTool` implements a 5-tier fallback hierarchy:
   1. Primary Element ID (`#btn-settle-{id}`)
   2. Semantic Text within Row (`tr#row-{id} button:has-text("Match & Settle")`)
   3. ARIA Role Attribute (`button[aria-label*="Reconcile"]`)
   4. Class Selector (`.action-settle`)
   5. Row Position Heuristic (`tr#row-{id} button.btn-success`)

5. **Stateful Checkpointing via SQLite:**  
   HITL approvals are persisted in SQLite (`hitl_approvals.db`), allowing tasks to be paused and resumed across arbitrary time spans, process restarts, or operator shifts.

6. **Tamper-Evident SHA-256 Audit Chaining:**  
   Every action generates a cryptographic record chained to the previous step's hash:
   $$\text{Hash}_n = \text{SHA256}(\text{Hash}_{n-1} \parallel \text{Timestamp} \parallel \text{Phase} \parallel \text{Action} \parallel \text{Target} \parallel \text{Payload})$$
   Any manual modification to the log file immediately invalidates the chain integrity check.

---

## 8. Evaluation Criteria Alignment

- **Autonomy:** Receives only a high-level operational goal. Autonomously reads SOPs, digests CSV payouts, determines tool selection, drives the browser, and completes work without step-by-step instructions.
- **Execution:** Performs concrete work by directly driving browser sessions, clicking real ERP buttons, submitting dispute forms, and writing files.
- **Reliability:** Recovers from altered selectors via multi-tier fallbacks, handles rounding tolerances ($\le \$0.05$), and preserves state in SQLite.
- **Verification:** Runs double-entry balance delta assertions and re-queries the ERP DOM to prove post-action status changes.
- **Generalization:** Pluggable `BaseTool` abstraction and decoupled `PolicyGuard` allow adding new tools (Slack, Stripe, Zendesk) without modifying the core runtime loop.
- **Engineering Quality:** Async-first Python, strict Pydantic typing, 10 automated unit and integration tests, and clean domain isolation.
- **Product Thinking:** Specifically targets high-friction enterprise financial workflows where regulatory auditability and permission gates are non-negotiable.

---

## 9. Known Limitations

- **Single Active Browser Tab:** Playwright automation currently operates sequentially on a single browser tab. In high-volume production, a distributed browser pool (e.g. Browserless or Playwright cluster) would enable parallel processing.
- **ERP Authentication Mechanism:** Uses session cookie authentication. Enterprise SSO/SAML with physical MFA requires hardware token integration.
- **Unrecognized Vendor Auto-Discovery:** Bank payouts with completely unknown vendor IDs are escalated to Controllership rather than automatically provisioned.

---

## 10. Future Roadmap (What We Would Build Next)

1. **Multi-Tenant SSO & Webhook Connectors:** Native webhooks for Slack/Teams alerts allowing managers to approve high-risk payouts directly via interactive buttons.
2. **Self-Supervised SOP Learning:** Feedback ingestion loop where approved operator decisions update company memory weights, gradually increasing autonomous authorization boundaries.
3. **Computer-Vision Desktop Agent:** Integration with OS-level desktop automation (via PyAutoGUI/Accessibility APIs) for legacy desktop ERP applications (e.g. SAP GUI or QuickBooks Desktop) that lack web interfaces.
4. **PDF Invoice OCR Extraction:** Parsing unstructured vendor invoice PDFs attached to emails and cross-referencing them against banking wire feeds.

---

## 11. Assumptions Made

- All banking payout records are denominated in USD.
- ERP invoice statuses follow the lifecycle: `Pending` $\rightarrow$ `Reconciled` / `Disputed`.
- Rounding discrepancies up to $\$0.05$ are acceptable per corporate SOP-FIN-001.

---

## 12. Tech Stack & Dependencies

- **Runtime & Orchestration:** Python 3.11+, `asyncio`, `Pydantic 2.10`, `FastAPI 0.115`, `Uvicorn`
- **Browser Automation:** `Playwright 1.49` (Chromium headless/headed)
- **Data & Precision:** `decimal.Decimal`, `csv`, `json`, `hashlib`
- **Frontend Console:** Vanilla JavaScript (ES6+), HTML5, Vanilla CSS, WebSockets (strictly no TypeScript)
- **Testing:** `pytest 9.1`, `pytest-asyncio`
- **LLM Integration:** OpenRouter OpenAI-compatible API (`base_url="https://openrouter.ai/api/v1"`) with deterministic fallback
