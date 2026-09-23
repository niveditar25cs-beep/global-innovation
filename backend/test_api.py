import sys
from pathlib import Path

# Ensure backend path is configured
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app
from app.data_access.database import init_db, SessionLocal
from app.services.dataset_service import DatasetService

def test_all():
    print("=" * 60)
    print("RUNNING BACKEND MEMBER 1 FOUNDATION VERIFICATION SUITE")
    print("=" * 60)

    # Explicitly initialize database and seed sample data
    init_db()
    db = SessionLocal()
    try:
        from app.models.transformer import Transformer
        from app.models.reading import TransformerReading
        existing = db.query(Transformer).filter(Transformer.transformer_id == "TR-TEST-99").first()
        if existing:
            db.query(TransformerReading).filter(TransformerReading.transformer_id == existing.id).delete()
            db.delete(existing)
            db.commit()
        ds = DatasetService(db)
        ds.seed_sample_if_empty()
    finally:
        db.close()

    with TestClient(app) as client:
        # 1. Health check
        print("\n1. Testing GET /api/health ...")
        r = client.get("/api/health")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        body = r.json()
        assert body["success"] is True
        assert body["data"]["status"] == "healthy"
        assert body["data"]["database"] == "connected"
        print("   -> PASSED:", body["data"])

        # 2. Dataset info
        print("\n2. Testing GET /api/dataset/info ...")
        r = client.get("/api/dataset/info")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        body = r.json()
        assert body["success"] is True
        assert body["data"]["total_records"] > 0
        assert len(body["data"]["transformers_found"]) >= 5
        print("   -> PASSED: Found", body["data"]["total_records"], "records, transformers:", body["data"]["transformers_found"])

        # 3. Dataset preview
        print("\n3. Testing GET /api/dataset/preview?limit=3 ...")
        r = client.get("/api/dataset/preview?limit=3")
        assert r.status_code == 200
        body = r.json()
        assert len(body["data"]["rows"]) == 3
        print("   -> PASSED: Preview retrieved 3 rows successfully.")

        # 4. List transformers
        print("\n4. Testing GET /api/transformers ...")
        r = client.get("/api/transformers")
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert len(body["data"]["items"]) >= 5
        tr_ids = [t["id"] for t in body["data"]["items"]]
        print("   -> PASSED: Retrieved transformers:", tr_ids)

        # 5. Get specific transformer
        print("\n5. Testing GET /api/transformers/TR-001 ...")
        r = client.get("/api/transformers/TR-001")
        assert r.status_code == 200
        body = r.json()
        assert body["data"]["id"] == "TR-001"
        print("   -> PASSED: Details for TR-001:", body["data"]["name"], "| Status:", body["data"]["status"])

        # 6. Create new transformer
        print("\n6. Testing POST /api/transformers ...")
        new_tr_payload = {
            "id": "TR-TEST-99",
            "name": "Integration Test Transformer Unit 99",
            "location": "Substation Zeta - Test Bay",
            "rating_mva": 50.0,
            "voltage_rating_kv": 66.0,
            "installation_date": "2026-09-01",
            "manufacturer": "General Electric",
            "status": "operational"
        }
        r = client.post("/api/transformers", json=new_tr_payload)
        assert r.status_code == 201
        body = r.json()
        assert body["data"]["id"] == "TR-TEST-99"
        print("   -> PASSED: Successfully registered TR-TEST-99.")

        # 7. Current reading
        print("\n7. Testing GET /api/transformers/TR-001/readings/current ...")
        r = client.get("/api/transformers/TR-001/readings/current")
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert body["data"]["reading"] is not None
        reading = body["data"]["reading"]
        print(f"   -> PASSED: Voltage: {reading['voltage_kv']} kV, Current: {reading['current_a']} A, Oil Temp: {reading['oil_temperature_c']} C")

        # 8. Next reading (simulated sensor playback stream)
        print("\n8. Testing GET /api/transformers/TR-001/readings/next (advance cursor) ...")
        r1 = client.get("/api/transformers/TR-001/readings/next")
        assert r1.status_code == 200
        reading1 = r1.json()["data"]["reading"]
        
        r2 = client.get("/api/transformers/TR-001/readings/next")
        assert r2.status_code == 200
        reading2 = r2.json()["data"]["reading"]

        print(f"   Reading 1 timestamp: {reading1['timestamp']}")
        print(f"   Reading 2 timestamp: {reading2['timestamp']}")
        assert reading1["timestamp"] != reading2["timestamp"], "Cursor did not advance!"
        print("   -> PASSED: Cursor advanced to sequential next reading.")

        # 9. Reset stream
        print("\n9. Testing POST /api/transformers/TR-001/readings/reset-stream ...")
        r_reset = client.post("/api/transformers/TR-001/readings/reset-stream")
        assert r_reset.status_code == 200
        assert r_reset.json()["data"]["status"] == "stream_cursor_reset"
        print("   -> PASSED: Cursor reset confirmed.")

        # 10. Reading history with pagination
        print("\n10. Testing GET /api/transformers/TR-001/readings/history?limit=5&order=asc ...")
        r_hist = client.get("/api/transformers/TR-001/readings/history?limit=5&order=asc")
        assert r_hist.status_code == 200
        body = r_hist.json()
        assert len(body["data"]["items"]) == 5
        assert body["data"]["pagination"]["total"] > 100
        print(f"   -> PASSED: Retrieved 5 historical items, total in series: {body['data']['pagination']['total']}")

        # 11. Record new reading
        print("\n11. Testing POST /api/transformers/TR-TEST-99/readings ...")
        record_payload = {
            "voltage_kv": 65.8,
            "current_a": 210.5,
            "load_percentage": 58.2,
            "oil_temperature_c": 54.5,
            "winding_temperature_c": 62.1,
            "oil_level_pct": 89.0,
            "vibration_mm_s": 1.15,
            "dissolved_gas_ppm": 32.0,
            "ambient_temperature_c": 27.0,
            "humidity_pct": 52.0
        }
        r_rec = client.post("/api/transformers/TR-TEST-99/readings", json=record_payload)
        assert r_rec.status_code == 201
        rec_body = r_rec.json()
        assert rec_body["data"]["transformer_id"] == "TR-TEST-99"
        print("   -> PASSED: Ingested live reading successfully.")

        # 12. Network summary
        print("\n12. Testing GET /api/network/summary ...")
        r_sum = client.get("/api/network/summary")
        assert r_sum.status_code == 200
        sum_body = r_sum.json()
        assert sum_body["data"]["total_transformers"] >= 6
        assert sum_body["data"]["status_breakdown"]["operational"] >= 6
        print("   -> PASSED: Network summary:", sum_body["data"])

        # 13. Network topology
        print("\n13. Testing GET /api/network/topology ...")
        r_top = client.get("/api/network/topology")
        assert r_top.status_code == 200
        top_body = r_top.json()
        assert top_body["data"]["total_nodes"] >= 6
        print(f"   -> PASSED: Retrieved topology with {top_body['data']['total_nodes']} network nodes.")

        # 14. Error handling: 404 Not Found
        print("\n14. Testing error handling (404 Not Found) for non-existent transformer ...")
        r_404 = client.get("/api/transformers/NON-EXISTENT-XYZ")
        assert r_404.status_code == 404
        err_body = r_404.json()
        assert err_body["success"] is False
        assert err_body["error"]["code"] == "RESOURCE_NOT_FOUND"
        print("   -> PASSED: Received standardized 404 response:", err_body["error"])

        # 15. Error handling: 422 Validation Error
        print("\n15. Testing error handling (422 Validation Error) for invalid payload ...")
        bad_payload = {
            "voltage_kv": -10.0,  # Negative voltage is invalid (gt=0)
            "current_a": -5.0
        }
        r_422 = client.post("/api/transformers/TR-001/readings", json=bad_payload)
        assert r_422.status_code == 422
        val_body = r_422.json()
        assert val_body["success"] is False
        assert val_body["error"]["code"] == "REQUEST_VALIDATION_FAILED"
        print("   -> PASSED: Received standardized 422 validation response:", val_body["error"]["code"])

        # Cleanup test transformer
        client.delete("/api/transformers/TR-TEST-99")
        print("\nCleaned up TR-TEST-99.")
        print("\n" + "=" * 60)
        print("ALL 15 VERIFICATION CHECKS PASSED SUCCESSFULLY!")
        print("=" * 60)

if __name__ == "__main__":
    test_all()
