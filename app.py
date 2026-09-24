import os
import sys
import json
import io
import pandas as pd
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Ensure src is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from predict import TransformerPredictor
from src.db import get_latest_reading, get_historical_readings

app = FastAPI(
    title="TransformerAI - Predictive Maintenance API",
    description="AI-powered fault risk classification and oil temperature forecasting for distributed transformer monitoring.",
    version="1.0.0"
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/reports", StaticFiles(directory="reports"), name="reports")
templates = Jinja2Templates(directory="templates")

# Load predictor once at startup
predictor = TransformerPredictor(models_dir="./models")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main dashboard."""
    return templates.TemplateResponse(request, "index.html")


@app.get("/api/health")
async def health():
    """Health check endpoint with model info."""
    return {
        "status": "healthy",
        "classification_model": predictor.metadata.get("best_classification_model", "N/A"),
        "regression_model": predictor.metadata.get("best_regression_model", "N/A"),
        "records_trained_on": predictor.metadata.get("records", 0),
    }
@app.get("/api/transformer/latest")
async def latest_transformer_reading():
    """
    Get the latest transformer reading from PostgreSQL
    and run it through the ML prediction engine.
    """
    reading = get_latest_reading()

    if reading is None:
        return {
            "status": "no_data",
            "message": "No transformer readings found"
        }

    prediction = predictor.predict_single(reading)

    return {
        "status": "success",
        "transformer_id": "ML-TRANSFORMER-01",
        "reading": reading,
        "risk": prediction
    }
@app.get("/api/transformer/history")
async def transformer_history(limit: int = 50):
    readings = get_historical_readings(limit)

    return {
        "status": "success",
        "transformer_id": "ML-TRANSFORMER-01",
        "count": len(readings),
        "readings": readings
    }
@app.get("/api/metadata")
async def metadata():
    """Return full model training metadata."""
    return predictor.metadata


@app.post("/api/predict/alarm")
async def predict_alarm(request: Request):
    """
    Predict fault risk level and oil temperature from a single sensor reading.
    Expects JSON body with sensor feature values.
    """
    payload = await request.json()
    result = predictor.predict_single(payload)
    return result


@app.post("/api/predict/temperature")
async def predict_temperature(request: Request):
    """
    Alias endpoint focused on temperature prediction.
    """
    payload = await request.json()
    result = predictor.predict_single(payload)
    return {
        "predicted_oil_temperature_celsius": result["predicted_oil_temperature_celsius"],
        "safety_status": result["safety_status"],
    }


@app.post("/api/predict/batch")
async def predict_batch(file: UploadFile = File(...)):
    """
    Upload a CSV and get batch predictions for all rows.
    Returns summary statistics and a preview of predictions.
    """
    contents = await file.read()
    df = pd.read_csv(io.BytesIO(contents))
    result_df = predictor.predict_batch(df)

    risk_dist = result_df['Predicted_Fault_Risk'].value_counts().to_dict()
    risk_dist = {str(k): int(v) for k, v in risk_dist.items()}

    # Return first 20 rows as preview
    preview_cols = ['DeviceTimeStamp', 'Predicted_Fault_Risk', 'Risk_Status', 'Predicted_OTI_Temp_C']
    available_cols = [c for c in preview_cols if c in result_df.columns]
    if not available_cols:
        available_cols = result_df.columns.tolist()[-5:]

    preview = result_df[available_cols].head(20).to_dict(orient='records')

    return JSONResponse({
        "total_rows": len(result_df),
        "risk_distribution": risk_dist,
        "preview": preview,
    })


if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 60)
    print("  TransformerAI - Predictive Maintenance Dashboard")
    print("  URL: http://localhost:8000")
    print("  API Docs: http://localhost:8000/docs")
    print("=" * 60 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
