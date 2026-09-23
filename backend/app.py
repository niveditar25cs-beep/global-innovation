"""
app.py — Flask application entry point
Smart City Transformer Monitoring — Backend Member 2 (ML Integration)

Startup sequence:
  1. Configure logging
  2. Load all ML models
  3. Register API blueprints
  4. Configure CORS
  5. Start Flask dev server (or expose `app` for production WSGI)

Usage:
    python app.py
  or (production):
    gunicorn backend.app:app
"""

import logging
import os
import sys
import warnings

# Suppress sklearn InconsistentVersionWarning (models trained with 1.9.1, deployed on 1.5.2)
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

# ─── Logging configuration ────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Ensure backend/ is on sys.path so absolute imports work from any working directory
_backend_dir = os.path.dirname(os.path.abspath(__file__))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

# ─── Flask app ────────────────────────────────────────────────────────────────
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)

# ─── CORS configuration ───────────────────────────────────────────────────────
from config import CORS_ORIGINS, HOST, PORT, DEBUG as _DEBUG
CORS(app, resources={
    r"/api/*": {
        "origins":  CORS_ORIGINS,
        "methods":  ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
    }
})
logger.info("CORS enabled for origins: %s", CORS_ORIGINS)

# ─── Register blueprints ──────────────────────────────────────────────────────
from routes.prediction_routes import prediction_bp
app.register_blueprint(prediction_bp)
logger.info("Registered blueprint: %s", prediction_bp.name)

# ─── Frontend directory ───────────────────────────────────────────────────────
_frontend_dir = os.path.join(os.path.dirname(_backend_dir), "frontend")

# ─── Root health check & Dashboard routes ─────────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "service":  "Smart City Transformer Monitoring — ML Risk Engine",
        "status":   "running",
        "endpoints": [
            "POST /api/predict",
            "GET  /api/model/status",
            "GET  /dashboard",
        ],
    }), 200


@app.route("/dashboard", methods=["GET"])
def dashboard():
    """Serve the interactive web monitoring dashboard."""
    if os.path.exists(os.path.join(_frontend_dir, "index.html")):
        return send_from_directory(_frontend_dir, "index.html")
    return jsonify({"error": "Dashboard UI not found."}), 404


# ─── Global error handlers ────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found.", "status": 404}), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method not allowed.", "status": 405}), 405


@app.errorhandler(500)
def internal_error(e):
    logger.error("Unhandled 500 error: %s", e)
    return jsonify({"error": "Internal server error.", "status": 500}), 500


# ─── Model loading at startup ─────────────────────────────────────────────────
def startup():
    """Load all ML models. Called once before serving requests."""
    logger.info("=" * 60)
    logger.info("  Smart City Transformer ML Risk Engine — Starting Up")
    logger.info("=" * 60)

    from ml.predictor import load_models
    success = load_models()

    if success:
        logger.info("🚀 Backend ready — listening on http://%s:%d", HOST, PORT)
    else:
        logger.error(
            "⚠️  One or more CRITICAL models failed to load. "
            "The /api/predict endpoint will return 503 until resolved."
        )


# ─── Entry point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    startup()
    app.run(host=HOST, port=PORT, debug=_DEBUG)
