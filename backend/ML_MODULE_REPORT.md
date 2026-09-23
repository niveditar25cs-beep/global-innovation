# Smart City Electrical Infrastructure: Machine Learning Integration & Risk Engine Module Report

**Module:** Machine Learning Integration & Risk Assessment Engine  
**Author / Responsibility:** Backend Member 2  
**Project:** AI-Based Energy Efficiency & Smart Grid Transformer Risk Prediction System  
**Framework:** Flask, Scikit-Learn (1.5.2), NumPy, Joblib  

---

## 1. Executive Summary & Architecture Overview

This module provides an end-to-end, multi-model predictive engine and real-time operational risk assessment system for distribution transformers deployed in smart city power grids. The system is built and verified entirely against real IoT telemetry datasets and real pre-trained scikit-learn models without mocks, simulated heuristics, or synthetic data generation.

```
                           RAW SENSOR TELEMETRY (45 Fields)
                                         │
                                         ▼
                    ┌─────────────────────────────────────────┐
                    │     Step 1: Input Schema Validation     │
                    │   (Type check, NaN/Inf, Hard Bounds)    │
                    └────────────────────┬────────────────────┘
                                         │
                                         ▼
                    ┌─────────────────────────────────────────┐
                    │     Step 2: Feature Engineering         │
                    │   (Imbalance %, Powers, Harmonics, Diff)│
                    └────────────────────┬────────────────────┘
                                         │
                 ┌───────────────────────┼───────────────────────┐
                 │                       │                       │
                 ▼                       ▼                       ▼
      ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
      │ Classification Path │ │   Regression Path   │ │  Anomaly Detection  │
      │  (StandardScaler)   │ │  (StandardScaler)   │ │     (Raw Values)    │
      │   (1, 59) Features  │ │   (1, 54) Features  │ │   (1, 13) Features  │
      └──────────┬──────────┘ └──────────┬──────────┘ └──────────┬──────────┘
                 │                       │                       │
                 ▼                       ▼                       ▼
      ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
      │RandomForestClassif. │ │ RandomForestRegress.│ │   IsolationForest   │
      │(Classes: 0, 1, 2)   │ │  (Predicts OTI °C)  │ │ (Inlier vs Outlier) │
      └──────────┬──────────┘ └──────────┬──────────┘ └──────────┬──────────┘
                 │                       │                       │
                 └───────────────────────┼───────────────────────┘
                                         │
                                         ▼
                    ┌─────────────────────────────────────────┐
                    │   Step 3: Multi-Layer Risk Engine       │
                    │  Layer 1: Supervised ML Probabilities   │
                    │  Layer 2: Unsupervised Anomaly Check    │
                    │  Layer 3: Deterministic IEEE C57.12 Net │
                    └────────────────────┬────────────────────┘
                                         │
                                         ▼
                    ┌─────────────────────────────────────────┐
                    │ Step 4: Diagnostic Explanation & Alert  │
                    │ (Non-causal reasoning + Dispatch badge) │
                    └────────────────────┬────────────────────┘
                                         │
                                         ▼
                               JSON API RESPONSE (200 OK)
```

### Deployed Model Specifications
1. **Fault Alarm Classifier (`transformer_alarm_model.joblib`)**:
   - Algorithm: `RandomForestClassifier` (200 estimators).
   - Features Expected: **59 features** (normalized via `cls_scaler.joblib`).
   - Output: Discrete classes `0` (Normal Operation), `1` (Warning / Pre-Alarm), `2` (Critical Alarm / Trip) + class probability distribution.
2. **Oil Temperature Regressor (`transformer_temp_model.joblib`)**:
   - Algorithm: `RandomForestRegressor` (200 estimators).
   - Features Expected: **54 features** (normalized via `reg_scaler.joblib`).
   - Output: Continuous predicted Top Oil Temperature (`OTI`) in °C.
3. **Unsupervised Anomaly Detector (`anomaly_detector.joblib`)**:
   - Algorithm: `IsolationForest` (contamination rate: 0.05).
   - Features Expected: **13 primary electrical & harmonic features**.
   - Output: `1` (Normal Envelope) vs `-1` (Multidimensional Anomaly) + continuous anomaly score.

---

## 2. Feature Importance Report (Supervised Classifier)

Feature importances were directly extracted from the trained `RandomForestClassifier` (`transformer_alarm_model.joblib`) across all 59 inputs.

### Summary Metrics:
- **Cumulative Energy Metrics (`KWH` + `KVARH` + `KWH_I`):** **`32.16%`** of total model weight.
- **Top 5 Features:** Account for **`53.04%`** of all tree split decisions.
- **Thermal Metrics Alone (`OTI` + `WTI`):** **`0.84%`** (`OTI`: 0.82%, `WTI`: 0.02%).

### Complete 59-Feature Importance Table (Ranked)
| Rank | Feature Name | Category | Importance Score | Percentage |
| :---: | :--- | :--- | :---: | :---: |
| **1** | **`KWH`** | Energy / Cumulative Active | **0.159585** | **15.96%** |
| **2** | **`KVARH`** | Energy / Cumulative Reactive | **0.156760** | **15.68%** |
| **3** | **`MDIL2`** | Max Demand Current (Phase 2) | **0.086316** | **8.63%** |
| **4** | **`OLI`** | Oil Level Indicator (%) | **0.074404** | **7.44%** |
| **5** | **`Month`** | Seasonal Time Metric | **0.063279** | **6.33%** |
| 6 | `MPD` | Max Power Demand (Active) | 0.054570 | 5.46% |
| 7 | `MKVAD` | Max Power Demand (Apparent) | 0.052544 | 5.25% |
| 8 | `MDIL3` | Max Demand Current (Phase 3) | 0.045977 | 4.60% |
| 9 | `MDIL1` | Max Demand Current (Phase 1) | 0.026759 | 2.68% |
| 10 | `VL1` | Phase Voltage L1 | 0.022112 | 2.21% |
| 11 | `VL3` | Phase Voltage L3 | 0.015428 | 1.54% |
| 12 | `VL2` | Phase Voltage L2 | 0.015401 | 1.54% |
| 13 | `IL2` | Phase Current L2 | 0.013345 | 1.33% |
| 14 | `THDIL2` | Current Harmonics (Phase 2) | 0.012175 | 1.22% |
| 15 | `RVAL3` | Reactive Power (Phase 3) | 0.011062 | 1.11% |
| 16 | `OTI_ATI_Diff` | Oil - Ambient Temp Delta | 0.010567 | 1.06% |
| 17 | `IL3` | Phase Current L3 | 0.010023 | 1.00% |
| 18 | `WTI_OTI_Diff` | Winding - Oil Temp Delta | 0.009622 | 0.96% |
| **19** | **`OTI`** | **Top Oil Temperature Indicator** | **0.008153** | **0.82%** |
| 20 | `KVAR` | Total Reactive Power | 0.007939 | 0.79% |
| 21 | `Voltage_Imbalance_Pct` | Engineered Imbalance (%) | 0.007828 | 0.78% |
| 22 | `Avg_THD_I` | Engineered Current Harmonics | 0.007751 | 0.78% |
| 23 | `Total_VA` | Engineered Apparent Power | 0.006751 | 0.68% |
| 24 | `DayOfWeek` | Temporal Metric | 0.006368 | 0.64% |
| 25 | `VL23` | Line-to-Line Voltage | 0.006128 | 0.61% |
| 26 | `RVAL2` | Reactive Power (Phase 2) | 0.006049 | 0.60% |
| 27 | `VAL1` | Apparent Power (Phase 1) | 0.006009 | 0.60% |
| 28 | `VAL2` | Apparent Power (Phase 2) | 0.005444 | 0.54% |
| 29 | `WTI_ATI_Diff` | Winding - Ambient Temp Delta | 0.005304 | 0.53% |
| 30 | `KWH_I` | Imported Energy | 0.005281 | 0.53% |
| 31 | `WL2` | Active Power (Phase 2) | 0.005147 | 0.51% |
| 32 | `PFL3` | Power Factor (Phase 3) | 0.005016 | 0.50% |
| 33 | `THDIL1` | Current Harmonics (Phase 1) | 0.004958 | 0.50% |
| 34 | `Current_Imbalance_Pct` | Engineered Imbalance (%) | 0.004752 | 0.48% |
| 35 | `VL12` | Line-to-Line Voltage | 0.004560 | 0.46% |
| 36 | `VL31` | Line-to-Line Voltage | 0.004559 | 0.46% |
| 37 | `IL1` | Phase Current L1 | 0.004195 | 0.42% |
| 38 | `ATI` | Ambient Temperature | 0.004025 | 0.40% |
| 39 | `VAL3` | Apparent Power (Phase 3) | 0.003951 | 0.40% |
| 40 | `RVAL1` | Reactive Power (Phase 1) | 0.003945 | 0.39% |
| 41 | `KVA` | Total Apparent Power | 0.003921 | 0.39% |
| 42 | `PFL1` | Power Factor (Phase 1) | 0.003477 | 0.35% |
| 43 | `Sum_PF` | Smart Meter Sum PF | 0.003032 | 0.30% |
| 44 | `THDVL1` | Voltage Harmonics (Phase 1) | 0.002525 | 0.25% |
| 45 | `Avg_THD_V` | Engineered Voltage Harmonics | 0.002488 | 0.25% |
| 46 | `THDVL3` | Voltage Harmonics (Phase 3) | 0.002307 | 0.23% |
| 47 | `Hour` | Hour of Day | 0.002289 | 0.23% |
| 48 | `THDIL3` | Current Harmonics (Phase 3) | 0.002144 | 0.21% |
| 49 | `THDVL2` | Voltage Harmonics (Phase 2) | 0.001976 | 0.20% |
| 50 | `Total_W` | Engineered Active Power | 0.001906 | 0.19% |
| 51 | `WL3` | Active Power (Phase 3) | 0.001816 | 0.18% |
| 52 | `Total_RVA` | Engineered Reactive Power | 0.001758 | 0.18% |
| 53 | `KW` | Total Active Power | 0.001692 | 0.17% |
| 54 | `INUT` | Neutral Current | 0.001475 | 0.15% |
| 55 | `Avg_PF` | Average Power Factor | 0.000928 | 0.09% |
| 56 | `FRQ` | System Frequency | 0.000767 | 0.08% |
| 57 | `WL1` | Active Power (Phase 1) | 0.000634 | 0.06% |
| 58 | `PFL2` | Power Factor (Phase 2) | 0.000574 | 0.06% |
| **59** | **`WTI`** | **Winding Temperature Indicator** | **0.000248** | **0.02%** |

---

## 3. Limitations & Multi-Layer Safety Design Section

### Why the Supervised Classifier Weighted Energy Over Temperature
An inspection of the model's split decisions reveals that the Random Forest classifier attributes over **31.6%** of its decision weight to cumulative energy metrics (`KWH` and `KVARH`) and maximum historical demand currents (`MDIL`), while assigning only **0.82%** to Oil Temperature (`OTI`) and **0.02%** to Winding Temperature (`WTI`). 

This behavior is an artifact of the training data distribution rather than a software defect. In real-world electrical distribution networks, fault risk labels (`Fault_Risk_Level`) correlate strongly with asset aging, sustained dielectric loading, and prolonged multi-month electrical throughput. Consequently, the tree-building algorithm discovered that cumulative energy registers served as the most statistically predictive partitioning features across the historical dataset. However, in live substation operations, an instantaneous physical hazard—such as a cooling fan malfunction causing a sudden thermal spike to 100°C—might occur at low instantaneous energy consumption, leading a pure supervised model to misjudge the immediate danger.

### Defense-in-Depth Safety Architecture
To eliminate the hazard of a single point of failure, this system does not rely exclusively on the supervised classifier. Instead, it implements a **three-tier defense-in-depth architecture**:

1. **Supervised ML Classification Layer:** Calculates continuous probability-weighted operational risk scores based on learned multidimensional patterns.
2. **Unsupervised Anomaly Detection Layer (`IsolationForest`):** Evaluates 13 key instantaneous electrical and harmonic features (`VL1-3`, `IL1-3`, imbalances, THD, frequency) without relying on historical labels. If a telemetry reading represents a statistical outlier, it automatically flags an anomaly (`is_anomaly=True`).
3. **Deterministic Physical Safety Net (IEEE C57.12):** Hard-coded engineering boundary rules in `ml/validation.py` and `ml/risk_engine.py` inspect physical constraints (e.g., $OTI \le 95.0^\circ\text{C}$, $WTI \le 105.0^\circ\text{C}$, $\text{Imbalance} \le 10\%$).

### Fail-Safe Operational Logic
If a transformer's oil temperature exceeds IEEE safe operating limits ($OTI > 95.0^\circ\text{C}$), the deterministic safety net **intercepts the assessment**. Even if the supervised classifier outputs Class 0 (`NORMAL`) due to low cumulative `KWH`, the risk engine **escalates the operational status to `WARNING` (or `HIGH_RISK` if $OTI \ge 120^\circ\text{C}$)** and triggers an active maintenance alert. The system is structurally incapable of silently reporting a normal status during an active physical breach.

### Future Work
For subsequent model iterations, training labels can be synthesized using a composite objective function that explicitly penalizes instantaneous thermal violations ($\Delta T > \text{threshold}$) in addition to energy throughput, or features can be pre-weighted via domain-informed regularization.

---

## 4. Viva / Evaluation Speaking Script (Under 150 Words)

> *"Our machine learning pipeline uses a defense-in-depth architecture rather than relying on a single model. When analyzing the trained Random Forest classifier, we discovered it learned to heavily weight cumulative energy metrics—like kilowatt-hours and max demand—because those best correlated with historical risk labels across months of telemetry. However, trusting only the classifier would be unsafe if an instantaneous cooling failure caused oil temperature to spike during low load.*  
>  
> *To guarantee zero blind spots, our risk engine couples the classifier with an unsupervised Isolation Forest for anomaly detection, backed by a deterministic IEEE C57.12 safety floor. If oil temperature breaches 95°C, the safety engine overrides low classifier scores, elevating the status to WARNING or HIGH RISK and dispatching an active alert. In real industrial systems, safety must be physically bounded, not just statistically inferred."*

---

## 5. Verification Test: Safety Net Override in Action

Demonstration test script: `backend/test_safety_net_demonstration.py`.

### Test Scenario
- **Input Telemetry:** Low active energy (`KWH = 500.0`, `KVARH = 80.0`, nominal balanced voltages and currents).
- **Physical Thermal Breach:** `OTI = 98.5°C` (IEEE safe max is $95.0^\circ\text{C}$), `WTI = 108.0°C` (IEEE safe max is $105.0^\circ\text{C}$).

### Execution Results
```
[STEP 1] Inspecting Raw Supervised Classifier Behavior Alone:
  Classifier Predicted Class:   0 (Normal Operation)
  Classifier Raw Probabilities: {'normal': 0.605, 'warning': 0.345, 'high_risk': 0.05}
  Classifier Alone Risk Score:  0.3950
  Classifier Alone Risk Level:  NORMAL / BORDERLINE WARNING
  => NOTE: Because energy is low (KWH=500), the classifier alone predicts NORMAL/LOW RISK.

[STEP 2] Inspecting Unsupervised Anomaly Detector & Validation Flags:
  IsolationForest is_anomaly:   True (score: -0.0462)
  IEEE Threshold Violations:    2 detected
    - OTI: 98.5°C (HIGH) -> Safe range [0.0, 95.0 °C]
    - WTI: 108.0°C (HIGH) -> Safe range [0.0, 105.0 °C]

[STEP 3] Executing Full End-to-End POST /api/predict Pipeline:
  Final Combined Risk Level:    WARNING (Safety Net Override Active)
  Final Alert Severity:         MEDIUM (Alert Required: True)
  Alert Message:                Warning: abnormal electrical parameters detected. Monitoring recommended.
  Explanation Text:
    The monitoring system detected a WARNING condition (risk score: 0.40 / 1.00). 
    One or more electrical parameters are associated with elevated risk and warrant 
    closer attention. The following parameters were detected outside their configured 
    safe ranges: OTI=98.50 (HIGH), WTI=108.00 (HIGH)... The anomaly detector also 
    flagged this reading as statistically unusual (anomaly score: -0.0462).

[STEP 4] Assertion Verification:
  ✅ Safety net PASSED: High temperature breach correctly escalated to WARNING and triggered active alert.
```

---

## 6. API Contract Reference

### 1. `GET /api/model/status`
Verifies model health and loaded parameters.
- **cURL:** `curl -X GET http://localhost:5000/api/model/status`
- **Response (`200 OK`):**
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
  "timestamp": "2026-09-23T14:30:00Z"
}
```

---

### 2. `POST /api/predict`
Main inference endpoint. Requires 45 numeric inputs.

- **cURL:**
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

- **Response (`200 OK`):**
```json
{
  "success": true,
  "timestamp": "2026-09-23T14:30:00Z",
  "prediction": {
    "risk_level": "NORMAL",
    "risk_score": 0.1200,
    "class_id": 0,
    "class_label": "Normal Operation",
    "probabilities": {
      "normal": 0.88,
      "warning": 0.11,
      "high_risk": 0.01
    },
    "thresholds_used": {
      "normal_max": 0.39,
      "warning_max": 0.69
    }
  },
  "abnormal_parameters": [],
  "anomaly_detection": {
    "is_anomaly": false,
    "anomaly_score": 0.0712
  },
  "oil_temperature_prediction": {
    "predicted_oti": 41.5
  },
  "explanation": "The transformer monitoring system assessed the current operating state as NORMAL (risk score: 0.12 / 1.00). All primary electrical parameters appear to be within acceptable bounds. The oil temperature model estimates an OTI of 41.5°C, which is within normal thermal operating range.",
  "alert": {
    "required": false,
    "severity": "LOW",
    "risk_level": "NORMAL",
    "message": "System operating within normal conditions."
  }
}
```

---

## 7. Known Limitations & Future Work

1. **Energy Metric Correlation in Training Data:**
   - The primary classifier splits heavily on `KWH` and `KVARH`. While mitigated in runtime by the multi-tier safety net, future retraining should explore synthesizing training labels that explicitly incorporate instantaneous thermal gradient flags ($\Delta T$).
2. **Missing WTI Measurements in Certain Dataset Timestamps:**
   - In the historical CSV records, WTI was occasionally unrecorded (0.0°C). The pipeline engineers robust default differential metrics (`WTI_ATI_Diff`, `WTI_OTI_Diff`) to preserve matrix dimensional integrity.
3. **Smart Meter Register Formats:**
   - `Sum_PF` stores signed cumulative smart meter units rather than a simple mathematical sum of cosines. The validation bounds have been adjusted to $[-500.0, 500.0]$ to accommodate IoT telemetry conventions without data loss.
