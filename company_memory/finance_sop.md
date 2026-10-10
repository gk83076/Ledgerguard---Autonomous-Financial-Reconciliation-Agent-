# STANDARD OPERATING PROCEDURE (SOP)
## Document ID: SOP-FIN-001 (Rev 4.2)
### Title: Autonomous & Semi-Autonomous Accounts Payable Reconciliation and Dispute Management
**Effective Date:** October 1, 2026  
**Audience:** Finance Operations, AI Autonomous Operators, Controllership

---

### 1. Purpose & Objective
This SOP defines the mandated procedures, permission boundaries, and operational safeguards for automating the reconciliation of weekly vendor payouts from banking clearinghouse records against our internal Enterprise Resource Planning (ERP) billing portal.

---

### 2. Regulatory & Operational Scope
This procedure applies to all commercial payouts, software vendor remittances, logistics disbursements, and contractor settlement batches processed through the Corporate Operations Account.

---

### 3. Financial Authorization Matrix & Governance Tiers

| Tier | Payout Amount (USD) | Variance Allowed | Authorized Actor | Action Protocol |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1 (Autonomous Micro)** | $\le \$1,000.00$ | $\le \$0.05$ (Rounding) | AI Autonomous Operator | Auto-reconcile & settle immediately in ERP without human sign-off. |
| **Tier 2 (Manager Gate)** | $>\$1,000.00$ and $\le \$10,000.00$ | $\$0.00$ | Operations Manager (HITL) | Pause execution. Emit approval request payload. Requires digital sign-off. |
| **Tier 3 (Executive Gate)** | $>\$10,000.00$ | $\$0.00$ | VP of Finance / CFO | Hard stop. Requires multi-signature sign-off and secondary compliance check. |

---

### 4. Matching Rules & Variance Tolerances

#### 4.1 Perfect Match
- When Bank Payout Net Amount exactly equals ERP Approved Invoice Net Amount and Vendor Tax ID matches:
  - If Amount $\le \$1,000.00$: **Auto-reconcile**.
  - If Amount $> \$1,000.00$: **Route to HITL Approval Gate**.

#### 4.2 Micro Variance Tolerance
- A variance of up to **$\$0.05$** is allowable due to banking rounding conventions.
- The operator is authorized to record the delta against the `9990-ROUNDING-VARIANCE` ledger and proceed under normal Tier 1 limits.

#### 4.3 Material Discrepancy ($\Delta > \$0.05$)
- **STRICT PROHIBITION:** Never settle or match an invoice with an unexplained variance $> \$0.05$.
- Mandated Protocol:
  1. Place invoice into `Disputed` status in the ERP portal.
  2. Record a structured dispute ticket citing:
     - Bank Reference ID
     - ERP Invoice Number
     - Expected Amount vs Billed Amount
     - Calculated Delta
  3. Attach audit evidence and notify Vendor Management.

#### 4.4 Unrecognized Payouts (Missing in ERP)
- If a bank transaction has no matching invoice record in the ERP:
  - Do NOT create arbitrary records.
  - Flag transaction as `UNRECOGNIZED_BANK_TRANSACTION`.
  - Escalate to Controllership via High-Priority HITL alert.

---

### 5. Verification & Audit Standards
1. **Double-Entry Balance Check:** The sum of all bank debits must strictly equal the sum of settled invoices plus disputed amounts plus rounding delta:
   $$\sum \text{Bank Debits} = \sum \text{Settled} + \sum \text{Disputed} + \Delta_{\text{tolerance}}$$
2. **Post-State UI Verification:** Following any mutating browser click (e.g. "Match & Settle"), the operator must re-read the invoice DOM to confirm status transitioned to `Reconciled`.
3. **Tamper-Evident Proof of Work:** Every executed batch must produce an immutable audit log with cryptographic hash verification and timestamped screenshot captures.
