from flask import Flask, request, jsonify
import joblib
import pandas as pd
import os

# Create Flask application
app = Flask(__name__)

# Load trained ML model
model_path = "logistic_regression_alarm_model.joblib"

try:
    model = joblib.load(model_path)
    print("Model loaded successfully!")

except Exception as e:
    print(f"Error loading model: {e}")
    model = None


# Home route
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Suraksha AI Alarm Detection API is running",
        "status": "success"
    })


# Health check
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy"
    })


# Prediction API
@app.route("/predict", methods=["POST"])
def predict():

    # Check JSON input
    if not request.is_json:
        return jsonify({
            "error": "Invalid input. Expected JSON."
        }), 400

    data = request.get_json()

    # Required ML features
    required_features = [
        "OTI",
        "WTI",
        "ATI",
        "OLI"
    ]

    # Check missing features
    missing_features = [
        feature
        for feature in required_features
        if feature not in data
    ]

    if missing_features:
        return jsonify({
            "error": "Missing required features",
            "missing": missing_features,
            "expected": required_features
        }), 400

    # Check model
    if model is None:
        return jsonify({
            "error": "Model is not loaded."
        }), 500

    try:

        # Create DataFrame
        input_df = pd.DataFrame([{
            "OTI": float(data["OTI"]),
            "WTI": float(data["WTI"]),
            "ATI": float(data["ATI"]),
            "OLI": float(data["OLI"])
        }])

        # Make prediction
        prediction = model.predict(input_df)

        # Get probabilities
        prediction_proba = model.predict_proba(input_df)

        # Alarm status
        if int(prediction[0]) == 1:
            alarm_status = "ALARM"
        else:
            alarm_status = "NO ALARM"

        # Response
        result = {
            "prediction": int(prediction[0]),
            "alarm_status": alarm_status,
            "probability_no_alarm": float(
                prediction_proba[0][0]
            ),
            "probability_alarm": float(
                prediction_proba[0][1]
            )
        }

        return jsonify(result)

    except ValueError as e:

        return jsonify({
            "error": f"Invalid numeric input: {str(e)}"
        }), 400

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# Local development only
if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
