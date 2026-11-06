/**
 * ZeroShield: Flow Details & Deep Anomaly Inspection Modal
 * Provides feature-level attribution, class probability breakdowns,
 * and novelty score deviation vs validation calibrated threshold.
 */

const FlowInspector = {
  modalInstance: null,

  init() {
    const el = document.getElementById("flowDetailsModal");
    if (el && typeof bootstrap !== "undefined") {
      this.modalInstance = new bootstrap.Modal(el);
    }
  },

  inspect(flow) {
    if (!flow) return;

    // Ensure bootstrap modal instance exists
    if (!this.modalInstance) {
      const el = document.getElementById("flowDetailsModal");
      if (el) this.modalInstance = new bootstrap.Modal(el);
    }

    // Header ID
    document.getElementById("modalFlowId").textContent = `Flow Inspection: ${flow.flow_id}`;

    // Verdict Banner
    const banner = document.getElementById("modalVerdictBanner");
    const verdictText = document.getElementById("modalVerdictText");
    const energyScore = document.getElementById("modalEnergyScore");

    energyScore.textContent = `${flow.novelty_score.toFixed(4)} (Threshold: ${flow.threshold.toFixed(4)})`;

    if (flow.verdict === "Potential Zero-Day") {
      banner.style.backgroundColor = "rgba(239, 68, 68, 0.2)";
      banner.style.border = "1px solid rgba(239, 68, 68, 0.6)";
      verdictText.className = "fw-bold mb-0 text-danger";
      verdictText.innerHTML = `<i class="fa-solid fa-radiation text-danger me-2"></i> Potential Zero-Day Exploit (Novel Anomaly)`;
      energyScore.className = "fw-bold mb-0 text-danger";
    } else if (flow.verdict === "Known Attack") {
      banner.style.backgroundColor = "rgba(245, 158, 11, 0.2)";
      banner.style.border = "1px solid rgba(245, 158, 11, 0.6)";
      verdictText.className = "fw-bold mb-0 text-warning";
      verdictText.innerHTML = `<i class="fa-solid fa-triangle-exclamation text-warning me-2"></i> Known Attack Signature: ${flow.predicted_class}`;
      energyScore.className = "fw-bold mb-0 text-warning";
    } else {
      banner.style.backgroundColor = "rgba(16, 185, 129, 0.15)";
      banner.style.border = "1px solid rgba(16, 185, 129, 0.5)";
      verdictText.className = "fw-bold mb-0 text-success";
      verdictText.innerHTML = `<i class="fa-solid fa-circle-check text-success me-2"></i> Benign Enterprise Traffic`;
      energyScore.className = "fw-bold mb-0 text-success";
    }

    // 1. Render Probabilities Chart
    if (flow.class_probabilities) {
      CyberCharts.renderModalProbabilities(flow.class_probabilities);
    }

    // 2. Render Top Contributing Features List
    const topFeatList = document.getElementById("modalTopFeaturesList");
    if (topFeatList) {
      topFeatList.innerHTML = "";
      if (flow.top_features && Object.keys(flow.top_features).length > 0) {
        Object.entries(flow.top_features).forEach(([feat, score]) => {
          const pct = Math.round(score * 100);
          const div = document.createElement("div");
          div.className = "mb-2";
          div.innerHTML = `
            <div class="d-flex justify-content-between mb-1">
              <span class="text-secondary"><code>${feat}</code></span>
              <span class="text-info fw-bold">${pct}% contribution</span>
            </div>
            <div class="progress" style="height: 5px; background: rgba(30, 41, 59, 0.8);">
              <div class="progress-bar bg-info" role="progressbar" style="width: ${pct}%"></div>
            </div>
          `;
          topFeatList.appendChild(div);
        });
      } else {
        topFeatList.innerHTML = `<span class="text-muted">Feature contributions not available.</span>`;
      }
    }

    // 3. Render Raw Features Grid
    const rawTable = document.getElementById("modalRawFeaturesTable");
    if (rawTable && flow.raw_features) {
      rawTable.innerHTML = "";
      const entries = Object.entries(flow.raw_features);

      // Render 2 columns of key-values
      for (let i = 0; i < entries.length; i += 2) {
        const [k1, v1] = entries[i];
        const [k2, v2] = entries[i + 1] || ["-", "-"];

        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td class="text-muted" style="width: 25%;"><strong>${k1}</strong></td>
          <td class="text-light" style="width: 25%;"><code>${v1}</code></td>
          <td class="text-muted" style="width: 25%;"><strong>${k2}</strong></td>
          <td class="text-light" style="width: 25%;"><code>${v2}</code></td>
        `;
        rawTable.appendChild(tr);
      }
    }

    if (this.modalInstance) {
      this.modalInstance.show();
    }
  }
};
