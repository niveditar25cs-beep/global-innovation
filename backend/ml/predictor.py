"""
predictor.py — Model loading and prediction engine
Smart City Transformer Monitoring — Backend Member 2 (ML Integration)

Loads:
  - transformer_alarm_model.joblib  → RandomForest classifier (Fault_Risk_Level: 0/1/2)
  - cls_scaler.joblib               → StandardScaler for 59 classification features
  - transformer_temp_model.joblib   → RandomForest regressor (OTI prediction)
  - reg_scaler.joblib               → StandardScaler for 54 regression features
  - anomaly_detector.joblib         → IsolationForest anomaly detector (13 features)

All models are loaded once at startup; prediction is stateless and thread-safe.
"""

import logging
import numpy as np

logger = logging.getLogger(__name__)

# ─── Module-level model singletons (loaded once) ─────────────────────────────
_clf_model   = None   # classification: alarm level
_clf_scaler  = None   # scaler for classification
_reg_model   = None   # regression: OTI temperature
_reg_scaler  = None   # scaler for regression
_anom_model  = None   # anomaly detector
_models_loaded = False
_load_error    = None   # stores the first load error if any


def load_models():
    """
    Load all models from disk. Called once at application startup.
    Logs success or failure clearly. Sets module-level singletons.
    """
    global _clf_model, _clf_scaler, _reg_model, _reg_scaler
    global _anom_model, _models_loaded, _load_error

    import sys
    import os
    # Ensure backend/ is on sys.path so config can be imported
    _backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _backend_dir not in sys.path:
        sys.path.insert(0, _backend_dir)

    import joblib
    from config import (
        CLASSIFIER_MODEL_PATH, CLASSIFIER_SCALER_PATH,
        REGRESSOR_MODEL_PATH,  REGRESSOR_SCALER_PATH,
        ANOMALY_MODEL_PATH,
    )

    errors = []

    # 1. Classification model (REQUIRED — primary risk output)
    try:
        _clf_model = joblib.load(CLASSIFIER_MODEL_PATH)
        logger.info("✅ Classification model loaded: %s", type(_clf_model).__name__)
        if hasattr(_clf_model, "classes_"):
            logger.info("   Classes: %s", _clf_model.classes_)
        if hasattr(_clf_model, "n_features_in_"):
            logger.info("   n_features_in_: %d", _clf_model.n_features_in_)
    except Exception as exc:
        msg = f"Classification model load FAILED: {exc}"
        logger.error(msg)
        errors.append(msg)

    # 2. Classification scaler (REQUIRED — preprocessing)
    try:
        _clf_scaler = joblib.load(CLASSIFIER_SCALER_PATH)
        logger.info("✅ Classification scaler loaded: %s (n_features=%s)",
                    type(_clf_scaler).__name__,
                    getattr(_clf_scaler, "n_features_in_", "?"))
    except Exception as exc:
        msg = f"Classification scaler load FAILED: {exc}"
        logger.error(msg)
        errors.append(msg)

    # 3. Regression model (OPTIONAL — temperature prediction)
    try:
        _reg_model = joblib.load(REGRESSOR_MODEL_PATH)
        logger.info("✅ Regression model loaded: %s", type(_reg_model).__name__)
    except Exception as exc:
        logger.warning("Regression model load FAILED (non-critical): %s", exc)

    # 4. Regression scaler
    try:
        _reg_scaler = joblib.load(REGRESSOR_SCALER_PATH)
        logger.info("✅ Regression scaler loaded.")
    except Exception as exc:
        logger.warning("Regression scaler load FAILED (non-critical): %s", exc)

    # 5. Anomaly detector
    try:
        _anom_model = joblib.load(ANOMALY_MODEL_PATH)
        logger.info("✅ Anomaly detector loaded: %s", type(_anom_model).__name__)
    except Exception as exc:
        logger.warning("Anomaly detector load FAILED (non-critical): %s", exc)

    if errors:
        _load_error = "; ".join(errors)
        _models_loaded = False
        logger.error("❌ Critical model(s) failed to load. Prediction will be unavailable.")
    else:
        _models_loaded = True
        _load_error = None
        logger.info("🚀 All models loaded successfully. Prediction API is ready.")

    return _models_loaded


def get_model_status() -> dict:
    """Return status info for the GET /api/model/status endpoint."""
    import sklearn
    status = {
        "model_loaded":     bool(_models_loaded),
        "load_error":       str(_load_error) if _load_error else None,
        "classifier": {
            "loaded": _clf_model is not None,
            "type":   type(_clf_model).__name__ if _clf_model else None,
            "classes": [int(c) for c in _clf_model.classes_] if (_clf_model and hasattr(_clf_model, "classes_")) else None,
            "n_estimators": int(_clf_model.n_estimators) if (_clf_model and hasattr(_clf_model, "n_estimators")) else None,
            "n_features_in": int(_clf_model.n_features_in_) if (_clf_model and hasattr(_clf_model, "n_features_in_")) else None,
        },
        "regressor": {
            "loaded": _reg_model is not None,
            "type":   type(_reg_model).__name__ if _reg_model else None,
            "n_features_in": int(_reg_model.n_features_in_) if (_reg_model and hasattr(_reg_model, "n_features_in_")) else None,
        },
        "anomaly_detector": {
            "loaded": _anom_model is not None,
            "type":   type(_anom_model).__name__ if _anom_model else None,
            "n_features_in": int(_anom_model.n_features_in_) if (_anom_model and hasattr(_anom_model, "n_features_in_")) else None,
        },
        "sklearn_version": str(sklearn.__version__),
    }
    return status


def predict_classification(feature_array: np.ndarray) -> dict:
    """
    Run the classification model.

    Args:
        feature_array: numpy array of shape (1, N) — preprocessed features

    Returns:
        dict with:
          - prediction (int): 0, 1, or 2
          - risk_score (float): probability of the highest non-normal class
          - probabilities (dict): per-class probabilities
          - class_label (str): human-readable class name
    """
    if _clf_model is None:
        raise RuntimeError("Classification model is not loaded.")

    prediction = int(_clf_model.predict(feature_array)[0])

    # Attempt predict_proba for confidence/risk score
    probabilities = {}
    risk_score = None

    if hasattr(_clf_model, "predict_proba"):
        try:
            proba = _clf_model.predict_proba(feature_array)[0]
            classes = _clf_model.classes_
            probabilities = {int(c): round(float(p), 6) for c, p in zip(classes, proba)}

            # Risk score = probability of WARNING (class 1) + CRITICAL (class 2)
            p_warn     = probabilities.get(1, 0.0)
            p_critical = probabilities.get(2, 0.0)
            risk_score = round(p_warn + p_critical, 6)
            logger.debug("predict_proba: %s → risk_score=%.4f", probabilities, risk_score)
        except Exception as exc:
            logger.warning("predict_proba failed: %s", exc)

    # Fallback: if no risk_score from proba, map class to approximate score
    if risk_score is None:
        fallback = {0: 0.10, 1: 0.55, 2: 0.85}
        risk_score = fallback.get(prediction, 0.0)
        logger.info("Using fallback risk_score=%.2f for class=%d", risk_score, prediction)

    from config import CLASS_LABELS
    class_label = CLASS_LABELS.get(prediction, f"UNKNOWN({prediction})")

    return {
        "prediction":    prediction,
        "risk_score":    risk_score,
        "probabilities": probabilities,
        "class_label":   class_label,
    }


def predict_regression(feature_array: np.ndarray) -> dict:
    """
    Predict Oil Temperature (OTI) using the regression model.

    Args:
        feature_array: numpy array of shape (1, 54)

    Returns:
        dict with predicted_oti (float) or error info
    """
    if _reg_model is None:
        return {"predicted_oti": None, "error": "Regression model not loaded"}

    try:
        predicted = float(_reg_model.predict(feature_array)[0])
        return {"predicted_oti": round(predicted, 2)}
    except Exception as exc:
        logger.error("OTI regression failed: %s", exc)
        return {"predicted_oti": None, "error": str(exc)}


def predict_anomaly(feature_array: np.ndarray) -> dict:
    """
    Run the IsolationForest anomaly detector.

    Returns:
        dict with is_anomaly (bool) and anomaly_score (float, lower = more anomalous)
    """
    if _anom_model is None:
        return {"is_anomaly": None, "anomaly_score": None, "error": "Anomaly model not loaded"}

    try:
        # IsolationForest: predict returns +1 (normal) or -1 (anomaly)
        label = int(_anom_model.predict(feature_array)[0])
        is_anomaly = label == -1

        # decision_function: negative scores mean more anomalous
        if hasattr(_anom_model, "decision_function"):
            score = float(_anom_model.decision_function(feature_array)[0])
        elif hasattr(_anom_model, "score_samples"):
            score = float(_anom_model.score_samples(feature_array)[0])
        else:
            score = None

        return {
            "is_anomaly":    is_anomaly,
            "anomaly_score": round(score, 6) if score is not None else None,
        }
    except Exception as exc:
        logger.error("Anomaly detection failed: %s", exc)
        return {"is_anomaly": None, "anomaly_score": None, "error": str(exc)}
