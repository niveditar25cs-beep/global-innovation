# Distributed Transformer Predictive Maintenance - AI/ML System

An end-to-end Machine Learning solution for **Distributed Transformer Monitoring** using IoT sensor telemetry data. This system provides real-time predictive maintenance, fault risk classification, oil temperature forecasting, and anomaly detection through an interactive web dashboard and REST API.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![scikit-learn](https://img.shields.io/badge/scikit--learn-1.9-orange)
![FastAPI](https://img.shields.io/badge/FastAPI-0.141-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Features

### Machine Learning Models
| Model | Type | Algorithm | Key Metric |
|-------|------|-----------|------------|
| **Fault Risk Classifier** | Multi-class Classification | Random Forest (200 trees) | F1 Macro: **0.9925** |
| **Oil Temperature Forecaster** | Regression | Random Forest | R2: **0.8361** |
| **Grid Anomaly Detector** | Unsupervised | Isolation Forest | 5% contamination |

### Web Dashboard & API
- **Interactive Prediction Form**: Enter sensor readings for real-time risk assessment
- **Batch CSV Upload**: Upload CSV files for bulk transformer health analysis
- **Model Performance Dashboard**: Confusion matrix, regression plots, metrics comparison
- **REST API**: Full Swagger/OpenAPI documentation at `/docs`

---

## Dataset

**Distributed Transformer Monitoring** - IoT telemetry collected every 15 minutes from June 2019 to April 2020.

| File | Description |
|------|-------------|
| `Alarm.csv` | Oil/Winding/Ambient temperature indicators, oil level, alarm triggers |
| `CurrentVoltage.csv` | Phase voltages (VL1-VL3), currents (IL1-IL3), neutral current |
| `Power.csv` | Active, apparent, and reactive power per phase |
| `PowerFactor.csv` | Power factor, frequency, harmonic distortion (THD) |
| `TotalPower.csv` | Total energy consumption (KWH, KW, KVA, KVAR) |

---

## Project Structure

```
.
|-- app.py                  # FastAPI web application & API server
|-- src/
|   |-- data_loader.py      # Data merging, cleaning, feature engineering
|   |-- train.py            # Multi-model training, evaluation, serialization
|   |-- predict.py          # Inference engine (single & batch)
|-- models/
|   |-- transformer_alarm_model.joblib
|   |-- transformer_temp_model.joblib
|   |-- anomaly_detector.joblib
|   |-- cls_scaler.joblib
|   |-- reg_scaler.joblib
|   |-- metadata.json
|-- templates/
|   |-- index.html           # Dashboard UI
|-- static/
|   |-- style.css            # Glassmorphic dark theme
|   |-- app.js               # Frontend logic
|-- reports/
|   |-- classification_confusion_matrix.png
|   |-- regression_actual_vs_pred.png
|   |-- classification_report.txt
|   |-- evaluation_summary.json
|-- data/                    # Raw IoT CSV files
|-- requirements.txt
|-- README.md
```

---

## Quick Start

### 1. Install Dependencies
```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

### 2. Train Models (Optional - pre-trained models included)
```bash
.venv\Scripts\python src\train.py
```

### 3. Launch Web Dashboard
```bash
.venv\Scripts\python app.py
```

Open your browser to **http://localhost:8000**

### 4. API Documentation
Visit **http://localhost:8000/docs** for interactive Swagger API docs.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Dashboard UI |
| `GET` | `/api/health` | System health check |
| `GET` | `/api/metadata` | Model training metadata |
| `POST` | `/api/predict/alarm` | Single reading prediction |
| `POST` | `/api/predict/temperature` | Temperature-only prediction |
| `POST` | `/api/predict/batch` | Batch CSV prediction |

---

## Model Performance

### Classification (Fault Risk Level)
```
                precision    recall  f1-score   support
      Normal       1.00      1.00      1.00      6064
     Warning       0.99      0.99      0.99        82
    Critical       0.98      0.98      0.98       109
```

### Regression (Oil Temperature)
- **RMSE**: 4.31 C
- **MAE**: 0.72 C
- **R2 Score**: 0.8361

---

## Engineered Features

The pipeline creates 15+ domain-engineered features including:
- **Voltage & Current Imbalance (%)**: Detects asymmetric phase loading
- **Total Power Metrics**: Sum of per-phase active, apparent, reactive power
- **Average THD**: Mean total harmonic distortion across voltage and current lines
- **Thermal Gradients**: Temperature differences (OTI-ATI, WTI-ATI, WTI-OTI)
- **Temporal Features**: Hour, day of week, month for pattern detection

---

## Technologies Used

- **Python 3.12** - Core language
- **scikit-learn** - ML model training and evaluation
- **pandas / NumPy** - Data processing and feature engineering
- **FastAPI** - Web framework and REST API
- **Jinja2** - Server-side HTML templating
- **matplotlib / seaborn** - Evaluation visualizations
- **joblib** - Model serialization

---

## License

MIT License
