// NexusERP Portal Client Logic (Pure Vanilla JavaScript)
document.addEventListener("DOMContentLoaded", () => {
  const tableBody = document.getElementById("invoices-table-body");
  const disputeModal = document.getElementById("dispute-modal");
  const btnCloseModal = document.getElementById("btn-close-modal");
  const btnCancelDispute = document.getElementById("btn-cancel-dispute");
  const btnSubmitDispute = document.getElementById("btn-submit-dispute");
  const modalInvoiceId = document.getElementById("modal-invoice-id");
  const modalTargetLabel = document.getElementById("modal-target-label");
  const modalBilledAmt = document.getElementById("modal-billed-amt");
  const modalExpectedAmt = document.getElementById("modal-expected-amt");
  const modalReason = document.getElementById("modal-reason");
  const modalNotes = document.getElementById("modal-notes");
  const vendorFilter = document.getElementById("vendor-filter");
  const invoiceSearch = document.getElementById("invoice-search");
  const chaosCheckbox = document.getElementById("chaos-mode-checkbox");
  const btnResetDb = document.getElementById("btn-reset-db");
  const toastContainer = document.getElementById("toast-container");

  // Show Toast
  function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    const icon = type === "success" ? "✅" : type === "error" ? "❌" : "ℹ️";
    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }

  // Update Summary Metrics
  function updateMetrics() {
    const rows = Array.from(document.querySelectorAll(".invoice-row"));
    const pendingCount = rows.filter(r => r.classList.contains("status-pending")).length;
    const reconciledCount = rows.filter(r => r.classList.contains("status-reconciled")).length;
    const disputedCount = rows.filter(r => r.classList.contains("status-disputed")).length;

    const elPending = document.getElementById("metric-pending");
    const elReconciled = document.getElementById("metric-reconciled");
    const elDisputed = document.getElementById("metric-disputed");

    if (elPending) elPending.textContent = pendingCount;
    if (elReconciled) elReconciled.textContent = reconciledCount;
    if (elDisputed) elDisputed.textContent = disputedCount;
  }

  // Handle Action Clicks (Settle & Dispute)
  if (tableBody) {
    tableBody.addEventListener("click", async (e) => {
      const settleBtn = e.target.closest(".action-settle");
      const disputeBtn = e.target.closest(".action-dispute");

      if (settleBtn) {
        const invoiceId = settleBtn.getAttribute("data-invoice-id");
        await handleSettle(invoiceId, settleBtn);
      } else if (disputeBtn) {
        const invoiceId = disputeBtn.getAttribute("data-invoice-id");
        const billedAmount = disputeBtn.getAttribute("data-net-amount");
        openDisputeModal(invoiceId, billedAmount);
      }
    });
  }

  // Settle Invoice via API
  async function handleSettle(invoiceId, buttonEl) {
    buttonEl.disabled = true;
    buttonEl.textContent = "Settling...";

    try {
      const response = await fetch(`/api/invoices/${invoiceId}/settle`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          payout_id: "AUTONOMOUS-DIRECT-SETTLE",
          bank_reference: `MATCHED-AP-${Date.now().toString().slice(-6)}`,
          reconciled_amount: 0.0,
          notes: "Settled via Portal Action"
        })
      });

      const data = await response.json();
      if (response.ok && data.success) {
        showToast(`Invoice ${invoiceId} marked as Reconciled`, "success");
        updateRowToReconciled(invoiceId, data.invoice.match_reference);
        updateMetrics();
      } else {
        showToast(data.detail || "Failed to settle invoice", "error");
        buttonEl.disabled = false;
        buttonEl.textContent = "Match & Settle";
      }
    } catch (err) {
      showToast("Network error during invoice settlement", "error");
      buttonEl.disabled = false;
      buttonEl.textContent = "Match & Settle";
    }
  }

  // Update DOM Row to Reconciled
  function updateRowToReconciled(invoiceId, matchRef) {
    const row = document.getElementById(`row-${invoiceId}`);
    if (!row) return;

    row.className = "invoice-row status-reconciled";
    const badge = document.getElementById(`status-badge-${invoiceId}`);
    if (badge) {
      badge.className = "badge badge-reconciled";
      badge.textContent = "Reconciled";
    }

    const refCell = row.querySelector(".cell-match-ref");
    if (refCell) {
      refCell.innerHTML = `<code class="ref-code">${matchRef || "RECONCILED"}</code>`;
    }

    const actionsCell = row.querySelector(".cell-actions");
    if (actionsCell) {
      actionsCell.innerHTML = `<span class="verified-tag">✓ Settled</span>`;
    }
  }

  // Open Dispute Modal
  function openDisputeModal(invoiceId, billedAmount) {
    modalInvoiceId.value = invoiceId;
    modalTargetLabel.textContent = `Invoice: ${invoiceId}`;
    modalBilledAmt.value = billedAmount || "";
    modalExpectedAmt.value = "";
    modalNotes.value = "";
    disputeModal.classList.remove("hidden");
  }

  function closeDisputeModal() {
    disputeModal.classList.add("hidden");
  }

  if (btnCloseModal) btnCloseModal.addEventListener("click", closeDisputeModal);
  if (btnCancelDispute) btnCancelDispute.addEventListener("click", closeDisputeModal);

  // Submit Dispute Ticket
  if (btnSubmitDispute) {
    btnSubmitDispute.addEventListener("click", async () => {
      const invoiceId = modalInvoiceId.value;
      const billed = parseFloat(modalBilledAmt.value) || 0;
      const expected = parseFloat(modalExpectedAmt.value) || billed;
      const discrepancy = Math.abs(billed - expected);
      const reason = modalReason.value;

      btnSubmitDispute.disabled = true;
      btnSubmitDispute.textContent = "Filing...";

      try {
        const response = await fetch(`/api/invoices/${invoiceId}/dispute`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            reason: reason,
            expected_amount: expected,
            billed_amount: billed,
            discrepancy: discrepancy,
            priority: "High"
          })
        });

        const data = await response.json();
        if (response.ok && data.success) {
          showToast(`Dispute ticket ${data.ticket.ticket_id} filed for ${invoiceId}`, "warning");
          updateRowToDisputed(invoiceId, data.ticket.ticket_id, discrepancy);
          closeDisputeModal();
          updateMetrics();
        } else {
          showToast(data.detail || "Failed to submit dispute", "error");
        }
      } catch (err) {
        showToast("Network error submitting dispute", "error");
      } finally {
        btnSubmitDispute.disabled = false;
        btnSubmitDispute.textContent = "Confirm & Open Dispute";
      }
    });
  }

  // Update DOM Row to Disputed
  function updateRowToDisputed(invoiceId, ticketId, discrepancy) {
    const row = document.getElementById(`row-${invoiceId}`);
    if (!row) return;

    row.className = "invoice-row status-disputed";
    const badge = document.getElementById(`status-badge-${invoiceId}`);
    if (badge) {
      badge.className = "badge badge-disputed";
      badge.textContent = "Disputed";
    }

    const refCell = row.querySelector(".cell-match-ref");
    if (refCell) {
      refCell.innerHTML = `<span class="dispute-snip" title="${ticketId}: Var $${discrepancy.toFixed(2)}">${ticketId}: Var $${discrepancy.toFixed(2)}</span>`;
    }

    const actionsCell = row.querySelector(".cell-actions");
    if (actionsCell) {
      actionsCell.innerHTML = `<span class="dispute-tag">⚠️ On Hold</span>`;
    }
  }

  // Filters & Search
  function applyFilters() {
    const selectedVendor = vendorFilter ? vendorFilter.value : "";
    const searchQuery = invoiceSearch ? invoiceSearch.value.trim().toLowerCase() : "";
    const rows = document.querySelectorAll(".invoice-row");

    rows.forEach(row => {
      const vendorId = row.getAttribute("data-vendor-id") || "";
      const invoiceId = (row.getAttribute("data-invoice-id") || "").toLowerCase();

      const matchVendor = !selectedVendor || vendorId === selectedVendor;
      const matchSearch = !searchQuery || invoiceId.includes(searchQuery);

      if (matchVendor && matchSearch) {
        row.style.display = "";
      } else {
        row.style.display = "none";
      }
    });
  }

  if (vendorFilter) vendorFilter.addEventListener("change", applyFilters);
  if (invoiceSearch) invoiceSearch.addEventListener("input", applyFilters);

  // Chaos Mode Toggle
  if (chaosCheckbox) {
    chaosCheckbox.addEventListener("change", async () => {
      try {
        const response = await fetch("/api/chaos/toggle", { method: "POST" });
        const data = await response.json();
        showToast(`Chaos Mode is now: ${data.chaos_mode ? "ENABLED (Mutated Selectors)" : "DISABLED"}`, "info");
        setTimeout(() => window.location.reload(), 600);
      } catch (err) {
        showToast("Could not toggle chaos mode", "error");
      }
    });
  }

  // Reset Database State
  if (btnResetDb) {
    btnResetDb.addEventListener("click", async () => {
      try {
        const response = await fetch("/api/reset", { method: "POST" });
        const data = await response.json();
        if (data.success) {
          showToast("ERP state restored to initial seed!", "success");
          setTimeout(() => window.location.reload(), 600);
        }
      } catch (err) {
        showToast("Failed to reset ERP state", "error");
      }
    });
  }
});
