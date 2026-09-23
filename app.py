from flask import Flask, request, jsonify,Flask
from pyngrok import ngrok
import joblib
import pandas as pd
import os
app = Flask(__name__)

# Set Flask app environment variable
os.environ["FLASK_APP"] = "app.py"

# Create Flask application


# Load the trained model
model_path = "logistic_regression_alarm_model.joblib"

try:
    model = joblib.load(model_path)
    print("Model loaded successfully!")

except Exception as e:
    print(f"Error loading model: {e}")
    model = None


# Prediction API
@app.route("/predict", methods=["POST"])
def predict():

    # Check if request contains JSON
    if not request.is_json:
        return jsonify({
            "error": "Invalid input. Expected JSON."
        }), 400

    # Get JSON data
    data = request.get_json()

    # Required input features
    required_features = ["OTI", "WTI", "ATI", "OLI"]

    # Check for missing features
    missing_features = [
        feature for feature in required_features
        if feature not in data
    ]

    if missing_features:
        return jsonify({
            "error": "Missing required features",
            "missing": missing_features,
            "expected": required_features
        }), 400

    # Check if model is loaded
    if model is None:
        return jsonify({
            "error": "Model is not loaded."
        }), 500

    try:

        # Create DataFrame from input
        input_df = pd.DataFrame([{
            "OTI": float(data["OTI"]),
            "WTI": float(data["WTI"]),
            "ATI": float(data["ATI"]),
            "OLI": float(data["OLI"])
        }])

        # Make prediction
        prediction = model.predict(input_df)

        # Get prediction probabilities
        prediction_proba = model.predict_proba(input_df)

        # Prepare response
        result = {
            "prediction": int(prediction[0]),
            "probability_no_alarm": float(prediction_proba[0][0]),
            "probability_alarm": float(prediction_proba[0][1])
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


# Main program
if __name__ == "__main__":

    # Flask port
    port = 5000

    # Start ngrok tunnel
    try:

        public_url = ngrok.connect(port).public_url

        print("\n====================================")
        print("       SURAKSHA AI API")
        print("====================================")
        print(f"ngrok URL     : {public_url}")
        print(f"Prediction API: {public_url}/predict")
        print(f"Local API     : http://localhost:{port}/predict")
        print("====================================\n")

    except Exception as e:

        print(f"ngrok error: {e}")
        print("Starting Flask without ngrok...")

    # Start Flask server
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False
    )
