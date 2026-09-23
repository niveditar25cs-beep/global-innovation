"""
test_safety_net_demonstration.py — Demonstrate multi-layer safety net override
Smart City Transformer Monitoring — Backend Member 2 (ML Integration)
"""

import sys
import os
import json
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_backend = os.path.dirname(os.path.abspath(__file__))
if _backend not in sys.path:
    sys.path.insert(0, _backend)

from app import app, startup
from ml.preprocessing import engineer_features, build_classification_array, build_anomaly_array

def demonstrate_safety_net():
    print("=" * 80)
    print("MULTI-LAYER SAFETY NET VERIFICATION & DEMONSTRATION")
    print("=" * 80)

    startup()
    client = app.test_client()

    import ml.predictor as predictor

    # 1. Base input reading with LOW energy and nominal electrical parameters
    # The classifier weights KWH/KVARH at 31.6%, so low energy rows produce low classifier risk scores.
    payload = {
        "OTI": 98.5,    # <-- VIOLATION: IEEE C57.12 safe max is 95.0°C
        "WTI": 108.0,   # <-- VIOLATION: IEEE C57.12 safe max is 105.0°C
        "ATI": 30.0,
        "OLI": 50.0,
        "VL1": 235.0, "VL2": 235.0, "VL3": 235.0,
        "VL12": 407.0, "VL23": 407.0, "VL31": 407.0,
        "IL1": 40.0, "IL2": 40.0, "IL3": 40.0,
        "INUT": 1.0,
        "WL1": 9400.0, "WL2": 9400.0, "WL3": 9400.0,
        "VAL1": 9400.0, "VAL2": 9400.0, "VAL3": 9400.0,
        "RVAL1": 500.0, "RVAL2": 500.0, "RVAL3": 500.0,
        "PFL1": 0.99, "PFL2": 0.99, "PFL3": 0.99,
        "Avg_PF": 0.99, "Sum_PF": 2.97,
        "FRQ": 50.0,
        "THDVL1": 1.5, "THDVL2": 1.5, "THDVL3": 1.5,
        "THDIL1": 2.5, "THDIL2": 2.5, "THDIL3": 2.5,
        "MDIL1": 45.0, "MDIL2": 45.0, "MDIL3": 45.0,
        "KWH": 500.0,    # Low cumulative energy
        "KWH_I": 0.0,
        "KVARH": 80.0,   # Low cumulative reactive energy
        "KW": 28.2, "KVA": 28.2, "KVAR": 1.5,
        "MPD": 30.0, "MKVAD": 30.0
    }

    print("\n[STEP 1] Inspecting Raw Supervised Classifier Behavior Alone:")
    feat = engineer_features(payload)
    X_clf = build_classification_array(feat, predictor._clf_scaler)
    clf_res = predictor.predict_classification(X_clf)
    print(f"  Classifier Predicted Class:  {clf_res['prediction']} ({clf_res['class_label']})")
    print(f"  Classifier Raw Probabilities: {clf_res['probabilities']}")
    print(f"  Classifier Alone Risk Score:  {clf_res['risk_score']:.4f}")
    classifier_alone_level = "NORMAL" if clf_res['risk_score'] <= 0.39 else ("WARNING" if clf_res['risk_score'] <= 0.69 else "HIGH_RISK")
    print(f"  Classifier Alone Risk Level:  {classifier_alone_level}")
    print(f"  => NOTE: Because cumulative energy is low (KWH=500), the classifier alone predicts {classifier_alone_level}!")

    print("\n[STEP 2] Inspecting Unsupervised Anomaly Detector & Validation Flags:")
    X_anom = build_anomaly_array(feat)
    anom_res = predictor.predict_anomaly(X_anom)
    print(f"  IsolationForest is_anomaly:  {anom_res['is_anomaly']} (score: {anom_res['anomaly_score']:.4f})")

    from ml.validation import detect_abnormal_parameters
    abnormal = detect_abnormal_parameters(feat)
    print(f"  IEEE Threshold Violations:   {len(abnormal)} detected")
    for p in abnormal:
        print(f"    - {p['parameter']}: {p['value']}{p['unit']} ({p['status']}) -> Safe range [{p['safe_min']}, {p['safe_max']} {p['unit']}]")

    print("\n[STEP 3] Executing Full End-to-End POST /api/predict Pipeline:")
    res = client.post("/api/predict", data=json.dumps(payload), content_type="application/json")
    assert res.status_code == 200, f"Error: {res.status_code}"
    data = res.get_json()

    final_pred = data["prediction"]
    final_alert = data["alert"]
    final_expl = data["explanation"]

    print(f"  Final Combined Risk Level:   {final_pred['risk_level']} (Overridden/Supplemented from classifier's {classifier_alone_level})")
    print(f"  Final Alert Severity:        {final_alert['severity']} (Alert Required: {final_alert['required']})")
    print(f"  Alert Message:               {final_alert['message']}")
    print(f"  Explanation Text:\n    {final_expl}")

    print("\n[STEP 4] Assertion Verification:")
    assert final_pred["risk_level"] in ("WARNING", "HIGH_RISK"), f"FAILED: Expected WARNING or HIGH_RISK, got {final_pred['risk_level']}"
    assert final_pred["risk_level"] != "NORMAL", "FAILED: Model silently returned NORMAL despite OTI > 95°C!"
    assert final_alert["required"] is True, "FAILED: Alert was not triggered!"
    print("  ✅ Safety net PASSED: High temperature breach correctly escalated to WARNING/HIGH_RISK and triggered active alert.")

if __name__ == "__main__":
    demonstrate_safety_net()
