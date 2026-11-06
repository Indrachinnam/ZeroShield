# ZeroShield: Zero-Day Exploit Detection Using Transformer-Based Network Traffic Classification

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.2+-ee4c2c.svg)](https://pytorch.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**ZeroShield** is an autonomous cybersecurity perimeter defense platform that classifies network flow traffic using a Transformer architecture (**FlowTransformer**) and detects previously unseen **Zero-Day exploits** through an **Energy-Based Out-of-Distribution Novelty Score**.

---

## 🛡️ Key Innovations

1. **Topology-Agnostic Behavioral Generalization**:
   - Strictly omits raw IP addresses and raw port numbers to prevent subnet overfitting.
   - Maps ports into standard categories: `well-known` (0–1023), `registered` (1024–49151), and `ephemeral` (49152–65535).
   - Ingests 12 behavioral flow tokens: protocol, duration, packet rates, byte rates, packet size variance, TCP flags (SYN, FIN, RST, ACK, PSH), and inter-arrival time (IAT) statistics.

2. **FlowTransformer (FT-Transformer Style Architecture)**:
   - Each numerical feature scalar is projected to a $d_{model} = 64$ continuous token via learnable weights $x_j W_j + b_j$.
   - Categorical tokens are embedded via categorical embedding layers.
   - A learnable `[CLS]` token is prepended to the sequence of 12 feature tokens.
   - 3 Transformer Encoder layers with 4 multi-head self-attention mechanisms model cross-feature correlations.

3. **Energy-Based Zero-Day Detection (Open-Set Recognition)**:
   - Traditional softmax probabilities suffer from overconfidence when encountering novel attack distributions.
   - ZeroShield computes Gibbs Free Energy across the classifier logits:
     $$E(x; T) = -T \cdot \log \sum_{c=1}^K \exp\left(\frac{z_c}{T}\right)$$
   - In-distribution flows (Benign and known attacks) exhibit high activations and low energy ($E < \tau$).
   - Novel Zero-Day exploits exhibit low, uniform activations and high free energy ($E > \tau$).
   - Rejection threshold $\tau$ is calibrated on benign validation traffic to enforce an exact **5% False Positive Rate (FPR)**.

4. **Leave-One-Attack-Out (LOAO) Rigorous Evaluation**:
   - Systematically holds out each attack family (DoS, PortScan, BruteForce, WebAttack, Botnet) as an unknown Zero-Day.
   - Benchmarked against classical baselines: **Random Forest**, **Gradient Boosting**, and **Multi-Layer Perceptron (MLP)**.
   - Metrics reported: **AUROC**, **AUPR**, and **FPR @ 95% TPR**.

---

## 📁 Project Structure

```
zeroshield/
├── backend/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, REST endpoints, and SSE stream
│   ├── database.py          # SQLite database schema (alerts, scans, settings)
│   ├── models.py            # Pydantic schemas
│   ├── inference.py         # FlowTransformer inference engine & feature attribution
│   └── stream_service.py    # SSE live network flow simulator (1-5 flows/sec)
├── frontend/
│   ├── index.html           # 6-view responsive Operations Center SPA
│   ├── css/
│   │   └── style.css        # Dark cybersecurity operations theme
│   └── js/
│       ├── app.js           # Navigation controller, state synchronization
│       ├── charts.js        # Chart.js line, doughnut, gauge, and LOAO bar charts
│       ├── stream.js        # Server-Sent Events client and live flow feed
│       ├── upload.js        # CSV drag-and-drop parser and CSV exporter
│       └── details.js       # Deep inspection modal & feature attribution
├── ml/
│   ├── __init__.py
│   ├── model.py             # PyTorch FlowTransformer architecture
│   ├── dataset.py           # Feature tokenizer and CIC-IDS2017 synthetic generator
│   ├── train.py             # Model training and 5% FPR threshold calibration
│   ├── evaluate.py          # Leave-One-Attack-Out (LOAO) benchmark
│   ├── baselines.py         # Random Forest, Gradient Boosting, MLP baselines
│   └── checkpoints/         # Pre-trained demo weights, scaler, and config
├── data/
│   ├── sample_flows.csv     # Test flows for live replay stream
│   ├── sample_zero_days.csv # Test flows for novel exploit detection
│   ├── synthetic_ids2017.csv# Realistic synthetic CIC-IDS2017 dataset
│   └── evaluation_results.json # Precomputed LOAO and baseline metrics
├── README.md
└── requirements.txt
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.11+
- Virtual environment recommended (`venv` or `uv`)

### 2. Installation
```bash
# Clone or navigate to the repository
cd zeroshield

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run the Application
The application includes a pre-trained `FlowTransformer` checkpoint, calibrated threshold, and demo dataset so it works immediately out of the box:

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Open your browser to: **[http://localhost:8000](http://localhost:8000)**

---

## 🖥️ Operations Center Dashboard Views

1. **Dashboard**:
   - Real-time KPI metric cards (Flows Analyzed, Benign %, Known Attacks, Zero-Day Alerts, Avg Latency).
   - Dynamic 60-second traffic volume timeline and classification distribution doughnut chart.
   - Live Threat Feed with pulsing red indicators for potential Zero-Day exploits.

2. **Live Monitor**:
   - Start / pause simulated live network traffic stream (1x to 4x speed).
   - Real-time Energy Score meter and animated gauge.
   - Interactive runtime threshold slider (&tau;) that dynamically adjusts the detection boundary.

3. **Analyze Upload**:
   - Drag-and-drop CSV batch scanner.
   - Pre-packaged demo download buttons ("Clean Benign", "Mixed Threats", "Hidden Zero-Days").
   - Filterable results table with column sorting and single-click **Export to CSV**.

4. **Alert Details & Flow Inspection**:
   - Click any flow to view its identity, timestamp, and severity.
   - Class probabilities horizontal bar chart.
   - Novelty score vs. calibrated threshold visualization.
   - Gradient-based top feature attributions highlighting root causes.

5. **Model Performance (LOAO Benchmarks)**:
   - Full Leave-One-Attack-Out table across DoS, PortScan, BruteForce, WebAttack, and Botnet.
   - Comparative bar charts (AUROC, AUPR, FPR@95%TPR) comparing FlowTransformer against Random Forest, Gradient Boosting, and MLP.

6. **How It Works**:
   - Step-by-step pipeline diagram (PCAP $\rightarrow$ Tokenization $\rightarrow$ Self-Attention $\rightarrow$ Dual Head $\rightarrow$ Alert).
   - In-depth mathematical explanation of Gibbs Free Energy vs. Softmax overconfidence.

---

## 📡 Backend API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service health status |
| `GET` | `/api/model-info` | Transformer architecture details, parameter counts, and calibration threshold |
| `GET` | `/api/stats` | Aggregated KPI statistics for the Dashboard |
| `POST` | `/api/analyze` | Upload a CSV file of network flows for batch inference and novelty scoring |
| `GET` | `/api/stream` | Server-Sent Events (SSE) streaming live simulated network flows |
| `GET` | `/api/alerts` | Paginated security alerts with severity and verdict filters |
| `POST` | `/api/threshold` | Update the runtime novelty threshold (&tau;) |
| `GET` | `/api/metrics` | Retrieve Leave-One-Attack-Out benchmark results |
| `GET` | `/api/sample-csv` | Download sample test CSVs (`benign`, `mixed`, `zero_day`) |

---

## 📷 Screenshots

### Operations Dashboard
```
+-------------------------------------------------------------------------------+
|  ZEROSHIELD  [Operations Dashboard]       Threshold: -7.4400  [SYNTHETIC DATA]|
+-------------------------------------------------------------------------------+
| [15,240 Flows]  [94.2% Benign]  [180 Attacks]  [42 Zero-Days]  [1.2ms Latency]|
+---------------------------------------+---------------------------------------+
|  Live Traffic Volume Line Chart       |  Classification Doughnut Chart        |
|  [~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~] |  ( Benign | DoS | Zero-Day | ...)     |
+---------------------------------------+---------------------------------------+
|  Live Security Alert Feed (Pulsing Critical Red Badges)                       |
+-------------------------------------------------------------------------------+
```

### Deep Flow Inspection Modal
```
+-------------------------------------------------------------------------------+
| Flow Inspection: FL-10492                                                     |
| Verdict: [POTENTIAL ZERO-DAY EXPLOIT]   Novelty Score: -4.1200 (Thresh: -7.44)|
+---------------------------------------+---------------------------------------+
| Class Probabilities Bar Chart         | Top Contributing Anomaly Features     |
| Benign:     [====] 12%                | bytes_per_sec:     [==============] 35%|
| DoS:        [==] 5%                   | packets_per_sec:   [===========]   28%|
| WebAttack:  [=] 2%                    | flow_duration:     [=======]       20%|
+---------------------------------------+---------------------------------------+
```

---

## 🔬 Retraining & Evaluation

To retrain the FlowTransformer or run the Leave-One-Attack-Out benchmark:

```bash
# 1. Train FlowTransformer and calibrate 5% FPR threshold
python ml/train.py

# 2. Run full LOAO benchmark against RF, Gradient Boosting, and MLP
python ml/evaluate.py
```

If real **CIC-IDS2017** CSV files are placed in `/data`, the training script will automatically detect and train on real production captures.

---

## 📜 License
MIT License. Built for enterprise perimeter network defense and academic intrusion detection research.
