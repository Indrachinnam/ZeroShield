/**
 * ZeroShield: Batch CSV Upload & Flow Analyzer
 * Handles drag-and-drop file ingestion, batch inference invocation,
 * dynamic filtering, and report CSV export.
 */

const BatchAnalyzer = {
  currentAnalysisResults: [],
  activeFilter: "all",

  init() {
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const exportBtn = document.getElementById("btn-export-csv");

    if (dropZone && fileInput) {
      dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("dragover");
      });

      dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("dragover");
      });

      dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
          this.uploadFile(e.dataTransfer.files[0]);
        }
      });

      fileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
          this.uploadFile(e.target.files[0]);
        }
      });
    }

    if (exportBtn) {
      exportBtn.addEventListener("click", () => this.exportResultsToCSV());
    }

    // Filter verdict buttons
    document.querySelectorAll(".filter-verdict-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".filter-verdict-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        this.activeFilter = btn.dataset.filter || "all";
        this.renderFilteredTable();
      });
    });
  },

  async uploadFile(file) {
    if (!file.name.endsWith(".csv")) {
      alert("Please upload a valid .csv network flow file.");
      return;
    }

    const dropZone = document.getElementById("drop-zone");
    const originalContent = dropZone.innerHTML;
    dropZone.innerHTML = `
      <i class="fa-solid fa-spinner fa-spin fa-3x text-info mb-3"></i>
      <h5 class="fw-bold">Analyzing Flow Sequences with FlowTransformer...</h5>
      <p class="text-muted small">Tokenizing continuous and categorical attributes, calculating Free Energy novelty scores...</p>
    `;

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("/api/analyze", {
        method: "POST",
        body: formData
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Analysis failed.");
      }

      const data = await response.json();
      this.currentAnalysisResults = data.results || [];
      this.displayResults(data);
      dropZone.innerHTML = originalContent;

      // Refresh dashboard KPI stats
      app.loadStats();
    } catch (error) {
      console.error("Batch upload failed:", error);
      alert(`Error analyzing file: ${error.message}`);
      dropZone.innerHTML = originalContent;
    }
  },

  displayResults(data) {
    const resultsSection = document.getElementById("upload-results-section");
    if (!resultsSection) return;

    resultsSection.classList.remove("d-none");

    // Populate summary bar
    document.getElementById("res-total-flows").textContent = data.total_flows;
    document.getElementById("res-benign-count").textContent = data.benign_count;
    document.getElementById("res-known-count").textContent = data.known_attack_count;
    document.getElementById("res-zd-count").textContent = data.zero_day_count;
    document.getElementById("res-latency").textContent = `${data.avg_inference_latency_ms} ms/flow`;

    // Render table
    this.renderFilteredTable();

    // Scroll to results
    resultsSection.scrollIntoView({ behavior: "smooth" });
  },

  renderFilteredTable() {
    const tbody = document.getElementById("upload-results-tbody");
    if (!tbody) return;

    tbody.innerHTML = "";
    const filtered = this.currentAnalysisResults.filter(item => {
      if (this.activeFilter === "all") return true;
      return item.verdict === this.activeFilter;
    });

    if (filtered.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted py-4">No flows matching filter "${this.activeFilter}"</td></tr>`;
      return;
    }

    filtered.slice(0, 100).forEach(item => {
      const tr = document.createElement("tr");

      let verdictBadge = "";
      if (item.verdict === "Potential Zero-Day") {
        verdictBadge = `<span class="badge-verdict badge-zero-day"><span class="pulsing-dot dot-red"></span> Potential Zero-Day</span>`;
      } else if (item.verdict === "Known Attack") {
        verdictBadge = `<span class="badge-verdict badge-known-attack"><span class="pulsing-dot dot-amber"></span> Known Attack</span>`;
      } else {
        verdictBadge = `<span class="badge-verdict badge-benign"><span class="pulsing-dot dot-green"></span> Benign</span>`;
      }

      tr.innerHTML = `
        <td class="fw-bold">${item.flow_id}</td>
        <td><code>${item.raw_features.protocol}</code> &bull; <span class="text-muted">${item.raw_features.dst_port_category}</span></td>
        <td>${verdictBadge}</td>
        <td><strong>${item.predicted_class}</strong></td>
        <td><span class="${item.is_anomaly ? 'text-danger' : 'text-info'} fw-bold">${item.novelty_score.toFixed(4)}</span></td>
        <td>${(item.confidence * 100).toFixed(1)}%</td>
        <td>
          <button class="btn btn-xs btn-outline-info py-0 px-2 btn-table-inspect" style="font-size: 0.75rem;">
            Inspect
          </button>
        </td>
      `;

      tr.querySelector(".btn-table-inspect").addEventListener("click", () => {
        FlowInspector.inspect(item);
      });

      tbody.appendChild(tr);
    });
  },

  exportResultsToCSV() {
    if (this.currentAnalysisResults.length === 0) {
      alert("No analysis results to export.");
      return;
    }

    const headers = [
      "flow_id", "verdict", "predicted_class", "novelty_score", "threshold",
      "confidence", "severity", "protocol", "dst_port_category", "flow_duration",
      "total_fwd_packets", "total_bwd_packets", "bytes_per_sec", "packets_per_sec"
    ];

    const rows = this.currentAnalysisResults.map(item => [
      item.flow_id,
      item.verdict,
      item.predicted_class,
      item.novelty_score,
      item.threshold,
      item.confidence,
      item.severity,
      item.raw_features.protocol,
      item.raw_features.dst_port_category,
      item.raw_features.flow_duration,
      item.raw_features.total_fwd_packets,
      item.raw_features.total_bwd_packets,
      item.raw_features.bytes_per_sec,
      item.raw_features.packets_per_sec
    ]);

    const csvContent = "data:text/csv;charset=utf-8,"
      + [headers.join(","), ...rows.map(e => e.join(","))].join("\n");

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `zeroshield_analysis_report_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
};
