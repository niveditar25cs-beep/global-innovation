"""
test_api_endpoints.py — Flask API endpoint automated tests
Smart City Transformer Monitoring — Backend Member 2 (ML Integration)
"""

import sys
import os
import json
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Add backend directory to sys.path
_backend = os.path.dirname(os.path.abspath(__file__))
if _backend not in sys.path:
    sys.path.insert(0, _backend)

from app import app, startup

def run_api_tests():
    print("=" * 60)
    print("  TESTING FLASK API ENDPOINTS")
    print("=" * 60)

    # Initialize models
    startup()
    client = app.test_client()

    # 1. Test Root GET /
    print("\n[TEST 1] GET /")
    res = client.get("/")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.get_json()
    assert data["status"] == "running"
    print("  -> Passed. Response:", data)

    # 2. Test GET /api/model/status
    print("\n[TEST 2] GET /api/model/status")
    res = client.get("/api/model/status")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.get_json()
    assert "classifier" in data
    assert data["model_loaded"] is True
    print("  -> Passed. Model status:", data["classifier"])

    # 3. Test POST /api/predict with full valid payload
    print("\n[TEST 3] POST /api/predict (Valid Reading)")
    sample_payload = {
        "OTI": 42.0, "WTI": 55.0, "ATI": 28.0, "OLI": 50.0,
        "VL1": 235.4, "VL2": 234.8, "VL3": 236.0,
        "VL12": 407.5, "VL23": 406.9, "VL31": 408.2,
        "IL1": 45.0, "IL2": 44.5, "IL3": 45.5,
        "INUT": 2.0,
        "WL1": 10500.0, "WL2": 10400.0, "WL3": 10600.0,
        "VAL1": 10620.0, "VAL2": 10520.0, "VAL3": 10720.0,
        "RVAL1": 1600.0, "RVAL2": 1580.0, "RVAL3": 1620.0,
        "PFL1": 0.989, "PFL2": 0.988, "PFL3": 0.990,
        "Avg_PF": 0.989, "Sum_PF": 2.967,
        "FRQ": 50.0,
        "THDVL1": 1.2, "THDVL2": 1.3, "THDVL3": 1.1,
        "THDIL1": 3.5, "THDIL2": 3.4, "THDIL3": 3.6,
        "MDIL1": 50.0, "MDIL2": 50.0, "MDIL3": 50.0,
        "KWH": 1250.5, "KWH_I": 0.0, "KVARH": 190.5,
        "KW": 31.5, "KVA": 31.86, "KVAR": 4.8,
        "MPD": 32.0, "MKVAD": 32.5
    }
    res = client.post(
        "/api/predict",
        data=json.dumps(sample_payload),
        content_type="application/json"
    )
    assert res.status_code == 200, f"Expected 200, got {res.status_code} ({res.data.decode()})"
    pred_data = res.get_json()
    print("  -> Passed. Response keys:", list(pred_data.keys()))
    print("     Risk Level:", pred_data["prediction"]["risk_level"])
    print("     Risk Score:", pred_data["prediction"]["risk_score"])
    print("     Alert Severity:", pred_data["alert"]["severity"])
    print("     Anomaly Detected:", pred_data["anomaly_detection"]["is_anomaly"])
    assert "prediction" in pred_data
    assert "risk_level" in pred_data["prediction"]
    assert "alert" in pred_data
    assert "explanation" in pred_data

    # 4. Test POST /api/predict with missing required fields
    print("\n[TEST 4] POST /api/predict (Missing Fields)")
    res = client.post(
        "/api/predict",
        data=json.dumps({"OTI": 42.0}),
        content_type="application/json"
    )
    assert res.status_code == 400, f"Expected 400, got {res.status_code}"
    err_data = res.get_json()
    assert "errors" in err_data
    print("  -> Passed. Correctly rejected missing fields:", err_data["errors"][0][:60], "...")

    # 5. Test POST /api/predict with invalid data type
    print("\n[TEST 5] POST /api/predict (Invalid Data Type)")
    bad_payload = dict(sample_payload)
    bad_payload["OTI"] = "NOT_A_NUMBER"
    res = client.post(
        "/api/predict",
        data=json.dumps(bad_payload),
        content_type="application/json"
    )
    assert res.status_code == 400, f"Expected 400, got {res.status_code}"
    err_data = res.get_json()
    assert "errors" in err_data
    print("  -> Passed. Correctly rejected invalid data type:", err_data["errors"])

    # 6. Test POST /api/predict without JSON content-type
    print("\n[TEST 6] POST /api/predict (Empty/Non-JSON Body)")
    res = client.post("/api/predict", data="not json", content_type="text/plain")
    assert res.status_code == 400, f"Expected 400, got {res.status_code}"
    print("  -> Passed. Rejected non-JSON body.")

    # 7. Test 404 handler
    print("\n[TEST 7] GET /api/non_existent_endpoint")
    res = client.get("/api/non_existent_endpoint")
    assert res.status_code == 404, f"Expected 404, got {res.status_code}"
    print("  -> Passed. Returned 404 for unknown endpoint.")

    # 8. Test GET /dashboard
    print("\n[TEST 8] GET /dashboard")
    res = client.get("/dashboard")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert b"Smart City Transformer" in res.data
    print("  -> Passed. Served dashboard HTML successfully.")

    # 9. Test Single Out-of-Range Parameter in POST /api/predict
    print("\n[TEST 9] POST /api/predict (Single Parameter Slightly Out-of-Range)")
    single_out_payload = dict(sample_payload)
    single_out_payload["OTI"] = 96.0  # IEEE Safe max is 95.0, everything else normal
    res = client.post(
        "/api/predict",
        data=json.dumps(single_out_payload),
        content_type="application/json"
    )
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    out_data = res.get_json()
    abnormal_params = out_data.get("abnormal_parameters", [])
    flagged_names = [p["parameter"] for p in abnormal_params]
    risk_level = out_data["prediction"]["risk_level"]
    print("  -> Flagged abnormal parameters:", flagged_names)
    print("  -> Resulting risk level:", risk_level)
    assert "OTI" in flagged_names, f"Expected 'OTI' to be flagged, got {flagged_names}"
    assert len(abnormal_params) == 1, f"Expected exactly 1 flagged parameter, got {len(abnormal_params)}"
    assert risk_level != "HIGH_RISK", f"Single mild deviation must NOT trigger HIGH_RISK, got {risk_level}"
    print("  -> Passed. Isolated parameter flagged without triggering HIGH_RISK.")

    print("\n" + "=" * 60)
    print("  ALL API ENDPOINT TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_api_tests()
