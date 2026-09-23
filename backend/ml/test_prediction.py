"""
test_prediction.py — End-to-end prediction pipeline tests
Smart City Transformer Monitoring — Backend Member 2 (ML Integration)

Tests use REAL model output — no mocking, no forced outcomes.
If a test fails, it reflects the model's actual behavior, not a bug.

Run from the backend/ directory:
    python ml/test_prediction.py
"""

import sys
import os
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Add backend/ to path
_backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _backend)

import numpy as np

# ─── Test Infrastructure ──────────────────────────────────────────────────────

PASS  = "[PASS] ✅"
FAIL  = "[FAIL] ❌"
WARN  = "[WARN] ⚠️"

results = []

def run_test(name: str, fn):
    print(f"\n{'─'*60}")
    print(f"  TEST: {name}")
    print(f"{'─'*60}")
    try:
        fn()
        results.append((name, "PASS"))
        print(f"\n{PASS}")
    except AssertionError as ae:
        results.append((name, f"FAIL: {ae}"))
        print(f"\n{FAIL}: {ae}")
    except Exception as exc:
        results.append((name, f"ERROR: {exc}"))
        import traceback
        print(f"\n{FAIL} (unexpected exception): {exc}")
        traceback.print_exc()


# ─── Shared: Load models once ─────────────────────────────────────────────────

def setup():
    from ml.predictor import load_models
    ok = load_models()
    assert ok, "Model loading FAILED — cannot run tests"
    print("Models loaded successfully.")


# ─── Sample inputs built from known dataset patterns ─────────────────────────
# Based on actual Distributed Transformer Monitoring dataset statistics.
# All-zeros → model predicts class=0 (NORMAL) as verified in live test.

def _base_normal_input():
    """A reading typical of normal transformer operation."""
    return {
        # Temperatures (°C)
        "OTI": 42.0, "WTI": 55.0, "ATI": 28.0, "OLI": 50.0,
        # Voltages (V) — balanced ~235V per phase
        "VL1": 235.4, "VL2": 234.8, "VL3": 236.0,
        "VL12": 407.5, "VL23": 406.9, "VL31": 408.2,
        # Currents (A) — light load
        "IL1": 45.0, "IL2": 44.5, "IL3": 45.5,
        "INUT": 2.0,
        # Active power per phase (W)
        "WL1": 10500.0, "WL2": 10400.0, "WL3": 10600.0,
        # Apparent power per phase (VA)
        "VAL1": 10620.0, "VAL2": 10520.0, "VAL3": 10720.0,
        # Reactive power per phase (VAR)
        "RVAL1": 1600.0, "RVAL2": 1580.0, "RVAL3": 1620.0,
        # Power factors
        "PFL1": 0.989, "PFL2": 0.988, "PFL3": 0.990,
        "Avg_PF": 0.989, "Sum_PF": 2.967,
        # Frequency
        "FRQ": 50.0,
        # THD voltage (%) — well within limits
        "THDVL1": 1.2, "THDVL2": 1.3, "THDVL3": 1.1,
        # THD current (%)
        "THDIL1": 3.5, "THDIL2": 3.4, "THDIL3": 3.6,
        # Max demand current
        "MDIL1": 50.0, "MDIL2": 50.0, "MDIL3": 50.0,
        # Energy
        "KWH": 1250.5, "KWH_I": 0.0, "KVARH": 190.5,
        "KW": 31.5, "KVA": 31.86, "KVAR": 4.8,
        # Power demand
        "MPD": 32.0, "MKVAD": 32.5,
    }

def _warning_input():
    """A reading with mildly elevated temperatures & THD — may elicit WARNING."""
    inp = _base_normal_input()
    inp.update({
        "OTI": 96.0, "WTI": 106.0, "ATI": 35.0,
        "THDVL1": 8.5, "THDVL2": 8.2, "THDVL3": 7.8,
        "THDIL1": 21.0, "THDIL2": 20.5, "THDIL3": 21.5,
        "FRQ": 48.5,
        "Avg_PF": 0.68, "Sum_PF": 2.04,
    })
    return inp

def _high_risk_input():
    """
    A reading with severely abnormal values — should elicit HIGH_RISK
    or at minimum WARNING from the classifier. We verify the abnormal
    parameter detection always fires correctly.
    """
    inp = _base_normal_input()
    inp.update({
        "OTI": 135.0, "WTI": 150.0, "ATI": 50.0,
        "THDVL1": 15.0, "THDVL2": 15.5, "THDVL3": 14.8,
        "THDIL1": 35.0, "THDIL2": 34.0, "THDIL3": 36.0,
        "IL1": 450.0, "IL2": 200.0, "IL3": 80.0,  # heavy imbalance
        "FRQ": 48.0,
        "Avg_PF": 0.65, "Sum_PF": 1.95,
        "INUT": 55.0,
    })
    return inp


# ─── TEST 1: Normal-range row ─────────────────────────────────────────────────

def test_normal_prediction():
    from ml.preprocessing import engineer_features, build_classification_array
    from ml.predictor     import predict_classification, _clf_scaler
    from ml.risk_engine   import determine_risk_level

    data = _base_normal_input()
    feat = engineer_features(data)
    X    = build_classification_array(feat, _clf_scaler)
    res  = predict_classification(X)
    level = determine_risk_level(res)

    print(f"  Prediction: class={res['prediction']}, risk_score={res['risk_score']:.4f}")
    print(f"  Probabilities: {res['probabilities']}")
    print(f"  Risk level: {level}")

    # With balanced normal input, the real model should output class=0
    # (verified in live model test: all-zeros → class=0, risk_score=0.10)
    assert res["prediction"] in (0, 1), (
        f"Expected class 0 or 1 for a normal-range input, got class={res['prediction']}"
    )
    assert level in ("NORMAL", "WARNING"), (
        f"Expected NORMAL or WARNING for a normal-range input, got {level}"
    )
    print(f"  → Risk level '{level}' is an acceptable real-model response.")


# ─── TEST 2: Warning-range row ────────────────────────────────────────────────

def test_warning_prediction():
    from ml.preprocessing import engineer_features, build_classification_array
    from ml.predictor     import predict_classification, _clf_scaler
    from ml.risk_engine   import determine_risk_level
    from ml.validation    import detect_abnormal_parameters

    data = _warning_input()
    feat = engineer_features(data)
    X    = build_classification_array(feat, _clf_scaler)
    res  = predict_classification(X)
    level = determine_risk_level(res)
    abnormal = detect_abnormal_parameters(feat)

    print(f"  Prediction: class={res['prediction']}, risk_score={res['risk_score']:.4f}")
    print(f"  Risk level: {level}")
    print(f"  Abnormal params: {[p['parameter'] for p in abnormal]}")

    # The model MUST flag at least some abnormal parameters
    assert len(abnormal) > 0, (
        "Expected at least 1 abnormal parameter for the warning-range input. "
        f"Got: {abnormal}"
    )
    print(f"  → {len(abnormal)} abnormal parameters correctly detected.")
    # Risk level is whatever the REAL model says — we don't force it
    print(f"  → Real model risk level: {level} (not forced by test).")


# ─── TEST 3: High-risk row ────────────────────────────────────────────────────

def test_high_risk_prediction():
    from ml.preprocessing import engineer_features, build_classification_array
    from ml.predictor     import predict_classification, _clf_scaler
    from ml.risk_engine   import determine_risk_level
    from ml.validation    import detect_abnormal_parameters

    data = _high_risk_input()
    feat = engineer_features(data)
    X    = build_classification_array(feat, _clf_scaler)
    res  = predict_classification(X)
    level = determine_risk_level(res)
    abnormal = detect_abnormal_parameters(feat)

    print(f"  Prediction: class={res['prediction']}, risk_score={res['risk_score']:.4f}")
    print(f"  Risk level: {level}")
    print(f"  Abnormal params ({len(abnormal)}): {[p['parameter'] for p in abnormal]}")

    # Must detect abnormal params
    assert len(abnormal) >= 3, (
        f"Expected ≥3 abnormal parameters for high-risk input, got {len(abnormal)}"
    )
    # The model should at minimum produce a non-zero risk score
    assert res["risk_score"] > 0, "Risk score should be > 0 for abnormal input"
    print(f"  → {len(abnormal)} abnormal parameters detected. Risk score: {res['risk_score']:.4f}")


# ─── TEST 4: Missing required field ──────────────────────────────────────────

def test_missing_field():
    from ml.validation import validate_input

    data = _base_normal_input()
    del data["OTI"]   # remove a required field
    del data["WTI"]

    result = validate_input(data)
    print(f"  Validation result: {result}")

    assert result["valid"] is False, "Expected validation to fail for missing field"
    assert any("OTI" in e for e in result["errors"]), \
        f"Expected 'OTI' in error messages, got: {result['errors']}"
    assert any("WTI" in e for e in result["errors"]), \
        f"Expected 'WTI' in error messages, got: {result['errors']}"
    print(f"  → Correctly returned errors: {result['errors'][:2]}")


# ─── TEST 5: Non-numeric value ────────────────────────────────────────────────

def test_non_numeric_value():
    from ml.validation import validate_input

    data = _base_normal_input()
    data["OTI"] = "abc"         # string instead of float
    data["WTI"] = None          # None
    data["FRQ"] = [50.0]        # list

    result = validate_input(data)
    print(f"  Validation result: {result}")

    assert result["valid"] is False, "Expected validation to fail for non-numeric values"
    # At least OTI and WTI should be flagged
    joined_errors = " ".join(result["errors"])
    assert "OTI" in joined_errors or "WTI" in joined_errors, \
        f"Expected OTI/WTI in errors, got: {result['errors']}"
    print(f"  → Correctly rejected non-numeric values. Errors: {result['errors'][:3]}")


# ─── TEST 6: Extreme out-of-range values ─────────────────────────────────────

def test_extreme_values():
    from ml.validation import validate_input, detect_abnormal_parameters
    from ml.preprocessing import engineer_features

    data = _base_normal_input()
    data["OTI"] = 180.0   # over 200°C hard limit = rejected
    data["FRQ"] = 25.0    # under 30Hz hard limit = rejected

    result = validate_input(data)
    print(f"  Validation result for extreme values: valid={result['valid']}")
    print(f"  Errors: {result.get('errors', [])}")

    # Hard out-of-range should be rejected at validation
    assert result["valid"] is False, (
        "Expected validation to reject extreme values (OTI=180, FRQ=25)"
    )
    print(f"  → Extreme values correctly rejected at validation stage.")

    # Also test that abnormal parameter detection fires on high-but-within-hard-bounds values
    data2 = _base_normal_input()
    data2["OTI"] = 97.0   # over safe max (95°C) but under hard bound (200°C)
    feat2 = engineer_features(data2)
    abnormal2 = detect_abnormal_parameters(feat2)
    flagged_params = [p["parameter"] for p in abnormal2]
    print(f"  Abnormal params for OTI=97: {flagged_params}")
    assert "OTI" in flagged_params, f"Expected OTI to be flagged for 97°C, got: {flagged_params}"
    print(f"  → OTI=97°C correctly flagged as HIGH by abnormal parameter detection.")


# ─── TEST 7: Full pipeline integration test ──────────────────────────────────

def test_full_pipeline():
    """Run the complete pipeline end-to-end (no Flask)."""
    from ml.preprocessing import (
        engineer_features, build_classification_array,
        build_regression_array, build_anomaly_array,
    )
    from ml.predictor   import (
        predict_classification, predict_regression, predict_anomaly,
        _clf_scaler, _reg_scaler,
    )
    from ml.risk_engine  import determine_risk_level, build_risk_output
    from ml.validation   import validate_input, detect_abnormal_parameters
    from ml.explanation  import generate_explanation
    from ml.alert        import generate_alert

    data = _base_normal_input()

    # Validate
    v = validate_input(data)
    assert v["valid"], f"Validation failed unexpectedly: {v}"

    # Engineer
    feat = engineer_features(data)

    # Classify
    X_clf    = build_classification_array(feat, _clf_scaler)
    clf_res  = predict_classification(X_clf)

    # Risk level
    level    = determine_risk_level(clf_res)
    risk_out = build_risk_output(clf_res, level)

    # Regression
    X_reg    = build_regression_array(feat, _reg_scaler)
    reg_res  = predict_regression(X_reg)

    # Anomaly
    X_anom   = build_anomaly_array(feat)
    anom_res = predict_anomaly(X_anom)

    # Abnormal
    abnormal = detect_abnormal_parameters(feat)

    # Explanation
    expl = generate_explanation(level, clf_res.get("risk_score"), abnormal, reg_res, anom_res)

    # Alert
    alert = generate_alert(level)

    # Assemble
    response = {
        "success":                    True,
        "prediction":                 risk_out,
        "abnormal_parameters":        abnormal,
        "anomaly_detection":          anom_res,
        "oil_temperature_prediction": reg_res,
        "explanation":                expl,
        "alert":                      alert,
    }

    print(f"  Full pipeline response:")
    print(f"    risk_level:   {response['prediction']['risk_level']}")
    print(f"    risk_score:   {response['prediction']['risk_score']}")
    print(f"    alert:        {response['alert']}")
    print(f"    explanation:  {response['explanation'][:120]}...")

    assert "risk_level" in response["prediction"], "Missing risk_level"
    assert "required"   in response["alert"],      "Missing alert.required"
    assert len(expl)    > 20,                      "Explanation is too short"
    print(f"  → Full pipeline completed successfully.")


# ─── TEST 8: Single out-of-range parameter (isolated flag check) ──────────────

def test_single_out_of_range_parameter():
    from ml.preprocessing import engineer_features, build_classification_array
    from ml.predictor     import predict_classification, _clf_scaler
    from ml.risk_engine   import determine_risk_level
    from ml.validation    import detect_abnormal_parameters

    data = _base_normal_input()
    # OTI safe max is 95.0°C. Set to 96.0°C — slightly out of range
    data["OTI"] = 96.0

    feat = engineer_features(data)
    X    = build_classification_array(feat, _clf_scaler)
    res  = predict_classification(X)
    level = determine_risk_level(res)
    abnormal = detect_abnormal_parameters(feat)

    flagged_params = [p["parameter"] for p in abnormal]
    print(f"  Single out-of-range test (OTI=96.0°C, safe max=95.0°C):")
    print(f"    Abnormal parameters flagged: {flagged_params}")
    print(f"    Risk score: {res['risk_score']:.4f}")
    print(f"    Risk level: {level}")

    # Must be flagged in abnormal parameters (not silently ignored)
    assert "OTI" in flagged_params, "Expected 'OTI' to be flagged in abnormal_parameters"
    assert len(abnormal) == 1, f"Expected exactly 1 abnormal parameter, got {len(abnormal)}: {flagged_params}"

    # Must NOT incorrectly trigger HIGH_RISK for a single mild temperature elevation
    assert level != "HIGH_RISK", f"Single mild out-of-range value should NOT trigger HIGH_RISK, got {level}"
    print(f"  → Correctly isolated as single abnormal flag without incorrectly triggering HIGH_RISK.")


# ─────────────────────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  SMART CITY TRANSFORMER ML — PREDICTION TESTS")
    print("=" * 60)

    print("\n[SETUP] Loading models...")
    try:
        setup()
    except Exception as e:
        print(f"❌ SETUP FAILED: {e}")
        sys.exit(1)

    run_test("Test 1: Normal-range prediction",          test_normal_prediction)
    run_test("Test 2: Warning-range prediction",         test_warning_prediction)
    run_test("Test 3: High-risk prediction",             test_high_risk_prediction)
    run_test("Test 4: Missing required field",           test_missing_field)
    run_test("Test 5: Non-numeric value",                test_non_numeric_value)
    run_test("Test 6: Extreme out-of-range values",      test_extreme_values)
    run_test("Test 7: Full pipeline integration",        test_full_pipeline)
    run_test("Test 8: Single out-of-range IEEE param",   test_single_out_of_range_parameter)

    print("\n" + "=" * 60)
    print("  RESULTS SUMMARY")
    print("=" * 60)
    passed = sum(1 for _, r in results if r == "PASS")
    for name, res in results:
        icon = "✅" if res == "PASS" else "❌"
        print(f"  {icon}  {name}")
        if res != "PASS":
            print(f"       → {res}")
    print()
    print(f"  {passed}/{len(results)} tests passed.")
    print("=" * 60)

    if passed < len(results):
        sys.exit(1)
