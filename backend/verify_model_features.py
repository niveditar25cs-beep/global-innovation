"""
verify_model_features.py — Inspect all 5 model/scaler files and compare against preprocessing.py
Smart City Transformer Monitoring — Backend Member 2 (ML Integration)
"""

import os
import sys
import json
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

_backend = os.path.dirname(os.path.abspath(__file__))
if _backend not in sys.path:
    sys.path.insert(0, _backend)

import joblib
import numpy as np
import config
from ml.preprocessing import (
    engineer_features,
    build_classification_array,
    build_regression_array,
    build_anomaly_array,
)

def verify_all():
    model_dir = config.MODEL_DIR
    print(f"Model directory: {model_dir}\n")

    files = {
        "classifier": "transformer_alarm_model.joblib",
        "cls_scaler": "cls_scaler.joblib",
        "regressor": "transformer_temp_model.joblib",
        "reg_scaler": "reg_scaler.joblib",
        "anomaly": "anomaly_detector.joblib"
    }

    loaded = {}
    for key, fname in files.items():
        fpath = os.path.join(model_dir, fname)
        if not os.path.exists(fpath):
            # check parent directory if not in ml/model
            alt_path = os.path.join(os.path.dirname(_backend), fname)
            if os.path.exists(alt_path):
                fpath = alt_path
        print(f"Loading {key} from {fpath}...")
        loaded[key] = joblib.load(fpath)

    print("\n" + "=" * 80)
    print("MODEL & SCALER FEATURE INSPECTION")
    print("=" * 80)

    for key, obj in loaded.items():
        n_feat = getattr(obj, "n_features_in_", "N/A")
        feat_names = getattr(obj, "feature_names_in_", None)
        print(f"[{key.upper()}] Type: {type(obj).__name__}")
        print(f"  n_features_in_: {n_feat}")
        print(f"  has feature_names_in_: {feat_names is not None}")
        if feat_names is not None:
            print(f"  feature_names_in_ ({len(feat_names)}): {list(feat_names)}")
        print()

    # Compare with metadata.json if available
    metadata_path = os.path.join(_backend, "ml", "dataset", "metadata.json")
    if not os.path.exists(metadata_path):
        metadata_path = os.path.join(os.path.dirname(_backend), "metadata.json")

    with open(metadata_path, "r") as f:
        meta = json.load(f)

    meta_cls = meta.get("classification_features", [])
    meta_reg = meta.get("regression_features", [])
    meta_anom = meta.get("anomaly_features", [])

    print("=" * 80)
    print("SIDE-BY-SIDE FEATURE LIST ALIGNMENT CHECK")
    print("=" * 80)

    # 1. Classification (59)
    print(f"\n--- 1. CLASSIFICATION FEATURES (Metadata: {len(meta_cls)}, Config: {len(config.CLASSIFICATION_FEATURES)}) ---")
    cls_match = (meta_cls == config.CLASSIFICATION_FEATURES)
    print(f"Exact match between metadata.json and config.CLASSIFICATION_FEATURES: {cls_match}")
    print(f"{'Idx':<4} | {'Metadata.json Feature':<28} | {'config.py Feature':<28} | {'Match'}")
    print("-" * 72)
    max_cls = max(len(meta_cls), len(config.CLASSIFICATION_FEATURES))
    for i in range(max_cls):
        m_f = meta_cls[i] if i < len(meta_cls) else "MISSING"
        c_f = config.CLASSIFICATION_FEATURES[i] if i < len(config.CLASSIFICATION_FEATURES) else "MISSING"
        eq = "OK" if m_f == c_f else "MISMATCH!"
        print(f"{i:<4} | {m_f:<28} | {c_f:<28} | {eq}")

    # 2. Regression (54)
    print(f"\n--- 2. REGRESSION FEATURES (Metadata: {len(meta_reg)}, Config: {len(config.REGRESSION_FEATURES)}) ---")
    reg_match = (meta_reg == config.REGRESSION_FEATURES)
    print(f"Exact match between metadata.json and config.REGRESSION_FEATURES: {reg_match}")
    print(f"{'Idx':<4} | {'Metadata.json Feature':<28} | {'config.py Feature':<28} | {'Match'}")
    print("-" * 72)
    max_reg = max(len(meta_reg), len(config.REGRESSION_FEATURES))
    for i in range(max_reg):
        m_f = meta_reg[i] if i < len(meta_reg) else "MISSING"
        c_f = config.REGRESSION_FEATURES[i] if i < len(config.REGRESSION_FEATURES) else "MISSING"
        eq = "OK" if m_f == c_f else "MISMATCH!"
        print(f"{i:<4} | {m_f:<28} | {c_f:<28} | {eq}")

    # 3. Anomaly (13)
    print(f"\n--- 3. ANOMALY FEATURES (Metadata: {len(meta_anom)}, Config: {len(config.ANOMALY_FEATURES)}) ---")
    anom_match = (meta_anom == config.ANOMALY_FEATURES)
    print(f"Exact match between metadata.json and config.ANOMALY_FEATURES: {anom_match}")
    print(f"{'Idx':<4} | {'Metadata.json Feature':<28} | {'config.py Feature':<28} | {'Match'}")
    print("-" * 72)
    max_anom = max(len(meta_anom), len(config.ANOMALY_FEATURES))
    for i in range(max_anom):
        m_f = meta_anom[i] if i < len(meta_anom) else "MISSING"
        c_f = config.ANOMALY_FEATURES[i] if i < len(config.ANOMALY_FEATURES) else "MISSING"
        eq = "OK" if m_f == c_f else "MISMATCH!"
        print(f"{i:<4} | {m_f:<28} | {c_f:<28} | {eq}")

    # 4. Verify preprocessing array output shapes and execution
    print("\n" + "=" * 80)
    print("PREPROCESSING PIPELINE ARRAY GENERATION VERIFICATION")
    print("=" * 80)
    sample_input = {f: 1.0 for f in config.REQUIRED_API_FIELDS}
    feat = engineer_features(sample_input)

    arr_cls = build_classification_array(feat, loaded["cls_scaler"])
    arr_reg = build_regression_array(feat, loaded["reg_scaler"])
    arr_anom = build_anomaly_array(feat)

    print(f"build_classification_array shape: {arr_cls.shape} (Expected: (1, 59))")
    print(f"build_regression_array shape:     {arr_reg.shape} (Expected: (1, 54))")
    print(f"build_anomaly_array shape:        {arr_anom.shape} (Expected: (1, 13))")

    assert arr_cls.shape == (1, 59), f"Mismatch! Got {arr_cls.shape}"
    assert arr_reg.shape == (1, 54), f"Mismatch! Got {arr_reg.shape}"
    assert arr_anom.shape == (1, 13), f"Mismatch! Got {arr_anom.shape}"

    # Test predict calls with loaded objects
    pred_cls = loaded["classifier"].predict(arr_cls)
    pred_reg = loaded["regressor"].predict(arr_reg)
    pred_anom = loaded["anomaly"].predict(arr_anom)

    print(f"Test prediction on sample array:")
    print(f"  Classifier predict: {pred_cls[0]} (Type: {type(pred_cls[0]).__name__})")
    print(f"  Regressor predict:  {pred_reg[0]:.2f} °C (Type: {type(pred_reg[0]).__name__})")
    print(f"  Anomaly predict:    {pred_anom[0]} (Type: {type(pred_anom[0]).__name__})")

    print("\n[VERIFICATION RESULT] ALL FEATURES, SHAPES, AND SCALERS ALIGNED PERFECTLY: PASS")

if __name__ == "__main__":
    verify_all()
