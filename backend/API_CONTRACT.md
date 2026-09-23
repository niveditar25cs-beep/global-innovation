# Smart City Transformer Risk Engine — API Contract & Integration Reference

**Target Audience:** Frontend Developers, Mobile Engineers, Backend Teammates  
**Base URL:** `http://localhost:5000` (or configured host/port)  
**Content-Type:** `application/json`

---

## 1. Health & Model Status: `GET /api/model/status`

Use this endpoint on frontend dashboard startup to verify that the ML inference engine, scikit-learn models, and scalers are loaded and ready.

### Request
- **Method:** `GET`
- **Path:** `/api/model/status`
- **Headers:** `Accept: application/json`

### cURL Example
```bash
curl -X GET http://localhost:5000/api/model/status
```

### Response (`200 OK`)
```json
{
  "model_loaded": true,
  "load_error": null,
  "classifier": {
    "loaded": true,
    "type": "RandomForestClassifier",
    "classes": [0, 1, 2],
    "n_estimators": 200,
    "n_features_in": 59
  },
  "regressor": {
    "loaded": true,
    "type": "RandomForestRegressor",
    "n_features_in": 54
  },
  "anomaly_detector": {
    "loaded": true,
    "type": "IsolationForest",
    "n_features_in": 13
  },
  "sklearn_version": "1.5.2",
  "timestamp": "2026-09-23T14:27:28.123456Z"
}
```

---

## 2. Prediction & Risk Assessment: `POST /api/predict`

Submits raw sensor telemetry to the end-to-end pipeline: validation $\rightarrow$ feature engineering $\rightarrow$ standard scaling $\rightarrow$ multi-model inference $\rightarrow$ risk scoring $\rightarrow$ explanation & alert generation.

### Request Body Schema (Exact 45 Telemetry Fields)
All 45 fields below are required numeric floats/integers:

```json
{
  "OTI": 42.0,
  "WTI": 55.0,
  "ATI": 28.0,
  "OLI": 50.0,
  "VL1": 235.4,
  "VL2": 234.8,
  "VL3": 236.0,
  "VL12": 407.5,
  "VL23": 406.9,
  "VL31": 408.2,
  "IL1": 45.0,
  "IL2": 44.5,
  "IL3": 45.5,
  "INUT": 2.0,
  "WL1": 10500.0,
  "WL2": 10400.0,
  "WL3": 10600.0,
  "VAL1": 10620.0,
  "VAL2": 10520.0,
  "VAL3": 10720.0,
  "RVAL1": 1600.0,
  "RVAL2": 1580.0,
  "RVAL3": 1620.0,
  "PFL1": 0.989,
  "PFL2": 0.988,
  "PFL3": 0.990,
  "Avg_PF": 0.989,
  "Sum_PF": 2.967,
  "FRQ": 50.0,
  "THDVL1": 1.2,
  "THDVL2": 1.3,
  "THDVL3": 1.1,
  "THDIL1": 3.5,
  "THDIL2": 3.4,
  "THDIL3": 3.6,
  "MDIL1": 50.0,
  "MDIL2": 50.0,
  "MDIL3": 50.0,
  "KWH": 1250.5,
  "KWH_I": 0.0,
  "KVARH": 190.5,
  "KW": 31.5,
  "KVA": 31.86,
  "KVAR": 4.8,
  "MPD": 32.0,
  "MKVAD": 32.5
}
```

### Field Definitions & Units
| Field | Description | Unit | Typical Safe Range |
| :--- | :--- | :---: | :--- |
| `OTI` | Oil Temperature Indicator | °C | 0.0 – 95.0 |
| `WTI` | Winding Temperature Indicator | °C | 0.0 – 105.0 |
| `ATI` | Ambient Temperature Indicator | °C | -10.0 – 55.0 |
| `OLI` | Oil Level Indicator | % | 10.0 – 80.0 |
| `VL1`, `VL2`, `VL3` | Line-to-Neutral Phase Voltages | V | 210.0 – 250.0 |
| `VL12`, `VL23`, `VL31` | Line-to-Line Voltages | V | Nominal ~400V |
| `IL1`, `IL2`, `IL3` | Phase Currents | A | 0.0 – 500.0 |
| `INUT` | Neutral Current | A | 0.0 – 50.0 |
| `WL1`, `WL2`, `WL3` | Active Power per Phase | W | Load dependent |
| `VAL1`, `VAL2`, `VAL3` | Apparent Power per Phase | VA | Load dependent |
| `RVAL1`, `RVAL2`, `RVAL3` | Reactive Power per Phase | VAR | Load dependent |
| `PFL1`, `PFL2`, `PFL3` | Power Factor per Phase | - | 0.70 – 1.00 |
| `Avg_PF` | Average 3-Phase Power Factor | - | 0.70 – 1.00 |
| `Sum_PF` | Sum Power Factor Meter Value | - | Signed smart meter metric |
| `FRQ` | System Frequency | Hz | 48.0 – 52.0 |
| `THDVL1`, `THDVL2`, `THDVL3` | Total Harmonic Distortion (Voltage) | % | 0.0 – 8.0 |
| `THDIL1`, `THDIL2`, `THDIL3` | Total Harmonic Distortion (Current) | % | 0.0 – 20.0 |
| `MDIL1`, `MDIL2`, `MDIL3` | Maximum Demand Current | A | Peak historical demand |
| `KWH`, `KWH_I`, `KVARH` | Cumulative Energy & Imported Energy | kWh / kVARh | Cumulative meter counter |
| `KW`, `KVA`, `KVAR` | Total 3-Phase Powers | kW / kVA / kVAR | Load dependent |
| `MPD`, `MKVAD` | Max Power & Reactive Demand | kW / kVAR | Peak power demand |

*(Note: Time features `Hour`, `DayOfWeek`, `Month` are automatically calculated on the server from UTC time if omitted).*

---

### cURL Example: Valid Assessment Call
```bash
curl -X POST http://localhost:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "OTI": 42.0, "WTI": 55.0, "ATI": 28.0, "OLI": 50.0,
    "VL1": 235.4, "VL2": 234.8, "VL3": 236.0,
    "VL12": 407.5, "VL23": 406.9, "VL31": 408.2,
    "IL1": 45.0, "IL2": 44.5, "IL3": 45.5, "INUT": 2.0,
    "WL1": 10500.0, "WL2": 10400.0, "WL3": 10600.0,
    "VAL1": 10620.0, "VAL2": 10520.0, "VAL3": 10720.0,
    "RVAL1": 1600.0, "RVAL2": 1580.0, "RVAL3": 1620.0,
    "PFL1": 0.989, "PFL2": 0.988, "PFL3": 0.990,
    "Avg_PF": 0.989, "Sum_PF": 2.967, "FRQ": 50.0,
    "THDVL1": 1.2, "THDVL2": 1.3, "THDVL3": 1.1,
    "THDIL1": 3.5, "THDIL2": 3.4, "THDIL3": 3.6,
    "MDIL1": 50.0, "MDIL2": 50.0, "MDIL3": 50.0,
    "KWH": 1250.5, "KWH_I": 0.0, "KVARH": 190.5,
    "KW": 31.5, "KVA": 31.86, "KVAR": 4.8,
    "MPD": 32.0, "MKVAD": 32.5
  }'
```

---

### Response (`200 OK`)
```json
{
  "success": true,
  "timestamp": "2026-09-23T14:27:29.123456Z",
  "prediction": {
    "risk_level": "NORMAL",
    "risk_score": 0.4200,
    "class_id": 0,
    "class_label": "Normal Operation",
    "probabilities": {
      "normal": 0.58,
      "warning": 0.375,
      "high_risk": 0.045
    },
    "thresholds_used": {
      "normal_max": 0.39,
      "warning_max": 0.69
    }
  },
  "abnormal_parameters": [],
  "anomaly_detection": {
    "is_anomaly": false,
    "anomaly_score": 0.0521
  },
  "oil_temperature_prediction": {
    "predicted_oti": 41.8
  },
  "explanation": "The transformer monitoring system assessed the current operating state as NORMAL (risk score: 0.42 / 1.00). All primary electrical parameters appear to be within acceptable bounds. The oil temperature model estimates an OTI of 41.8°C, which is within normal thermal operating range.",
  "alert": {
    "required": false,
    "severity": "LOW",
    "risk_level": "NORMAL",
    "message": "System operating within normal conditions."
  }
}
```

### Explanation of Response Fields
- **`prediction.risk_level`**: Primary operational classification:
  - `"NORMAL"`: Risk score $\le 0.39$.
  - `"WARNING"`: Risk score between $0.40$ and $0.69$.
  - `"HIGH_RISK"`: Risk score $\ge 0.70$.
- **`prediction.risk_score`**: Weighted probability of fault/stress ($P(\text{warning}) + P(\text{critical})$).
- **`prediction.probabilities`**: Calibrated multi-class probability breakdown from the 59-feature Random Forest classifier.
- **`abnormal_parameters`**: Array of IEEE C57.12 safety violations with parameter name, current value, status (`"HIGH"` or `"LOW"`), and safe limits.
- **`anomaly_detection`**:
  - `is_anomaly` (boolean): `true` if multidimensional Isolation Forest flags a statistical outlier.
  - `anomaly_score` (float): Negative indicates outlier; positive indicates typical baseline.
- **`oil_temperature_prediction`**: Estimated Top Oil Temperature (`OTI`) in °C from the 54-feature Random Forest regressor. Useful for comparing against actual measured OTI to detect cooling system failure.
- **`explanation`**: Rigorous, non-causal diagnostic summary for human operators.
- **`alert`**: Dispatch object (`required`: bool, `severity`: `"LOW"` | `"MEDIUM"` | `"HIGH"`).

---

### Error Responses

#### 1. Input Validation Failure (`400 Bad Request`)
Returned when required fields are missing, non-numeric, or outside physical feasibility bounds:
```json
{
  "success": false,
  "error": "Input validation failed.",
  "errors": [
    "Missing required field(s): OTI, WTI",
    "'FRQ' value 25.0 is outside physically plausible range [30.0, 70.0]."
  ]
}
```

#### 2. Models Not Available (`503 Service Unavailable`)
Returned if model files failed to load at startup:
```json
{
  "success": false,
  "error": "Prediction model is not available.",
  "detail": "The classification model failed to load at startup. Check server logs."
}
```
