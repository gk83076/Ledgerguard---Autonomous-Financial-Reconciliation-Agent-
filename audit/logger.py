"""
Cryptographic Audit Logger & Report Generator for LedgerGuard.
Creates tamper-evident SHA-256 chained event logs and publication-ready audit reports.
"""

import os
import json
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from runtime.models import AuditRecord, StepPhase, VerificationResult

GENESIS_HASH = "0" * 64

class AuditLogger:
    def __init__(self, artifacts_dir: Optional[str] = None):
        self.artifacts_dir = artifacts_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "audit_artifacts"
        )
        os.makedirs(self.artifacts_dir, exist_ok=True)
        self.log_file = os.path.join(self.artifacts_dir, "audit_trail.jsonl")
        self.records: List[AuditRecord] = []
        self._load_or_init()

    def _load_or_init(self):
        self.records = []
        if os.path.exists(self.log_file):
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            self.records.append(AuditRecord(**data))
                        except Exception:
                            pass

    def log(
        self,
        phase: StepPhase,
        action: str,
        target: str,
        details: Dict[str, Any],
        actor: str = "LedgerGuard Agent",
        screenshot: Optional[str] = None
    ) -> AuditRecord:
        """Appends a new cryptographically chained audit record."""
        prev_hash = self.records[-1].current_hash if self.records else GENESIS_HASH
        timestamp = datetime.now(timezone.utc).isoformat()
        step_number = len(self.records) + 1

        payload_bytes = f"{prev_hash}|{step_number}|{timestamp}|{phase.value}|{action}|{actor}|{target}|{json.dumps(details, sort_keys=True, default=str)}".encode("utf-8")
        current_hash = hashlib.sha256(payload_bytes).hexdigest()

        record = AuditRecord(
            step_number=step_number,
            timestamp=timestamp,
            phase=phase,
            action=action,
            actor=actor,
            target=target,
            details=details,
            screenshot=screenshot,
            previous_hash=prev_hash,
            current_hash=current_hash
        )

        self.records.append(record)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record.model_dump(), default=str) + "\n")

        return record

    def verify_integrity(self) -> bool:
        """Validates that the cryptographic hash chain has not been tampered with."""
        if not self.records:
            return True

        expected_prev = GENESIS_HASH
        for rec in self.records:
            if rec.previous_hash != expected_prev:
                return False
            payload_bytes = f"{rec.previous_hash}|{rec.step_number}|{rec.timestamp}|{rec.phase.value}|{rec.action}|{rec.actor}|{rec.target}|{json.dumps(rec.details, sort_keys=True, default=str)}".encode("utf-8")
            calculated_hash = hashlib.sha256(payload_bytes).hexdigest()
            if calculated_hash != rec.current_hash:
                return False
            expected_prev = rec.current_hash
        return True

    def export_report_html(self, verification: Optional[VerificationResult] = None) -> str:
        """Generates a standalone, beautiful HTML audit report."""
        report_path = os.path.join(self.artifacts_dir, "reconciliation_audit_report.html")

        records_html = ""
        for r in self.records:
            screenshot_snippet = ""
            if r.screenshot and os.path.exists(r.screenshot):
                rel_path = os.path.relpath(r.screenshot, self.artifacts_dir)
                screenshot_snippet = f"""
                <div class="evidence-box">
                    <span class="evidence-tag">Visual Proof Capture</span>
                    <a href="{rel_path}" target="_blank">
                        <img src="{rel_path}" alt="Proof" class="evidence-thumb" />
                    </a>
                </div>
                """

            records_html += f"""
            <tr class="phase-{r.phase.value.lower()}">
                <td><strong>#{r.step_number}</strong></td>
                <td><span class="badge badge-phase">{r.phase.value}</span></td>
                <td>{r.action}</td>
                <td><code>{r.target}</code></td>
                <td><small>{r.actor}</small></td>
                <td><pre class="details-pre">{json.dumps(r.details, indent=2, default=str)}</pre>{screenshot_snippet}</td>
                <td class="hash-cell" title="{r.current_hash}">{r.current_hash[:12]}...</td>
            </tr>
            """

        verif_summary = ""
        if verification:
            verif_summary = f"""
            <div class="verif-banner {'verif-pass' if verification.verified else 'verif-fail'}">
                <h3>Verification Status: {'PASSED ✓' if verification.verified else 'FAILED ✗'}</h3>
                <p>{verification.summary}</p>
                <div class="verif-stats">
                    <div><span>Total Bank Debits:</span> <strong>${verification.total_bank_debits:.2f}</strong></div>
                    <div><span>Total Settled:</span> <strong>${verification.total_settled_amount:.2f}</strong></div>
                    <div><span>Total Disputed:</span> <strong>${verification.total_disputed_amount:.2f}</strong></div>
                    <div><span>Unbalanced Delta:</span> <strong>${verification.unbalanced_delta:.2f}</strong></div>
                </div>
            </div>
            """

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>LedgerGuard Audit & Proof of Work Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; padding: 2rem; }}
        .report-header {{ border-bottom: 1px solid #334155; padding-bottom: 1.5rem; margin-bottom: 2rem; }}
        h1 {{ margin: 0; color: #38bdf8; }}
        .meta {{ color: #94a3b8; font-size: 14px; margin-top: 6px; }}
        .verif-banner {{ padding: 1.25rem; border-radius: 8px; margin-bottom: 2rem; }}
        .verif-pass {{ background: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; }}
        .verif-fail {{ background: rgba(244, 63, 94, 0.15); border: 1px solid #f43f5e; }}
        .verif-stats {{ display: flex; gap: 2rem; margin-top: 1rem; font-size: 14px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
        th, td {{ padding: 12px 14px; border-bottom: 1px solid #1e293b; text-align: left; vertical-align: top; font-size: 13px; }}
        th {{ background: #1e293b; color: #94a3b8; font-size: 11px; text-transform: uppercase; }}
        .badge-phase {{ background: #2563eb; color: #fff; padding: 2px 8px; border-radius: 4px; font-size: 11px; }}
        .details-pre {{ background: #090d16; padding: 8px; border-radius: 4px; color: #cbd5e1; font-size: 11px; max-width: 450px; overflow-x: auto; }}
        .hash-cell {{ font-family: monospace; color: #a855f7; font-size: 11px; }}
        .evidence-thumb {{ max-width: 140px; border-radius: 4px; border: 1px solid #334155; margin-top: 6px; display: block; }}
        .evidence-tag {{ font-size: 10px; color: #38bdf8; display: block; }}
    </style>
</head>
<body>
    <div class="report-header">
        <h1>🛡️ LedgerGuard Audit Trail & Cryptographic Proof-of-Work</h1>
        <div class="meta">Generated: {datetime.now(timezone.utc).isoformat()} | Chained Cryptographic Verification: {'VALID ✓' if self.verify_integrity() else 'INVALID ✗'}</div>
    </div>
    {verif_summary}
    <h2>Execution Step Ledger ({len(self.records)} Events)</h2>
    <table>
        <thead>
            <tr>
                <th>Step</th>
                <th>Phase</th>
                <th>Action</th>
                <th>Target</th>
                <th>Actor</th>
                <th>Details & Visual Evidence</th>
                <th>SHA-256 Hash</th>
            </tr>
        </thead>
        <tbody>
            {records_html}
        </tbody>
    </table>
</body>
</html>
        """

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        return report_path
