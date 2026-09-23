"""
risk_engine.py — Convert ML model output into structured risk levels
Smart City Transformer Monitoring — Backend Member 2 (ML Integration)

Risk level determination:
  - PRIMARY: predict_proba risk_score (P(class=1) + P(class=2))
    0.00 – 0.39 → NORMAL
    0.40 – 0.69 → WARNING
    0.70 – 1.00 → HIGH_RISK
  - FALLBACK (if predict_proba unavailable): direct class mapping
    0 → NORMAL, 1 → WARNING, 2 → HIGH_RISK

All thresholds are read from config.py — no magic numbers here.
"""

import logging

logger = logging.getLogger(__name__)


def determine_risk_level(
    prediction_result: dict,
    abnormal_parameters: list = None,
    anomaly_result: dict = None,
) -> str:
    """
    Determine NORMAL / WARNING / HIGH_RISK using a multi-layer defense-in-depth architecture:
      Layer 1: Supervised ML Classifier (RandomForest probabilities -> continuous risk score)
      Layer 2: Unsupervised Anomaly Detector (IsolationForest statistical outlier check)
      Layer 3: Deterministic Rule-Based Safety Net (IEEE C57.12 physical threshold violations)

    Ensures that if physical safety boundaries are breached (e.g. OTI > 95°C), the system
    never silently returns NORMAL, even if the ML classifier's raw output is low-risk.

    Args:
        prediction_result: dict from predictor.predict_classification()
        abnormal_parameters: list of flagged parameter dicts from validation.detect_abnormal_parameters()
        anomaly_result: dict from predictor.predict_anomaly()

    Returns:
        str: "NORMAL" | "WARNING" | "HIGH_RISK"
    """
    from config import RISK_THRESHOLDS, CLASS_TO_RISK

    risk_score   = prediction_result.get("risk_score")
    raw_class    = prediction_result.get("prediction")

    # ── Layer 1: Supervised ML Classifier Risk Level ──────────────────────────
    if risk_score is not None and isinstance(risk_score, (int, float)):
        if risk_score <= RISK_THRESHOLDS["NORMAL"]:
            level = "NORMAL"
        elif risk_score <= RISK_THRESHOLDS["WARNING"]:
            level = "WARNING"
        else:
            level = "HIGH_RISK"
    elif raw_class is not None:
        level = CLASS_TO_RISK.get(int(raw_class), "UNKNOWN")
    else:
        level = "UNKNOWN"

    # ── Layer 2: Unsupervised Anomaly Detection Safety Net ────────────────────
    if anomaly_result and anomaly_result.get("is_anomaly") is True:
        if level == "NORMAL":
            level = "WARNING"
            logger.info("Safety net: elevated risk from NORMAL to WARNING due to IsolationForest anomaly.")

    # ── Layer 3: Deterministic IEEE C57.12 Physical Rule-Based Safety Net ─────
    if abnormal_parameters:
        flagged_names = [p.get("parameter") for p in abnormal_parameters]

        # Check for critical thermal violations (OTI > 95°C, WTI > 105°C)
        has_thermal_violation = any(
            p.get("parameter") in ("OTI", "WTI") and p.get("status") == "HIGH"
            for p in abnormal_parameters
        )

        # Check for severe/emergency thermal runaway (OTI > 120°C, WTI > 130°C)
        has_severe_thermal = any(
            (p.get("parameter") == "OTI" and float(p.get("value", 0)) >= 120.0) or
            (p.get("parameter") == "WTI" and float(p.get("value", 0)) >= 130.0)
            for p in abnormal_parameters
        )

        if has_severe_thermal or len(abnormal_parameters) >= 5:
            level = "HIGH_RISK"
            logger.warning("Safety net: elevated risk to HIGH_RISK due to critical threshold violations: %s", flagged_names)
        elif (has_thermal_violation or len(abnormal_parameters) >= 1) and level == "NORMAL":
            level = "WARNING"
            logger.info("Safety net: elevated risk from NORMAL to WARNING due to IEEE safe threshold violations: %s", flagged_names)

    return level


def build_risk_output(prediction_result: dict, risk_level: str) -> dict:
    """
    Build the structured risk output dict for the API response.

    Args:
        prediction_result: raw dict from predictor.predict_classification()
        risk_level: "NORMAL" | "WARNING" | "HIGH_RISK"

    Returns:
        dict suitable for the "prediction" field of the API response
    """
    from config import CLASS_LABELS, RISK_THRESHOLDS

    raw_class  = prediction_result.get("prediction")
    risk_score = prediction_result.get("risk_score")
    proba      = prediction_result.get("probabilities", {})

    return {
        "risk_level":      risk_level,
        "risk_score":      risk_score,
        "class_id":        raw_class,
        "class_label":     CLASS_LABELS.get(raw_class, "Unknown"),
        "probabilities": {
            "normal":    proba.get(0, None),
            "warning":   proba.get(1, None),
            "high_risk": proba.get(2, None),
        },
        "thresholds_used": {
            "normal_max":  RISK_THRESHOLDS["NORMAL"],
            "warning_max": RISK_THRESHOLDS["WARNING"],
        },
    }
