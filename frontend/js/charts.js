/**
 * ZeroShield: Chart.js Visualizations Controller
 * Initializes and manages all dashboard charts, gauges, and comparative benchmarks.
 */

const CyberCharts = {
  timelineChart: null,
  doughnutChart: null,
  gaugeChart: null,
  aurocChart: null,
  fprChart: null,
  modalProbChart: null,

  // Global theme defaults
  theme: {
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    textColor: "#94a3b8",
    gridColor: "rgba(30, 41, 59, 0.4)",
    cyan: "#00f2fe",
    green: "#10b981",
    amber: "#f59e0b",
    red: "#ef4444",
    purple: "#8b5cf6"
  },

  initAll() {
    this.initTimelineChart();
    this.initDoughnutChart();
    this.initGaugeChart();
  },

  initTimelineChart() {
    const ctx = document.getElementById("trafficTimelineChart");
    if (!ctx) return;

    const initialLabels = Array.from({ length: 20 }, (_, i) => `-${(20 - i) * 2}s`);
    const benignData = Array.from({ length: 20 }, () => Math.floor(Math.random() * 8 + 15));
    const threatData = Array.from({ length: 20 }, () => Math.floor(Math.random() * 2));

    this.timelineChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: initialLabels,
        datasets: [
          {
            label: "Benign Flows",
            data: benignData,
            borderColor: this.theme.green,
            backgroundColor: "rgba(16, 185, 129, 0.12)",
            tension: 0.35,
            fill: true,
            borderWidth: 2,
            pointRadius: 2
          },
          {
            label: "Threats & Zero-Days",
            data: threatData,
            borderColor: this.theme.red,
            backgroundColor: "rgba(239, 68, 68, 0.15)",
            tension: 0.35,
            fill: true,
            borderWidth: 2,
            pointRadius: 2
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "top",
            labels: { color: this.theme.textColor, boxWidth: 12 }
          }
        },
        scales: {
          x: {
            grid: { color: this.theme.gridColor },
            ticks: { color: this.theme.textColor, maxTicksLimit: 10 }
          },
          y: {
            grid: { color: this.theme.gridColor },
            ticks: { color: this.theme.textColor },
            beginAtZero: true
          }
        }
      }
    });
  },

  updateTimeline(isThreat) {
    if (!this.timelineChart) return;
    const now = new Date().toLocaleTimeString([], { hour12: false, minute: "2-digit", second: "2-digit" });

    this.timelineChart.data.labels.shift();
    this.timelineChart.data.labels.push(now);

    const benignVal = isThreat ? 0 : 1;
    const threatVal = isThreat ? 1 : 0;

    const bLast = this.timelineChart.data.datasets[0].data;
    const tLast = this.timelineChart.data.datasets[1].data;

    bLast.shift();
    bLast.push(bLast[bLast.length - 1] + benignVal);

    tLast.shift();
    tLast.push(tLast[tLast.length - 1] + threatVal);

    this.timelineChart.update("none");
  },

  initDoughnutChart() {
    const ctx = document.getElementById("attackDoughnutChart");
    if (!ctx) return;

    this.doughnutChart = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: ["Benign", "Potential Zero-Day", "DoS", "PortScan", "BruteForce", "WebAttack", "Botnet"],
        datasets: [{
          data: [85, 4, 3, 3, 2, 2, 1],
          backgroundColor: [
            this.theme.green,
            this.theme.red,
            this.theme.amber,
            this.theme.cyan,
            this.theme.purple,
            "#f43f5e",
            "#6366f1"
          ],
          borderColor: "#0f172a",
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "right",
            labels: { color: this.theme.textColor, boxWidth: 10, font: { size: 11 } }
          }
        },
        cutout: "65%"
      }
    });
  },

  incrementDoughnutClass(className) {
    if (!this.doughnutChart) return;
    const labels = this.doughnutChart.data.labels;
    let idx = labels.indexOf(className);
    if (idx === -1) {
      if (className === "Zero-Day Exploit") idx = labels.indexOf("Potential Zero-Day");
      else idx = 0;
    }
    this.doughnutChart.data.datasets[0].data[idx] += 1;
    this.doughnutChart.update();
  },

  initGaugeChart() {
    const ctx = document.getElementById("noveltyGaugeChart");
    if (!ctx) return;

    this.gaugeChart = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: ["Safe In-Distribution", "Novelty Danger Zone"],
        datasets: [{
          data: [70, 30],
          backgroundColor: [this.theme.cyan, this.theme.red],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        circumference: 180,
        rotation: -90,
        cutout: "75%",
        plugins: {
          legend: { display: false },
          tooltip: { enabled: false }
        }
      }
    });
  },

  updateGauge(score, threshold) {
    const display = document.getElementById("gauge-score-display");
    const badge = document.getElementById("gauge-verdict-badge");
    if (display) display.textContent = score.toFixed(4);

    const isNovel = score > threshold;
    if (badge) {
      if (isNovel) {
        badge.className = "badge badge-zero-day mt-2";
        badge.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> ZERO-DAY THREAT (E > &tau;)`;
      } else {
        badge.className = "badge badge-benign mt-2";
        badge.innerHTML = `<i class="fa-solid fa-check"></i> In-Distribution Flow (E &le; &tau;)`;
      }
    }

    if (!this.gaugeChart) return;
    // Map score range [-12.0, -2.0] to [0, 100]
    const clampedScore = Math.max(-12.0, Math.min(-2.0, score));
    const pct = ((clampedScore - (-12.0)) / (10.0)) * 100;
    this.gaugeChart.data.datasets[0].data = [100 - pct, pct];
    this.gaugeChart.update();
  },

  renderPerformanceCharts(loaoData) {
    if (!loaoData || !loaoData.held_out_attacks) return;

    const attacks = Object.keys(loaoData.held_out_attacks);
    const models = ["FlowTransformer", "Random Forest", "Gradient Boosting", "MLP"];
    const colors = [this.theme.cyan, this.theme.green, this.theme.amber, this.theme.purple];

    // 1. AUROC Chart
    const aurocCtx = document.getElementById("aurocCompareChart");
    if (aurocCtx) {
      if (this.aurocChart) this.aurocChart.destroy();
      this.aurocChart = new Chart(aurocCtx, {
        type: "bar",
        data: {
          labels: attacks,
          datasets: models.map((m, idx) => ({
            label: m,
            data: attacks.map(att => loaoData.held_out_attacks[att][m].auroc),
            backgroundColor: colors[idx],
            borderRadius: 4
          }))
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { grid: { color: this.theme.gridColor }, ticks: { color: this.theme.textColor } },
            y: { min: 0.5, max: 1.0, grid: { color: this.theme.gridColor }, ticks: { color: this.theme.textColor } }
          },
          plugins: {
            legend: { labels: { color: this.theme.textColor, boxWidth: 10 } }
          }
        }
      });
    }

    // 2. FPR @ 95% TPR Chart
    const fprCtx = document.getElementById("fprCompareChart");
    if (fprCtx) {
      if (this.fprChart) this.fprChart.destroy();
      this.fprChart = new Chart(fprCtx, {
        type: "bar",
        data: {
          labels: attacks,
          datasets: models.map((m, idx) => ({
            label: m,
            data: attacks.map(att => loaoData.held_out_attacks[att][m].fpr_at_95_tpr),
            backgroundColor: colors[idx],
            borderRadius: 4
          }))
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { grid: { color: this.theme.gridColor }, ticks: { color: this.theme.textColor } },
            y: { min: 0.0, max: 0.6, grid: { color: this.theme.gridColor }, ticks: { color: this.theme.textColor } }
          },
          plugins: {
            legend: { labels: { color: this.theme.textColor, boxWidth: 10 } }
          }
        }
      });
    }
  },

  renderModalProbabilities(probDict) {
    const ctx = document.getElementById("modalProbChart");
    if (!ctx) return;
    if (this.modalProbChart) this.modalProbChart.destroy();

    const labels = Object.keys(probDict);
    const data = Object.values(probDict);

    this.modalProbChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [{
          data: data,
          backgroundColor: labels.map(l => l === "Benign" ? this.theme.green : this.theme.amber),
          borderRadius: 4
        }]
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => `Probability: ${(ctx.raw * 100).toFixed(2)}%`
            }
          }
        },
        scales: {
          x: { min: 0, max: 1, grid: { color: this.theme.gridColor }, ticks: { color: this.theme.textColor } },
          y: { grid: { display: false }, ticks: { color: this.theme.textColor } }
        }
      }
    });
  }
};
