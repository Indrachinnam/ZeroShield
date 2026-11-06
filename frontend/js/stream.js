/**
 * ZeroShield: Live Traffic Streaming Service
 * Manages Server-Sent Events (SSE) connection, flow table updaters, and live gauges.
 */

const TrafficStreamer = {
  eventSource: null,
  isStreaming: false,
  currentSpeed: 2.0,
  flowCount: 0,
  maxTableRows: 60,

  init() {
    const toggleBtn = document.getElementById("btn-stream-toggle");
    if (toggleBtn) {
      toggleBtn.addEventListener("click", () => this.toggleStream());
    }

    // Speed selector buttons
    document.querySelectorAll(".stream-speed-btn").forEach(btn => {
      btn.addEventListener("click", (e) => {
        document.querySelectorAll(".stream-speed-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        this.currentSpeed = parseFloat(btn.dataset.speed || 2.0);
        if (this.isStreaming) {
          this.stopStream();
          this.startStream();
        }
      });
    });
  },

  toggleStream() {
    if (this.isStreaming) {
      this.stopStream();
    } else {
      this.startStream();
    }
  },

  startStream() {
    const toggleBtn = document.getElementById("btn-stream-toggle");
    if (toggleBtn) {
      toggleBtn.innerHTML = `<i class="fa-solid fa-pause me-1"></i> Pause Stream`;
      toggleBtn.classList.replace("cyber-btn", "btn-warning");
    }

    const url = `/api/stream?flows_per_sec=${this.currentSpeed}`;
    this.eventSource = new EventSource(url);
    this.isStreaming = true;

    // Clear placeholder row if first time
    const tbody = document.getElementById("live-stream-tbody");
    if (tbody && this.flowCount === 0) {
      tbody.innerHTML = "";
    }

    this.eventSource.onmessage = (event) => {
      try {
        const flow = JSON.parse(event.data);
        this.handleIncomingFlow(flow);
      } catch (err) {
        console.error("Error parsing SSE flow message:", err);
      }
    };

    this.eventSource.onerror = (err) => {
      console.warn("SSE stream disconnected, retrying...", err);
    };
  },

  stopStream() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    this.isStreaming = false;

    const toggleBtn = document.getElementById("btn-stream-toggle");
    if (toggleBtn) {
      toggleBtn.innerHTML = `<i class="fa-solid fa-play me-1"></i> Start Live Stream`;
      toggleBtn.classList.replace("btn-warning", "cyber-btn");
    }
  },

  handleIncomingFlow(flow) {
    this.flowCount += 1;
    const counter = document.getElementById("stream-flow-counter");
    if (counter) counter.textContent = `${this.flowCount} Flows Ingested`;

    // 1. Update Gauge
    CyberCharts.updateGauge(flow.novelty_score, flow.threshold);

    // 2. Prepend Row to Live Monitor Table
    const tbody = document.getElementById("live-stream-tbody");
    if (tbody) {
      const tr = document.createElement("tr");
      tr.dataset.flow = JSON.stringify(flow);

      let badgeHtml = "";
      if (flow.verdict === "Potential Zero-Day") {
        badgeHtml = `<span class="badge-verdict badge-zero-day"><span class="pulsing-dot dot-red"></span> Potential Zero-Day</span>`;
      } else if (flow.verdict === "Known Attack") {
        badgeHtml = `<span class="badge-verdict badge-known-attack"><span class="pulsing-dot dot-amber"></span> ${flow.predicted_class}</span>`;
      } else {
        badgeHtml = `<span class="badge-verdict badge-benign"><span class="pulsing-dot dot-green"></span> Benign</span>`;
      }

      tr.innerHTML = `
        <td class="text-secondary small">${flow.timestamp || new Date().toLocaleTimeString()}</td>
        <td class="fw-bold">${flow.flow_id}</td>
        <td><code>${flow.raw_features.protocol}</code> &bull; <span class="text-muted">${flow.raw_features.dst_port_category}</span></td>
        <td>${badgeHtml}</td>
        <td><strong class="${flow.is_anomaly ? 'text-danger' : 'text-info'}">${flow.novelty_score.toFixed(4)}</strong></td>
        <td>
          <button class="btn btn-xs btn-outline-info py-0 px-2 btn-inspect" style="font-size: 0.75rem;">
            Inspect
          </button>
        </td>
      `;

      tr.querySelector(".btn-inspect").addEventListener("click", () => {
        FlowInspector.inspect(flow);
      });

      tbody.insertBefore(tr, tbody.firstChild);

      // Prune old rows
      while (tbody.children.length > this.maxTableRows) {
        tbody.removeChild(tbody.lastChild);
      }
    }

    // 3. Update Dashboard KPI counters & feeds
    const isThreat = flow.verdict !== "Benign";
    CyberCharts.updateTimeline(isThreat);
    CyberCharts.incrementDoughnutClass(flow.verdict === "Potential Zero-Day" ? "Potential Zero-Day" : flow.predicted_class);

    // Increment KPIs
    app.incrementKPIs(flow);

    // 4. If Threat, prepend to Dashboard Live Alert Feed
    if (isThreat) {
      const dashAlertsBody = document.getElementById("dashboard-alerts-body");
      if (dashAlertsBody) {
        // Clear placeholder if present
        if (dashAlertsBody.querySelector("td[colspan]")) {
          dashAlertsBody.innerHTML = "";
        }

        const dTr = document.createElement("tr");
        const severityClass = flow.severity === "critical" ? "severity-critical" : "severity-high";
        const verdictBadge = flow.verdict === "Potential Zero-Day"
          ? `<span class="badge-verdict badge-zero-day"><span class="pulsing-dot dot-red"></span> Zero-Day</span>`
          : `<span class="badge-verdict badge-known-attack">${flow.predicted_class}</span>`;

        dTr.innerHTML = `
          <td class="text-secondary small">${flow.timestamp || new Date().toLocaleTimeString()}</td>
          <td class="fw-bold">${flow.flow_id}</td>
          <td>${verdictBadge}</td>
          <td>${flow.predicted_class}</td>
          <td><span class="${flow.is_anomaly ? 'text-danger' : 'text-info'} fw-bold">${flow.novelty_score.toFixed(4)}</span></td>
          <td><span class="${severityClass} text-uppercase">${flow.severity}</span></td>
          <td>
            <button class="btn btn-xs btn-outline-info py-0 px-2 btn-dash-inspect" style="font-size: 0.75rem;">
              Inspect
            </button>
          </td>
        `;

        dTr.querySelector(".btn-dash-inspect").addEventListener("click", () => {
          FlowInspector.inspect(flow);
        });

        dashAlertsBody.insertBefore(dTr, dashAlertsBody.firstChild);

        while (dashAlertsBody.children.length > 10) {
          dashAlertsBody.removeChild(dashAlertsBody.lastChild);
        }
      }
    }
  }
};
