"""
prediction_routes.py — Flask API routes for prediction and model status
Smart City Transformer Monitoring — Backend Member 2 (ML Integration)

Endpoints:
  POST /api/predict       → Full ML prediction pipeline
  GET  /api/model/status  → Model health check

Never exposes raw stack traces or model file paths in responses.
All errors return structured JSON with a meaningful "error" key.
"""

import logging
import traceback
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

# Create Blueprint
prediction_bp = Blueprint("prediction", __name__, url_prefix="/api")


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/model/status
# ─────────────────────────────────────────────────────────────────────────────

@prediction_bp.route("/model/status", methods=["GET"])
def model_status():
    """
    Return model load status and metadata.

    Response (200):
    {
        "model_loaded": true,
        "models": {
            "classifier": {"loaded": true, "type": "RandomForestClassifier", ...},
            "regressor":  {"loaded": true, "type": "RandomForestRegressor"},
            "anomaly_detector": {"loaded": true, "type": "IsolationForest"}
        },
        "sklearn_version": "1.5.2",
        "timestamp": "..."
    }
    """
    try:
        from ml.predictor import get_model_status
        status = get_model_status()
        return jsonify({
            **status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }), 200
    except Exception as exc:
        logger.error("Error in /api/model/status: %s", exc)
        return jsonify({"error": "Failed to retrieve model status."}), 500


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/predict
# ─────────────────────────────────────────────────────────────────────────────

@prediction_bp.route("/predict", methods=["POST"])
def predict():
    """
    Full ML prediction pipeline.

    Request body (JSON):
        {
            "OTI": 45.2, "WTI": 60.1, "ATI": 28.5, "OLI": 50.0,
            "VL1": 235.4, "VL2": 234.8, "VL3": 236.0,
            "IL1": 120.0, "IL2": 118.5, "IL3": 121.2,
            ... (all REQUIRED_API_FIELDS from config.py)
        }

    Response (200):
        {
            "success": true,
            "timestamp": "2026-09-23T13:30:00Z",
            "prediction": {
                "risk_level": "NORMAL",
                "risk_score": 0.10,
                "class_id": 0,
                "class_label": "Normal Operation",
                "probabilities": {"normal": 0.90, "warning": 0.09, "high_risk": 0.01},
                "thresholds_used": {"normal_max": 0.39, "warning_max": 0.69}
            },
            "abnormal_parameters": [],
            "anomaly_detection": {"is_anomaly": false, "anomaly_score": -0.05},
            "oil_temperature_prediction": {"predicted_oti": 44.3},
            "explanation": "...",
            "alert": {"required": false, "severity": "LOW", "message": "..."}
        }

    Error (400):
        {"success": false, "error": "Validation failed", "errors": [...]}

    Error (503):
        {"success": false, "error": "Model not available"}
    """
    # ── 0. Check model is loaded ───────────────────────────────────────────────
    from ml.predictor import _models_loaded, _load_error
    if not _models_loaded:
        logger.error("Prediction request received but model is not loaded: %s", _load_error)
        return jsonify({
            "success": False,
            "error":   "Prediction model is not available.",
            "detail":  "The classification model failed to load at startup. Check server logs.",
        }), 503

    # ── 1. Parse request body ──────────────────────────────────────────────────
    if not request.is_json:
        return jsonify({
            "success": False,
            "error":   "Request must have Content-Type: application/json",
        }), 400

    try:
        data = request.get_json(force=True, silent=False)
    except Exception:
        return jsonify({
            "success": False,
            "error":   "Request body is not valid JSON.",
        }), 400

    if data is None:
        return jsonify({
            "success": False,
            "error":   "Empty request body.",
        }), 400

    # ── 2. Validate input ──────────────────────────────────────────────────────
    from ml.validation import validate_input
    validation = validate_input(data)
    if not validation["valid"]:
        return jsonify({
            "success":  False,
            "error":    "Input validation failed.",
            "errors":   validation["errors"],
        }), 400

    # ── 3. Feature engineering ─────────────────────────────────────────────────
    try:
        from ml.preprocessing import (
            engineer_features,
            build_classification_array,
            build_regression_array,
            build_anomaly_array,
        )
        from ml.predictor import _clf_scaler, _reg_scaler
        feat = engineer_features(data)
    except Exception as exc:
        logger.error("Feature engineering failed: %s\n%s", exc, traceback.format_exc())
        return jsonify({
            "success": False,
            "error":   "Feature engineering failed. Check input values.",
        }), 500

    # ── 4. Detect abnormal parameters ─────────────────────────────────────────
    from ml.validation import detect_abnormal_parameters
    abnormal = detect_abnormal_parameters(feat)
    if abnormal:
        logger.info(
            "Abnormal parameters detected: %s",
            [p["parameter"] for p in abnormal]
        )

    # ── 5. Classification (PRIMARY — fault risk level) ────────────────────────
    try:
        from ml.predictor import predict_classification
        X_clf = build_classification_array(feat, _clf_scaler)
        clf_result = predict_classification(X_clf)
    except Exception as exc:
        logger.error("Classification prediction failed: %s\n%s", exc, traceback.format_exc())
        return jsonify({
            "success": False,
            "error":   "Prediction failed. Please try again.",
        }), 500

    # ── 6. Regression — OTI temperature prediction (OPTIONAL) ─────────────────
    reg_result = None
    try:
        from ml.predictor import predict_regression
        X_reg = build_regression_array(feat, _reg_scaler)
        reg_result = predict_regression(X_reg)
    except Exception as exc:
        logger.warning("OTI regression prediction failed (non-critical): %s", exc)
        reg_result = {"predicted_oti": None, "error": str(exc)}

    # ── 7. Anomaly detection (OPTIONAL) ───────────────────────────────────────
    anom_result = None
    try:
        from ml.predictor import predict_anomaly
        X_anom = build_anomaly_array(feat)
        anom_result = predict_anomaly(X_anom)
    except Exception as exc:
        logger.warning("Anomaly detection failed (non-critical): %s", exc)
        anom_result = {"is_anomaly": None, "anomaly_score": None, "error": str(exc)}

    # ── 8. Multi-Layer Risk Level Determination ───────────────────────────────
    from ml.risk_engine import determine_risk_level, build_risk_output
    risk_level  = determine_risk_level(clf_result, abnormal_parameters=abnormal, anomaly_result=anom_result)
    risk_output = build_risk_output(clf_result, risk_level)

    # Log high-risk detections (without logging full input payload)
    if risk_level == "HIGH_RISK":
        logger.warning(
            "HIGH RISK detected — risk_score=%.4f, class=%d, abnormal_params=%d",
            clf_result.get("risk_score", -1),
            clf_result.get("prediction", -1),
            len(abnormal),
        )

    # ── 9. Explanation ────────────────────────────────────────────────────────
    from ml.explanation import generate_explanation
    explanation = generate_explanation(
        risk_level=risk_level,
        risk_score=clf_result.get("risk_score"),
        abnormal_parameters=abnormal,
        regression_result=reg_result,
        anomaly_result=anom_result,
    )

    # ── 10. Alert ─────────────────────────────────────────────────────────────
    from ml.alert import generate_alert
    alert = generate_alert(risk_level)

    # ── 11. Build and return full response ────────────────────────────────────
    response = {
        "success":   True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prediction": risk_output,
        "abnormal_parameters":         abnormal,
        "anomaly_detection":           anom_result,
        "oil_temperature_prediction":  reg_result,
        "explanation":                 explanation,
        "alert":                       alert,
    }

    logger.info(
        "Prediction complete — risk_level=%s, risk_score=%.4f",
        risk_level,
        clf_result.get("risk_score", -1),
    )
    return jsonify(response), 200
