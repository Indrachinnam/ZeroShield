"""
ZeroShield: SQLite Database Layer
Stores security alerts, scan histories, and runtime configuration.
"""

import os
import json
import sqlite3
import datetime
from typing import Dict, List, Optional, Any, Tuple

# Use /tmp on Vercel serverless where root filesystem is read-only
if os.environ.get("VERCEL"):
    DB_PATH = "/tmp/zeroshield.db"
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "zeroshield.db")



def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes SQLite tables for alerts, scans, and settings."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        flow_id TEXT NOT NULL,
        verdict TEXT NOT NULL,
        attack_class TEXT NOT NULL,
        novelty_score REAL NOT NULL,
        threshold REAL NOT NULL,
        confidence REAL NOT NULL,
        severity TEXT NOT NULL,
        protocol TEXT,
        dst_port_category TEXT,
        flow_duration REAL,
        total_fwd_packets INTEGER,
        total_bwd_packets INTEGER,
        bytes_per_sec REAL,
        packets_per_sec REAL,
        features_json TEXT,
        status TEXT DEFAULT 'active'
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scan_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        source TEXT NOT NULL,
        filename TEXT,
        total_flows INTEGER NOT NULL,
        benign_count INTEGER NOT NULL,
        known_attack_count INTEGER NOT NULL,
        zero_day_count INTEGER NOT NULL,
        avg_latency_ms REAL NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """)

    conn.commit()
    conn.close()


def save_alert(alert: Dict[str, Any]) -> int:
    """Inserts a new alert into SQLite."""
    conn = get_connection()
    cursor = conn.cursor()

    ts = alert.get("timestamp") or datetime.datetime.now().isoformat()
    cursor.execute("""
    INSERT INTO alerts (
        timestamp, flow_id, verdict, attack_class, novelty_score, threshold,
        confidence, severity, protocol, dst_port_category, flow_duration,
        total_fwd_packets, total_bwd_packets, bytes_per_sec, packets_per_sec,
        features_json, status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ts,
        alert.get("flow_id", "FL-UNKNOWN"),
        alert.get("verdict", "Benign"),
        alert.get("attack_class", "Benign"),
        float(alert.get("novelty_score", 0.0)),
        float(alert.get("threshold", 0.0)),
        float(alert.get("confidence", 0.0)),
        alert.get("severity", "low"),
        alert.get("protocol", "TCP"),
        alert.get("dst_port_category", "well-known"),
        float(alert.get("flow_duration", 0.0)),
        int(alert.get("total_fwd_packets", 0)),
        int(alert.get("total_bwd_packets", 0)),
        float(alert.get("bytes_per_sec", 0.0)),
        float(alert.get("packets_per_sec", 0.0)),
        json.dumps(alert.get("features", {})),
        alert.get("status", "active")
    ))

    alert_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return alert_id


def get_alerts(
    page: int = 1,
    page_size: int = 20,
    severity: Optional[str] = None,
    verdict: Optional[str] = None,
    search: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], int]:
    """Retrieves paginated alerts with filtering."""
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM alerts WHERE 1=1"
    params = []

    # Normalize string filters
    if severity is not None:
        sev_str = str(severity).lower().strip()
        if sev_str not in ["all", "none", ""]:
            query += " AND severity = ?"
            params.append(sev_str)

    if verdict is not None:
        ver_str = str(verdict).strip()
        if ver_str.lower() not in ["all", "none", ""]:
            query += " AND verdict = ?"
            params.append(ver_str)

    if search:
        search_str = str(search).strip()
        if search_str:
            query += " AND (flow_id LIKE ? OR attack_class LIKE ?)"
            params.extend([f"%{search_str}%", f"%{search_str}%"])

    # Count total
    count_query = f"SELECT COUNT(*) FROM ({query})"
    cursor.execute(count_query, params)
    total_count = cursor.fetchone()[0]

    # Paginate (newest first)
    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    offset = (page - 1) * page_size
    params.extend([page_size, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()
    alerts = []
    for r in rows:
        d = dict(r)
        if d.get("features_json"):
            try:
                d["features"] = json.loads(d["features_json"])
            except Exception:
                d["features"] = {}
        alerts.append(d)

    conn.close()
    return alerts, total_count


def save_scan(scan: Dict[str, Any]) -> int:
    """Records a completed batch scan in history."""
    conn = get_connection()
    cursor = conn.cursor()

    ts = scan.get("timestamp") or datetime.datetime.now().isoformat()
    cursor.execute("""
    INSERT INTO scan_history (
        timestamp, source, filename, total_flows, benign_count,
        known_attack_count, zero_day_count, avg_latency_ms
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ts,
        scan.get("source", "upload"),
        scan.get("filename", "unknown.csv"),
        int(scan.get("total_flows", 0)),
        int(scan.get("benign_count", 0)),
        int(scan.get("known_attack_count", 0)),
        int(scan.get("zero_day_count", 0)),
        float(scan.get("avg_latency_ms", 0.0))
    ))

    scan_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return scan_id


def get_runtime_threshold(default_threshold: float = -1.0) -> float:
    """Gets user-configured runtime threshold or returns default."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM system_settings WHERE key = 'novelty_threshold'")
    row = cursor.fetchone()
    conn.close()
    if row:
        try:
            return float(row["value"])
        except ValueError:
            pass
    return default_threshold


def set_runtime_threshold(val: float):
    """Sets user-configured runtime threshold."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO system_settings (key, value) VALUES ('novelty_threshold', ?)
    ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """, (str(val),))
    conn.commit()
    conn.close()


def get_kpi_stats() -> Dict[str, Any]:
    """Computes overall statistics for the Dashboard."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM alerts")
    total_alerts = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM alerts WHERE verdict = 'Potential Zero-Day'")
    zero_day_alerts = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM alerts WHERE verdict = 'Known Attack'")
    known_attack_alerts = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM alerts WHERE verdict = 'Benign'")
    benign_alerts = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(total_flows) FROM scan_history")
    total_scanned_flows = cursor.fetchone()[0] or 0

    cursor.execute("SELECT AVG(avg_latency_ms) FROM scan_history")
    avg_latency = cursor.fetchone()[0] or 1.4

    conn.close()

    total_flows_combined = total_scanned_flows + total_alerts
    benign_pct = round((benign_alerts / max(total_alerts, 1)) * 100, 1)

    return {
        "total_flows_analyzed": total_flows_combined,
        "total_alerts": total_alerts,
        "zero_day_alerts": zero_day_alerts,
        "known_attack_alerts": known_attack_alerts,
        "benign_alerts": benign_alerts,
        "benign_percentage": benign_pct,
        "avg_latency_ms": round(float(avg_latency), 2)
    }


# Auto-initialize DB tables on load
init_db()
