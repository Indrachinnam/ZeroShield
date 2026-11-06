"""
ZeroShield: Pydantic Data Models & Schemas
Defines request and response schemas for all API endpoints.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class FlowFeatureInput(BaseModel):
    flow_id: Optional[str] = "FL-USER"
    protocol: Optional[str] = "TCP"
    dst_port_category: Optional[str] = "well-known"
    flow_duration: Optional[float] = 1000.0
    total_fwd_packets: Optional[int] = 5
    total_bwd_packets: Optional[int] = 5
    packet_len_mean: Optional[float] = 500.0
    packet_len_std: Optional[float] = 100.0
    bytes_per_sec: Optional[float] = 50000.0
    packets_per_sec: Optional[float] = 100.0
    flag_syn: Optional[int] = 1
    flag_fin: Optional[int] = 1
    flag_rst: Optional[int] = 0
    flag_ack: Optional[int] = 1
    flag_psh: Optional[int] = 1
    flow_iat_mean: Optional[float] = 200.0
    flow_iat_std: Optional[float] = 50.0


class FlowPredictionResult(BaseModel):
    flow_id: str
    verdict: str  # "Benign", "Known Attack", or "Potential Zero-Day"
    predicted_class: str
    confidence: float
    novelty_score: float
    threshold: float
    is_anomaly: bool
    severity: str  # "critical", "high", "medium", "low"
    class_probabilities: Dict[str, float]
    top_features: Dict[str, float]
    raw_features: Dict[str, Any]


class AnalyzeResponse(BaseModel):
    total_flows: int
    benign_count: int
    known_attack_count: int
    zero_day_count: int
    avg_inference_latency_ms: float
    threshold_used: float
    results: List[FlowPredictionResult]


class ThresholdUpdateRequest(BaseModel):
    threshold: float = Field(..., description="Novelty score threshold for Zero-Day flagging")


class ModelInfoResponse(BaseModel):
    model_name: str
    architecture: str
    parameters: int
    d_model: int
    nhead: int
    num_encoder_layers: int
    classes: List[str]
    calibrated_threshold: float
    current_runtime_threshold: float
    calibrated_fpr: float
    test_accuracy: float
    test_macro_f1: float
    is_synthetic: bool
    training_samples: int
    device: str
