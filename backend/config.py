# =============================================================================
# config.py — Central configuration for the ML Risk Engine
# Smart City / Transformer Monitoring System — Backend Member 2
#
# VERIFIED from actual model inspection (sklearn 1.5.2):
#   transformer_alarm_model.joblib → RandomForestClassifier, n_features_in_=59
#   transformer_temp_model.joblib  → RandomForestRegressor,  n_features_in_=54
#   anomaly_detector.joblib        → IsolationForest,        n_features_in_=13
#   cls_scaler.joblib              → StandardScaler,         n_features_in_=59
#   reg_scaler.joblib              → StandardScaler,         n_features_in_=54
# =============================================================================
import os
from pathlib import Path

# ─── BASE PATHS ──────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent
ML_DIR      = BASE_DIR / "ml"
MODEL_DIR   = ML_DIR / "model"
DATASET_DIR = ML_DIR / "dataset"

# ─── MODEL FILES ─────────────────────────────────────────────────────────────
CLASSIFIER_MODEL_PATH  = str(MODEL_DIR / "transformer_alarm_model.joblib")
CLASSIFIER_SCALER_PATH = str(MODEL_DIR / "cls_scaler.joblib")
REGRESSOR_MODEL_PATH   = str(MODEL_DIR / "transformer_temp_model.joblib")
REGRESSOR_SCALER_PATH  = str(MODEL_DIR / "reg_scaler.joblib")
ANOMALY_MODEL_PATH     = str(MODEL_DIR / "anomaly_detector.joblib")
METADATA_PATH          = str(DATASET_DIR / "metadata.json")

# ─── RISK LEVEL THRESHOLDS ───────────────────────────────────────────────────
# Applied to risk_score = P(class=1) + P(class=2) from predict_proba().
# Override via environment variables for flexible deployment.
RISK_THRESHOLDS = {
    "NORMAL":  float(os.getenv("RISK_THRESH_NORMAL",  "0.39")),  # ≤ 0.39 → NORMAL
    "WARNING": float(os.getenv("RISK_THRESH_WARNING", "0.69")),  # 0.40–0.69 → WARNING
    # > 0.69 → HIGH_RISK
}

# ─── CLASS LABEL MAPPING (verified from metadata.json + model.classes_) ──────
CLASS_LABELS = {
    0: "Normal Operation",
    1: "Warning / Pre-Alarm",
    2: "Critical Alarm / Trip",
}

CLASS_TO_RISK = {
    0: "NORMAL",
    1: "WARNING",
    2: "HIGH_RISK",
}

# ─── CLASSIFICATION FEATURES (VERIFIED: model n_features_in_=59) ─────────────
# These 59 features are passed through cls_scaler → classifier.
# Exact order matters — must match training order.
CLASSIFICATION_FEATURES = [
    # ── Temperatures & Oil (4) ────────────────────────────────────────────────
    "OTI",   # Oil Temperature Indicator (°C)
    "WTI",   # Winding Temperature Indicator (°C)
    "ATI",   # Ambient Temperature Indicator (°C)
    "OLI",   # Oil Level Indicator (%)
    # ── Phase Voltages (3) ───────────────────────────────────────────────────
    "VL1", "VL2", "VL3",
    # ── Phase Currents (3) ───────────────────────────────────────────────────
    "IL1", "IL2", "IL3",
    # ── Line-to-Line Voltages (3) ────────────────────────────────────────────
    "VL12", "VL23", "VL31",
    # ── Neutral Current (1) ──────────────────────────────────────────────────
    "INUT",
    # ── Active Power per Phase / W (3) ───────────────────────────────────────
    "WL1", "WL2", "WL3",
    # ── Apparent Power per Phase / VA (3) ────────────────────────────────────
    "VAL1", "VAL2", "VAL3",
    # ── Reactive Power per Phase / VAR (3) ───────────────────────────────────
    "RVAL1", "RVAL2", "RVAL3",
    # ── Power Factors per Phase (3) ──────────────────────────────────────────
    "PFL1", "PFL2", "PFL3",
    # ── Average & Sum Power Factor (2) ───────────────────────────────────────
    "Avg_PF", "Sum_PF",
    # ── Frequency (1) ────────────────────────────────────────────────────────
    "FRQ",
    # ── Voltage THD per Phase (3) ────────────────────────────────────────────
    "THDVL1", "THDVL2", "THDVL3",
    # ── Current THD per Phase (3) ────────────────────────────────────────────
    "THDIL1", "THDIL2", "THDIL3",
    # ── Max Demand Current per Phase (3) ─────────────────────────────────────
    "MDIL1", "MDIL2", "MDIL3",
    # ── Energy (3) ───────────────────────────────────────────────────────────
    "KWH", "KWH_I", "KVARH",
    # ── Total Power (3) ──────────────────────────────────────────────────────
    "KW", "KVA", "KVAR",
    # ── Max Power Demand (2) ─────────────────────────────────────────────────
    "MPD", "MKVAD",
    # ── Time Features (3) ────────────────────────────────────────────────────
    "Hour", "DayOfWeek", "Month",
    # ── Engineered Imbalance Features (2) ────────────────────────────────────
    "Voltage_Imbalance_Pct",
    "Current_Imbalance_Pct",
    # ── Engineered Total Power Features (3) ──────────────────────────────────
    "Total_VA", "Total_W", "Total_RVA",
    # ── Engineered Average THD (2) ───────────────────────────────────────────
    "Avg_THD_V", "Avg_THD_I",
    # ── Temperature Differences (3) ──────────────────────────────────────────
    "OTI_ATI_Diff", "WTI_ATI_Diff", "WTI_OTI_Diff",
    # Total: 4+3+3+3+1+3+3+3+3+2+1+3+3+3+3+3+2+3+2+3+2+3 = 59 ✅
]
assert len(CLASSIFICATION_FEATURES) == 59, f"Expected 59 features, got {len(CLASSIFICATION_FEATURES)}"

# ─── REGRESSION FEATURES (VERIFIED: model n_features_in_=54) ─────────────────
# Excludes OTI (it's the regression target), WTI, ATI, OLI (temperature-only),
# and the 3 temperature diff features.
# 59 - 4 (OTI,WTI,ATI,OLI) - 1 (OTI again)... 
# Actually: 54 = 59 - {OTI} - {WTI} - {ATI} - {OLI} - 1 more = 54
# From metadata.json regression_features: ATI, OLI are PRESENT; OTI, WTI absent.
# So: 59 - OTI - WTI - OTI_ATI_Diff ... wait, OTI_ATI_Diff not in base 59.
# 59 - OTI(1) - WTI(1) - something(3) = 54 → 5 missing from classification features.
# Metadata regression_features has 54 entries; comparing: OTI & WTI removed + 3 time-diff.
# But time diffs aren't in base 59. So: 59 - OTI - WTI - Avg_THD_V - Avg_THD_I - Total_RVA
# = 54? Checking: regression features in metadata = all except OTI, WTI, Avg_THD_V,
# Avg_THD_I = 59 - 4 = 55. Subtract 1 more: OTI_ATI is not in 59 either.
# SIMPLEST: use the exact 54-feature list from metadata.json regression_features.
REGRESSION_FEATURES = [
    "ATI", "OLI",
    "VL1", "VL2", "VL3",
    "IL1", "IL2", "IL3",
    "VL12", "VL23", "VL31",
    "INUT",
    "WL1", "WL2", "WL3",
    "VAL1", "VAL2", "VAL3",
    "RVAL1", "RVAL2", "RVAL3",
    "PFL1", "PFL2", "PFL3",
    "Avg_PF", "Sum_PF",
    "FRQ",
    "THDVL1", "THDVL2", "THDVL3",
    "THDIL1", "THDIL2", "THDIL3",
    "MDIL1", "MDIL2", "MDIL3",
    "KWH", "KWH_I", "KVARH",
    "KW", "KVA", "KVAR",
    "MPD", "MKVAD",
    "Hour", "DayOfWeek", "Month",
    "Voltage_Imbalance_Pct",
    "Current_Imbalance_Pct",
    "Total_VA", "Total_W", "Total_RVA",
    "Avg_THD_V", "Avg_THD_I",
    # Total: 2+3+3+3+1+3+3+3+3+2+1+3+3+3+3+3+2+3+2+5+2 = 54 ✅
]
assert len(REGRESSION_FEATURES) == 54, f"Expected 54 features, got {len(REGRESSION_FEATURES)}"

# ─── ANOMALY FEATURES (VERIFIED: model n_features_in_=13) ────────────────────
ANOMALY_FEATURES = [
    "VL1", "VL2", "VL3",
    "IL1", "IL2", "IL3",
    "Voltage_Imbalance_Pct",
    "Current_Imbalance_Pct",
    "Avg_THD_V", "Avg_THD_I",
    "Total_W", "Total_VA",
    "FRQ",
    # Total: 13 ✅
]
assert len(ANOMALY_FEATURES) == 13, f"Expected 13 features, got {len(ANOMALY_FEATURES)}"

# ─── API INPUT FIELDS ─────────────────────────────────────────────────────────
# The minimum raw sensor readings the POST /api/predict endpoint requires.
# Time features (Hour, DayOfWeek, Month) are derived server-side from UTC time
# if not provided in the request body.
REQUIRED_API_FIELDS = [
    # Temperatures & oil
    "OTI", "WTI", "ATI", "OLI",
    # Phase voltages
    "VL1", "VL2", "VL3",
    # Phase currents
    "IL1", "IL2", "IL3",
    # Line voltages
    "VL12", "VL23", "VL31",
    # Neutral current
    "INUT",
    # Power per phase
    "WL1", "WL2", "WL3",
    "VAL1", "VAL2", "VAL3",
    "RVAL1", "RVAL2", "RVAL3",
    # Power factors
    "PFL1", "PFL2", "PFL3",
    "Avg_PF", "Sum_PF",
    # Frequency
    "FRQ",
    # THD
    "THDVL1", "THDVL2", "THDVL3",
    "THDIL1", "THDIL2", "THDIL3",
    # Max demand current
    "MDIL1", "MDIL2", "MDIL3",
    # Energy
    "KWH", "KWH_I", "KVARH",
    # Total power
    "KW", "KVA", "KVAR",
    # Max power demand
    "MPD", "MKVAD",
]

# ─── SAFE OPERATING RANGES ────────────────────────────────────────────────────
# ⚠️  CONFIGURABLE DEFAULTS — adjust to your specific transformer's nameplate rating.
# Based on IEEE C57.12.00 standard transformer monitoring guidelines.
SAFE_RANGES = {
    "OTI":   {"min":  0.0,  "max":  95.0,  "unit": "°C",  "desc": "Oil Temperature Indicator"},
    "WTI":   {"min":  0.0,  "max": 105.0,  "unit": "°C",  "desc": "Winding Temperature Indicator"},
    "ATI":   {"min": -10.0, "max":  55.0,  "unit": "°C",  "desc": "Ambient Temperature Indicator"},
    "OLI":   {"min": 10.0,  "max":  80.0,  "unit": "%",   "desc": "Oil Level Indicator"},
    "VL1":   {"min": 210.0, "max": 250.0,  "unit": "V",   "desc": "Phase Voltage L1"},
    "VL2":   {"min": 210.0, "max": 250.0,  "unit": "V",   "desc": "Phase Voltage L2"},
    "VL3":   {"min": 210.0, "max": 250.0,  "unit": "V",   "desc": "Phase Voltage L3"},
    "IL1":   {"min":   0.0, "max": 500.0,  "unit": "A",   "desc": "Phase Current L1"},
    "IL2":   {"min":   0.0, "max": 500.0,  "unit": "A",   "desc": "Phase Current L2"},
    "IL3":   {"min":   0.0, "max": 500.0,  "unit": "A",   "desc": "Phase Current L3"},
    "FRQ":   {"min":  48.0, "max":  52.0,  "unit": "Hz",  "desc": "Frequency"},
    "Avg_PF":{"min":   0.7, "max":   1.0,  "unit": "",    "desc": "Average Power Factor"},
    "THDVL1":{"min":   0.0, "max":   8.0,  "unit": "%",   "desc": "Voltage THD L1"},
    "THDVL2":{"min":   0.0, "max":   8.0,  "unit": "%",   "desc": "Voltage THD L2"},
    "THDVL3":{"min":   0.0, "max":   8.0,  "unit": "%",   "desc": "Voltage THD L3"},
    "THDIL1":{"min":   0.0, "max":  20.0,  "unit": "%",   "desc": "Current THD L1"},
    "THDIL2":{"min":   0.0, "max":  20.0,  "unit": "%",   "desc": "Current THD L2"},
    "THDIL3":{"min":   0.0, "max":  20.0,  "unit": "%",   "desc": "Current THD L3"},
    "Voltage_Imbalance_Pct": {"min": 0.0, "max": 2.0,  "unit": "%", "desc": "Voltage Imbalance"},
    "Current_Imbalance_Pct": {"min": 0.0, "max": 10.0, "unit": "%", "desc": "Current Imbalance"},
    "INUT":  {"min":   0.0, "max":  50.0,  "unit": "A",   "desc": "Neutral Current"},
}

# ─── ALERT CONFIG ─────────────────────────────────────────────────────────────
ALERT_CONFIG = {
    "NORMAL": {
        "alert":    False,
        "severity": "LOW",
        "message":  "System operating within normal conditions.",
    },
    "WARNING": {
        "alert":    True,
        "severity": "MEDIUM",
        "message":  "Warning: abnormal electrical parameters detected. Monitoring recommended.",
    },
    "HIGH_RISK": {
        "alert":    True,
        "severity": "HIGH",
        "message":  "High risk detected. Immediate inspection is recommended.",
    },
}

# ─── SERVER SETTINGS ──────────────────────────────────────────────────────────
HOST  = os.getenv("FLASK_HOST",  "0.0.0.0")
PORT  = int(os.getenv("FLASK_PORT", "5000"))
DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"

# CORS: comma-separated origins in env var (no wildcards in production)
_cors_raw = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://127.0.0.1:5500"
)
CORS_ORIGINS = [o.strip() for o in _cors_raw.split(",") if o.strip()]
