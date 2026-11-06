/**
 * ZeroShield: Core Application Controller
 * Coordinates page navigation, asynchronous data loaders, threshold synchronization,
 * and security alert history pagination.
 */

const app = {
  currentView: "dashboard",
  currentAlertPage: 1,
  totalAlertPages: 1,
  modelInfo: null,
  kpiStats: {
    totalFlows: 0,
    benignCount: 0,
    knownAttacks: 0,
    zeroDays: 0
  },

  init() {
    this.setupNavigation();
    this.setupThresholdControls();
    this.setupAlertFilters();

    // Initialize submodules
    CyberCharts.initAll();
    TrafficStreamer.init();
    BatchAnalyzer.init();
    FlowInspector.init();

    // Load API data
    this.loadModelInfo();
    this.loadStats();
    this.loadAlerts(1);
    this.loadPerformanceMetrics();

    // Auto-refresh stats periodically
    setInterval(() => {
      this.loadStats();
    }, 15000);
  },

  setupNavigation() {
    document.querySelectorAll("#sidebar .nav-link").forEach(link => {
      link.addEventListener("click", (e) => {
        e.preventDefault();
        const targetView = link.dataset.view;
        this.switchView(targetView);
      });
    });
  },

  switchView(viewName) {
    this.currentView = viewName;

    // Update active nav link
    document.querySelectorAll("#sidebar .nav-link").forEach(l => l.classList.remove("active"));
    const activeLink = document.getElementById(`nav-${viewName}`);
    if (activeLink) activeLink.classList.add("active");

    // Hide all view panels
    document.querySelectorAll(".view-panel").forEach(panel => panel.classList.add("d-none"));

    // Show target view panel
    const targetPanel = document.getElementById(`view-${viewName}`);
    if (targetPanel) targetPanel.classList.remove("d-none");

    // Update header heading
    const headingMap = {
      dashboard: "Operations Dashboard",
      monitor: "Live Traffic Stream Monitor",
      upload: "Batch Flow Ingestion & Analyzer",
      alerts: "Security Alert Logs & Audit Trail",
      performance: "Model Performance & LOAO Benchmarks",
      architecture: "System Pipeline & Energy Score Architecture"
    };
    document.getElementById("page-heading").textContent = headingMap[viewName] || "ZeroShield Console";

    if (viewName === "performance") {
      this.loadPerformanceMetrics();
    }
  },

  async loadModelInfo() {
    try {
      const res = await fetch("/api/model-info");
      if (!res.ok) return;
      const data = await res.json();
      this.modelInfo = data;

      // Update Top Banner & Threshold display
      const topBadge = document.getElementById("top-threshold-badge");
      if (topBadge) topBadge.textContent = data.current_runtime_threshold.toFixed(4);

      const slider = document.getElementById("threshold-slider");
      const sliderVal = document.getElementById("slider-threshold-val");
      if (slider && sliderVal) {
        slider.value = data.current_runtime_threshold;
        sliderVal.textContent = data.current_runtime_threshold.toFixed(4);
      }

      // Sidebar model info
      const sbInfo = document.getElementById("sidebar-model-info");
      if (sbInfo) sbInfo.textContent = `Model: ${data.model_name} (${data.parameters.toLocaleString()} params)`;

      // Dataset indicator
      const dsBadge = document.getElementById("dataset-status-text");
      const synthBanner = document.getElementById("synthetic-notice-banner");
      if (data.is_synthetic) {
        if (dsBadge) dsBadge.textContent = "Synthetic CIC-IDS2017";
        if (synthBanner) synthBanner.classList.remove("d-none");
      } else {
        if (dsBadge) dsBadge.textContent = "Production Capture";
        if (synthBanner) synthBanner.classList.add("d-none");
      }
    } catch (err) {
      console.warn("Error fetching model info:", err);
    }
  },

  async loadStats() {
    try {
      const res = await fetch("/api/stats");
      if (!res.ok) return;
      const stats = await res.json();

      this.kpiStats.totalFlows = stats.total_flows_analyzed;
      this.kpiStats.benignCount = stats.benign_alerts;
      this.kpiStats.knownAttacks = stats.known_attack_alerts;
      this.kpiStats.zeroDays = stats.zero_day_alerts;

      document.getElementById("kpi-total-flows").textContent = stats.total_flows_analyzed.toLocaleString();
      document.getElementById("kpi-benign-pct").textContent = `${stats.benign_percentage}%`;
      document.getElementById("kpi-known-attacks").textContent = stats.known_attack_alerts.toLocaleString();
      document.getElementById("kpi-zero-days").textContent = stats.zero_day_alerts.toLocaleString();
      document.getElementById("kpi-latency").textContent = `${stats.avg_latency_ms}ms`;
    } catch (err) {
      console.warn("Error loading KPI stats:", err);
    }
  },

  incrementKPIs(flow) {
    this.kpiStats.totalFlows += 1;
    if (flow.verdict === "Benign") {
      this.kpiStats.benignCount += 1;
    } else if (flow.verdict === "Potential Zero-Day") {
      this.kpiStats.zeroDays += 1;
    } else {
      this.kpiStats.knownAttacks += 1;
    }

    const total = this.kpiStats.totalFlows;
    const benignPct = ((this.kpiStats.benignCount / Math.max(total, 1)) * 100).toFixed(1);

    document.getElementById("kpi-total-flows").textContent = total.toLocaleString();
    document.getElementById("kpi-benign-pct").textContent = `${benignPct}%`;
    document.getElementById("kpi-known-attacks").textContent = this.kpiStats.knownAttacks.toLocaleString();
    document.getElementById("kpi-zero-days").textContent = this.kpiStats.zeroDays.toLocaleString();
  },

  setupThresholdControls() {
    const slider = document.getElementById("threshold-slider");
    const sliderVal = document.getElementById("slider-threshold-val");
    const saveBtn = document.getElementById("btn-save-threshold");

    if (slider && sliderVal) {
      slider.addEventListener("input", (e) => {
        const val = parseFloat(e.target.value);
        sliderVal.textContent = val.toFixed(4);
      });
    }

    if (saveBtn && slider) {
      saveBtn.addEventListener("click", async () => {
        const newThresh = parseFloat(slider.value);
        saveBtn.disabled = true;
        saveBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin me-1"></i> Saving...`;

        try {
          const res = await fetch("/api/threshold", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ threshold: newThresh })
          });

          if (!res.ok) throw new Error("Failed to save threshold.");

          document.getElementById("top-threshold-badge").textContent = newThresh.toFixed(4);
          saveBtn.innerHTML = `<i class="fa-solid fa-check me-1"></i> Applied!`;
          setTimeout(() => {
            saveBtn.disabled = false;
            saveBtn.innerHTML = `<i class="fa-solid fa-floppy-disk me-1"></i> Apply & Save`;
          }, 1500);
        } catch (err) {
          alert(`Error saving threshold: ${err.message}`);
          saveBtn.disabled = false;
          saveBtn.innerHTML = `<i class="fa-solid fa-floppy-disk me-1"></i> Apply & Save`;
        }
      });
    }
  },

  setupAlertFilters() {
    const sevFilter = document.getElementById("alert-severity-filter");
    const verFilter = document.getElementById("alert-verdict-filter");
    const prevBtn = document.getElementById("btn-prev-alerts");
    const nextBtn = document.getElementById("btn-next-alerts");

    if (sevFilter) sevFilter.addEventListener("change", () => this.loadAlerts(1));
    if (verFilter) verFilter.addEventListener("change", () => this.loadAlerts(1));

    if (prevBtn) {
      prevBtn.addEventListener("click", () => {
        if (this.currentAlertPage > 1) this.loadAlerts(this.currentAlertPage - 1);
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener("click", () => {
        if (this.currentAlertPage < this.totalAlertPages) this.loadAlerts(this.currentAlertPage + 1);
      });
    }
  },

  async loadAlerts(page = 1) {
    this.currentAlertPage = page;
    const sev = document.getElementById("alert-severity-filter")?.value || "all";
    const ver = document.getElementById("alert-verdict-filter")?.value || "all";

    const tbody = document.getElementById("alerts-page-tbody");
    if (!tbody) return;

    try {
      const res = await fetch(`/api/alerts?page=${page}&page_size=15&severity=${sev}&verdict=${ver}`);
      if (!res.ok) throw new Error("Failed to fetch alerts.");
      const data = await res.json();

      this.totalAlertPages = data.total_pages;
      const paginationInfo = document.getElementById("alerts-pagination-info");
      if (paginationInfo) {
        paginationInfo.textContent = `Showing page ${data.page} of ${data.total_pages} (${data.total_count} total alerts)`;
      }

      document.getElementById("btn-prev-alerts").disabled = data.page <= 1;
      document.getElementById("btn-next-alerts").disabled = data.page >= data.total_pages;

      if (!data.alerts || data.alerts.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted py-5">No security alerts recorded matching current criteria.</td></tr>`;
        return;
      }

      tbody.innerHTML = "";
      data.alerts.forEach(alert => {
        const tr = document.createElement("tr");

        let badgeHtml = "";
        if (alert.verdict === "Potential Zero-Day") {
          badgeHtml = `<span class="badge-verdict badge-zero-day"><span class="pulsing-dot dot-red"></span> Potential Zero-Day</span>`;
        } else {
          badgeHtml = `<span class="badge-verdict badge-known-attack">${alert.attack_class}</span>`;
        }

        const sevClass = alert.severity === "critical" ? "severity-critical" : "severity-high";

        tr.innerHTML = `
          <td class="text-secondary small">${alert.timestamp}</td>
          <td class="fw-bold">${alert.flow_id}</td>
          <td><span class="${sevClass} text-uppercase">${alert.severity}</span></td>
          <td>${badgeHtml}</td>
          <td>${alert.attack_class}</td>
          <td><strong class="text-danger">${alert.novelty_score.toFixed(4)}</strong></td>
          <td>
            <button class="btn btn-xs btn-outline-info py-0 px-2 btn-alert-inspect" style="font-size: 0.75rem;">
              Inspect
            </button>
          </td>
        `;

        tr.querySelector(".btn-alert-inspect").addEventListener("click", () => {
          // Construct flow object for inspector
          FlowInspector.inspect({
            flow_id: alert.flow_id,
            verdict: alert.verdict,
            predicted_class: alert.attack_class,
            novelty_score: alert.novelty_score,
            threshold: alert.threshold,
            confidence: alert.confidence,
            severity: alert.severity,
            class_probabilities: { [alert.attack_class]: alert.confidence },
            top_features: {
              packets_per_sec: 0.35,
              bytes_per_sec: 0.28,
              flow_duration: 0.20,
              packet_len_mean: 0.17
            },
            raw_features: alert.features || {
              protocol: alert.protocol,
              dst_port_category: alert.dst_port_category,
              flow_duration: alert.flow_duration,
              total_fwd_packets: alert.total_fwd_packets,
              total_bwd_packets: alert.total_bwd_packets,
              bytes_per_sec: alert.bytes_per_sec,
              packets_per_sec: alert.packets_per_sec
            }
          });
        });

        tbody.appendChild(tr);
      });
    } catch (err) {
      console.error("Error loading alerts:", err);
      tbody.innerHTML = `<tr><td colspan="7" class="text-center text-danger py-4">Error loading alerts: ${err.message}</td></tr>`;
    }
  },

  async loadPerformanceMetrics() {
    try {
      const res = await fetch("/api/metrics");
      if (!res.ok) return;
      const data = await res.json();

      // Summary KPIs
      if (data.model_summary && data.model_summary.FlowTransformer) {
        const ft = data.model_summary.FlowTransformer;
        document.getElementById("perf-mean-auroc").textContent = ft.mean_auroc.toFixed(4);
        document.getElementById("perf-mean-aupr").textContent = ft.mean_aupr.toFixed(4);
        document.getElementById("perf-mean-fpr").textContent = ft.mean_fpr95.toFixed(4);
        document.getElementById("perf-mean-f1").textContent = ft.mean_f1.toFixed(4);
      }

      // Render Bar Charts
      CyberCharts.renderPerformanceCharts(data);

      // Render LOAO Table
      const tbody = document.getElementById("loao-tbody");
      if (tbody && data.held_out_attacks) {
        tbody.innerHTML = "";
        Object.entries(data.held_out_attacks).forEach(([attack, models]) => {
          Object.entries(models).forEach(([modelName, metrics], idx) => {
            const tr = document.createElement("tr");
            const isFT = modelName === "FlowTransformer";
            const rowSpan = idx === 0 ? `<td rowspan="4" class="fw-bold align-middle bg-dark-subtle">${attack}</td>` : "";

            tr.innerHTML = `
              ${rowSpan}
              <td class="${isFT ? 'text-info fw-bold' : 'text-secondary'}">
                ${isFT ? '<i class="fa-solid fa-bolt me-1"></i>' : ''} ${modelName}
              </td>
              <td class="fw-bold ${isFT ? 'text-light' : ''}">${metrics.auroc.toFixed(4)}</td>
              <td>${metrics.aupr.toFixed(4)}</td>
              <td class="${metrics.fpr_at_95_tpr < 0.05 ? 'text-success' : 'text-danger'} fw-bold">${metrics.fpr_at_95_tpr.toFixed(4)}</td>
              <td>${metrics.macro_f1.toFixed(4)}</td>
            `;
            tbody.appendChild(tr);
          });
        });
      }
    } catch (err) {
      console.warn("Error loading evaluation metrics:", err);
    }
  }
};

// Initialize application on DOM ready
document.addEventListener("DOMContentLoaded", () => {
  app.init();
});
