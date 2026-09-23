"""
preprocessing.py — Feature engineering & preprocessing pipeline
Smart City Transformer Monitoring — Backend Member 2 (ML Integration)

VERIFIED PIPELINE (from model inspection):
  Input: raw sensor dict (48 fields from API)
  Step 1: Compute 11 engineered features:
    Voltage_Imbalance_Pct, Current_Imbalance_Pct,
    Total_VA, Total_W, Total_RVA,
    Avg_THD_V, Avg_THD_I,
    Hour, DayOfWeek, Month   (from server time if not supplied)
  Step 2: Arrange all 59 features in CLASSIFICATION_FEATURES order
  Step 3: Scale with cls_scaler (StandardScaler, n_features_in_=59)
  Step 4: Return np.ndarray of shape (1, 59) → ready for model.predict()

  For regression (OTI prediction):
    Steps 1–2 for 54-feature REGRESSION_FEATURES list
    Step 3: Scale with reg_scaler

  For anomaly detection:
    Arrange 13 features in ANOMALY_FEATURES order
    No scaler (IsolationForest is scale-invariant in this pipeline)
"""

import logging
import numpy as np
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Compute engineered features from raw readings
# ─────────────────────────────────────────────────────────────────────────────

def engineer_features(raw: dict) -> dict:
    """
    Compute all engineered features from raw sensor readings.

    Modifies a copy of `raw` in-place and returns it with all
    derived features added.

    Args:
        raw: dict of validated numeric sensor values

    Returns:
        dict with all 59 classification features populated
    """
    feat = {k: float(v) for k, v in raw.items()}  # ensure all numeric

    # ── Time features ──────────────────────────────────────────────────────
    # If not provided in request, derive from current UTC time.
    if "Hour" not in feat:
        now = datetime.now(timezone.utc)
        feat["Hour"]      = float(now.hour)
        feat["DayOfWeek"] = float(now.weekday())   # 0 = Monday
        feat["Month"]     = float(now.month)
    else:
        feat.setdefault("DayOfWeek", float(datetime.now(timezone.utc).weekday()))
        feat.setdefault("Month",     float(datetime.now(timezone.utc).month))

    # ── Voltage imbalance (%) ──────────────────────────────────────────────
    vl1, vl2, vl3 = feat.get("VL1", 0.0), feat.get("VL2", 0.0), feat.get("VL3", 0.0)
    avg_v = (vl1 + vl2 + vl3) / 3.0 if (vl1 + vl2 + vl3) > 0 else 1e-9
    max_v_dev = max(abs(vl1 - avg_v), abs(vl2 - avg_v), abs(vl3 - avg_v))
    feat["Voltage_Imbalance_Pct"] = round((max_v_dev / avg_v) * 100.0, 4) if avg_v != 0 else 0.0

    # ── Current imbalance (%) ──────────────────────────────────────────────
    il1, il2, il3 = feat.get("IL1", 0.0), feat.get("IL2", 0.0), feat.get("IL3", 0.0)
    total_i = il1 + il2 + il3
    if total_i > 0:
        avg_i = total_i / 3.0
        max_i_dev = max(abs(il1 - avg_i), abs(il2 - avg_i), abs(il3 - avg_i))
        feat["Current_Imbalance_Pct"] = round((max_i_dev / avg_i) * 100.0, 4) if avg_i != 0 else 0.0
    else:
        feat["Current_Imbalance_Pct"] = 0.0

    # ── Total apparent / active / reactive power ───────────────────────────
    feat["Total_VA"]  = feat.get("VAL1", 0.0)  + feat.get("VAL2", 0.0)  + feat.get("VAL3", 0.0)
    feat["Total_W"]   = feat.get("WL1",  0.0)  + feat.get("WL2",  0.0)  + feat.get("WL3",  0.0)
    feat["Total_RVA"] = feat.get("RVAL1", 0.0) + feat.get("RVAL2", 0.0) + feat.get("RVAL3", 0.0)

    # ── Average THD voltage & current ─────────────────────────────────────
    feat["Avg_THD_V"] = (
        feat.get("THDVL1", 0.0) + feat.get("THDVL2", 0.0) + feat.get("THDVL3", 0.0)
    ) / 3.0
    feat["Avg_THD_I"] = (
        feat.get("THDIL1", 0.0) + feat.get("THDIL2", 0.0) + feat.get("THDIL3", 0.0)
    ) / 3.0

    # ── Temperature differences ─────────────────────────────────────────────
    feat["OTI_ATI_Diff"] = round(feat.get("OTI", 0.0) - feat.get("ATI", 0.0), 4)
    feat["WTI_ATI_Diff"] = round(feat.get("WTI", 0.0) - feat.get("ATI", 0.0), 4)
    feat["WTI_OTI_Diff"] = round(feat.get("WTI", 0.0) - feat.get("OTI", 0.0), 4)

    return feat


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 + 3 — Build numpy arrays for each model
# ─────────────────────────────────────────────────────────────────────────────

def build_classification_array(feat: dict, scaler) -> np.ndarray:
    """
    Build the (1, 59) scaled array for the classification model.

    Args:
        feat:   dict from engineer_features() — must contain all 59 keys
        scaler: fitted cls_scaler (StandardScaler, n_features_in_=59)

    Returns:
        np.ndarray of shape (1, 59), scaled
    """
    from config import CLASSIFICATION_FEATURES

    values = np.array(
        [feat.get(col, 0.0) for col in CLASSIFICATION_FEATURES],
        dtype=np.float64
    ).reshape(1, -1)

    if scaler is not None:
        return scaler.transform(values)
    else:
        logger.warning("Classification scaler not available; returning raw (unscaled) array.")
        return values


def build_regression_array(feat: dict, scaler) -> np.ndarray:
    """
    Build the (1, 54) scaled array for the OTI regression model.

    Args:
        feat:   dict from engineer_features()
        scaler: fitted reg_scaler (StandardScaler, n_features_in_=54)

    Returns:
        np.ndarray of shape (1, 54), scaled
    """
    from config import REGRESSION_FEATURES

    values = np.array(
        [feat.get(col, 0.0) for col in REGRESSION_FEATURES],
        dtype=np.float64
    ).reshape(1, -1)

    if scaler is not None:
        return scaler.transform(values)
    else:
        logger.warning("Regression scaler not available; returning raw array.")
        return values


def build_anomaly_array(feat: dict) -> np.ndarray:
    """
    Build the (1, 13) array for the IsolationForest anomaly detector.
    No scaler applied (IsolationForest handles its own scaling internally).

    Args:
        feat: dict from engineer_features()

    Returns:
        np.ndarray of shape (1, 13)
    """
    from config import ANOMALY_FEATURES

    values = np.array(
        [feat.get(col, 0.0) for col in ANOMALY_FEATURES],
        dtype=np.float64
    ).reshape(1, -1)
    return values
