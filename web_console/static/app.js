// LedgerGuard Operator Console Client (Pure Vanilla JavaScript)
document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const btnDeploy = document.getElementById("btn-deploy-agent");
  const goalInput = document.getElementById("goal-input");
  const chkAutoApprove = document.getElementById("chk-auto-approve");
  const chkHeadless = document.getElementById("chk-headless");
  const scenarioButtons = document.querySelectorAll(".btn-scenario");
  const runtimeStatusDot = document.querySelector("#agent-runtime-status .status-dot");
  const runtimeStatusText = document.querySelector("#agent-runtime-status .status-text");
  const wsBadge = document.getElementById("ws-status-badge");
  const logContainer = document.getElementById("log-stream-container");
  const eventCounter = document.getElementById("event-counter");
  const hitlBadge = document.getElementById("hitl-badge");
  const hitlContainer = document.getElementById("hitl-requests-container");
  const evidenceViewer = document.getElementById("evidence-viewer");

  // Verification elements
  const valBankDebits = document.getElementById("val-bank-debits");
  const valSettled = document.getElementById("val-settled");
  const valDisputed = document.getElementById("val-disputed");
  const valDelta = document.getElementById("val-delta");
  const verifStatusBadge = document.getElementById("verif-status-badge");
  const checkUiDom = document.getElementById("check-ui-dom");
  const checkDoubleEntry = document.getElementById("check-double-entry");
  const checkHashChain = document.getElementById("check-hash-chain");

  let totalEvents = 0;
  let socket = null;

  // Scenario Presets
  const SCENARIOS = {
    full: {
      goal: "Reconcile vendor payouts from last week's CSV against internal ERP portal, flag discrepancies, draft dispute tickets, and process undisputed batches under $1,000.",
      autoApprove: false
    },
    auto: {
      goal: "Execute end-to-end zero-touch reconciliation with pre-authorized managerial sign-off for payouts exceeding $1,000.",
      autoApprove: true
    },
    chaos: {
      goal: "Reconcile vendor payouts under active DOM chaos conditions. Test multi-tier resilient locator adaptation.",
      autoApprove: true
    }
  };

  // Scenario Switcher
  scenarioButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      scenarioButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const key = btn.getAttribute("data-scenario");
      if (SCENARIOS[key]) {
        goalInput.value = SCENARIOS[key].goal;
        chkAutoApprove.checked = SCENARIOS[key].autoApprove;
      }
    });
  });

  // Telemetry Log Appender
  function appendLog(phase, action, details) {
    totalEvents++;
    if (eventCounter) eventCounter.textContent = `${totalEvents} Events`;

    const now = new Date();
    const timeStr = now.toTimeString().split(" ")[0];

    const entry = document.createElement("div");
    entry.className = "log-entry";

    const badgeClass = `badge-${(phase || "sys").toLowerCase()}`;

    let detailsSnip = "";
    if (details && Object.keys(details).length > 0) {
      const summary = typeof details === "string" ? details : JSON.stringify(details);
      detailsSnip = `<small style="color:#94a3b8; display:block; margin-top:2px;">${summary.slice(0, 120)}</small>`;
    }

    entry.innerHTML = `
      <span class="log-time">${timeStr}</span>
      <span class="log-badge ${badgeClass}">${phase || "INFO"}</span>
      <div class="log-msg">
        <strong>${action}</strong>
        ${detailsSnip}
      </div>
    `;

    logContainer.appendChild(entry);
    logContainer.scrollTop = logContainer.scrollHeight;
  }

  // Update Pipeline Visual Stages
  function updatePipelineStage(activePhase) {
    const stageElements = document.querySelectorAll(".stage-step");
    const phaseOrder = [
      "UNDERSTAND", "PLAN", "INGEST", "CONNECT",
      "POLICY_CHECK", "EXECUTE", "ADAPT", "VERIFY"
    ];

    const activeIndex = phaseOrder.indexOf(activePhase);

    stageElements.forEach((el) => {
      const stageName = el.getAttribute("data-stage");
      const idx = phaseOrder.indexOf(stageName);

      if (idx < activeIndex) {
        el.className = "stage-step completed";
      } else if (idx === activeIndex) {
        el.className = "stage-step active";
      } else {
        el.className = "stage-step";
      }
    });
  }

  // Set Runtime Status
  function setRuntimeStatus(status) {
    if (!runtimeStatusDot || !runtimeStatusText) return;

    runtimeStatusDot.className = "status-dot";
    if (status === "IN_PROGRESS") {
      runtimeStatusDot.classList.add("dot-active");
      runtimeStatusText.textContent = "OPERATOR RUNNING";
    } else if (status === "WAITING_APPROVAL") {
      runtimeStatusDot.classList.add("dot-waiting");
      runtimeStatusText.textContent = "WAITING APPROVAL";
    } else if (status === "COMPLETED") {
      runtimeStatusDot.classList.add("dot-complete");
      runtimeStatusText.textContent = "OPERATOR COMPLETE";
    } else if (status === "FAILED") {
      runtimeStatusDot.classList.add("dot-failed");
      runtimeStatusText.textContent = "OPERATOR FAILED";
    } else {
      runtimeStatusDot.classList.add("dot-idle");
      runtimeStatusText.textContent = "OPERATOR IDLE";
    }
  }

  // Render HITL Approval Request
  function renderApprovalRequest(req) {
    hitlContainer.innerHTML = "";
    hitlBadge.textContent = "1 Pending Sign-off";
    hitlBadge.style.background = "rgba(244, 63, 94, 0.2)";
    hitlBadge.style.color = "#fb7185";

    const box = document.createElement("div");
    box.className = "hitl-request-box";
    box.id = `approval-box-${req.approval_id}`;

    box.innerHTML = `
      <div class="hitl-req-header">
        <div class="hitl-req-title">
          <strong>${req.vendor_name} (${req.invoice_id})</strong>
          <small>Banking Clearinghouse Ref: ${req.payout_id}</small>
        </div>
        <div class="hitl-amount-box">$${parseFloat(req.amount).toFixed(2)}</div>
      </div>
      <div class="hitl-policy-citation">
        <strong>⚠️ Policy Exception:</strong> ${req.policy_citation}
      </div>
      <div class="hitl-actions">
        <button class="btn btn-sm btn-danger btn-reject" data-id="${req.approval_id}">
          Reject & Open Dispute
        </button>
        <button class="btn btn-sm btn-success btn-approve" data-id="${req.approval_id}">
          ✓ Authorize & Settle Payout
        </button>
      </div>
    `;

    hitlContainer.appendChild(box);

    // Event listeners
    box.querySelector(".btn-approve").addEventListener("click", () => handleDecision(req.approval_id, "APPROVE"));
    box.querySelector(".btn-reject").addEventListener("click", () => handleDecision(req.approval_id, "REJECT"));
  }

  // Handle Decision
  async function handleDecision(approvalId, decision) {
    try {
      const res = await fetch(`/api/approvals/${approvalId}/decision`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision: decision, notes: `Decided via Operator Console (${decision})` })
      });
      const data = await res.json();
      if (data.success) {
        appendLog("POLICY_CHECK", `Operator Sign-Off Recorded: ${decision} for ${approvalId}`, {});
        hitlContainer.innerHTML = `
          <div class="hitl-idle-state">
            <span class="idle-shield">✅</span>
            <p>Decision '${decision}' recorded in cryptographic audit ledger.</p>
            <small>AI Operator continuing execution pipeline...</small>
          </div>
        `;
        hitlBadge.textContent = "0 Pending Approvals";
        hitlBadge.style.background = "";
        hitlBadge.style.color = "";
      }
    } catch (e) {
      appendLog("ERROR", `Failed to record approval decision: ${e}`, {});
    }
  }

  // Update Verification UI
  function updateVerification(v) {
    if (!v) return;

    if (valBankDebits) valBankDebits.textContent = `$${parseFloat(v.total_bank_debits).toFixed(2)}`;
    if (valSettled) valSettled.textContent = `$${parseFloat(v.total_settled_amount).toFixed(2)}`;
    if (valDisputed) valDisputed.textContent = `$${parseFloat(v.total_disputed_amount).toFixed(2)}`;
    if (valDelta) valDelta.textContent = `$${parseFloat(v.unbalanced_delta).toFixed(2)}`;

    if (verifStatusBadge) {
      verifStatusBadge.textContent = v.verified ? "VERIFIED ✓" : "UNVERIFIED ✗";
      verifStatusBadge.className = `verif-tag-pill ${v.verified ? "verif-tag-pass" : ""}`;
    }

    if (checkUiDom && v.erp_ui_verified) {
      checkUiDom.className = "check-item pass";
      checkUiDom.querySelector(".check-icon").textContent = "✅";
    }

    if (checkDoubleEntry && parseFloat(v.unbalanced_delta) <= 0.05) {
      checkDoubleEntry.className = "check-item pass";
      checkDoubleEntry.querySelector(".check-icon").textContent = "✅";
    }

    if (checkHashChain && v.audit_hash_verified) {
      checkHashChain.className = "check-item pass";
      checkHashChain.querySelector(".check-icon").textContent = "✅";
    }
  }

  // Display Evidence Screenshot
  function updateEvidence(screenshotPath) {
    if (!screenshotPath) return;
    const filename = screenshotPath.split(/[\\/]/).pop();
    evidenceViewer.innerHTML = `
      <img src="/api/evidence/${filename}" alt="Evidence" class="evidence-img-main" title="Click to view full resolution" />
    `;
    evidenceViewer.querySelector("img").addEventListener("click", () => {
      window.open(`/api/evidence/${filename}`, "_blank");
    });
  }

  // WebSocket Connection
  function initWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      if (wsBadge) {
        wsBadge.className = "ws-badge connected";
        wsBadge.querySelector("span:last-child").textContent = "Telemetry Live";
      }
    };

    socket.onclose = () => {
      if (wsBadge) {
        wsBadge.className = "ws-badge";
        wsBadge.querySelector("span:last-child").textContent = "Offline (Reconnecting)";
      }
      setTimeout(initWebSocket, 2000);
    };

    socket.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "AGENT_EVENT") {
          const payload = msg.payload;
          appendLog(payload.phase, payload.action, payload.details);
          updatePipelineStage(payload.phase);
          setRuntimeStatus(payload.status);

          // Handle Approval Waiting
          if (payload.status === "WAITING_APPROVAL" && payload.details) {
            renderApprovalRequest(payload.details);
          }

          // Check if evidence screenshot path exists
          if (payload.details && (payload.details.screenshot || payload.details.screenshot_path)) {
            updateEvidence(payload.details.screenshot || payload.details.screenshot_path);
          }

          // Complete phase verification update
          if (payload.phase === "VERIFY" && payload.details) {
            updateVerification(payload.details);
          }
        } else if (msg.type === "APPROVAL_DECIDED") {
          appendLog("HITL", `Approval decided: ${msg.payload.operator_decision}`, {});
        }
      } catch (err) {
        console.error("WS Parse error", err);
      }
    };
  }

  initWebSocket();

  // Deploy AI Employee Button Handler
  if (btnDeploy) {
    btnDeploy.addEventListener("click", async () => {
      btnDeploy.disabled = true;
      btnDeploy.textContent = "⚙️ Executing Loop...";

      const goal = goalInput.value.trim();
      const autoApprove = chkAutoApprove.checked;
      const headless = chkHeadless.checked;

      setRuntimeStatus("IN_PROGRESS");
      appendLog("SYSTEM", "Dispatching goal to LedgerGuard autonomous runtime...", { goal: goal });

      try {
        const res = await fetch("/api/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ goal: goal, auto_approve: autoApprove, headless: headless })
        });
        const data = await res.json();
        if (res.ok) {
          appendLog("SYSTEM", `Task initialized with ID ${data.task_id}`, {});
        } else {
          appendLog("ERROR", data.detail || "Dispatch failed", {});
          setRuntimeStatus("FAILED");
          btnDeploy.disabled = false;
          btnDeploy.textContent = "🚀 Deploy AI Employee";
        }
      } catch (err) {
        appendLog("ERROR", `Network failure: ${err}`, {});
        setRuntimeStatus("FAILED");
        btnDeploy.disabled = false;
        btnDeploy.textContent = "🚀 Deploy AI Employee";
      } finally {
        setTimeout(() => {
          btnDeploy.disabled = false;
          btnDeploy.textContent = "🚀 Deploy AI Employee";
        }, 8000);
      }
    });
  }
});
