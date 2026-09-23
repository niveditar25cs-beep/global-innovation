"""
validation.py — Server-side input validation for the prediction API
Smart City Transformer Monitoring — Backend Member 2 (ML Integration)

Validates all incoming request fields before they reach the model.
Returns structured error messages; never exposes internal details.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def validate_input(data: dict) -> dict:
    """
    Validate an incoming prediction request payload.

    Checks:
      1. Request body is a non-empty dict
      2. All required fields are present
      3. All field values are numeric (int or float, no NaN/Inf)
      4. Optional: fields within physically plausible hard bounds
         (not the configurable SAFE_RANGES — those are for flagging, not rejection)

    Args:
        data: dict from request JSON body

    Returns:
        {"valid": True}  on success
        {"valid": False, "errors": [str, ...]}  on failure
    """
    from config import REQUIRED_API_FIELDS

    errors = []

    # ── Guard: must be a non-empty dict ───────────────────────────────────────
    if not isinstance(data, dict) or not data:
        return {
            "valid":  False,
            "errors": ["Request body is missing or not a valid JSON object."],
        }

    # ── Required field presence ────────────────────────────────────────────────
    missing = [f for f in REQUIRED_API_FIELDS if f not in data]
    if missing:
        errors.append(f"Missing required field(s): {', '.join(missing)}")

    # ── Type and value checks ──────────────────────────────────────────────────
    # Hard physical plausibility bounds (rejection, not flagging)
    # These are deliberately wide — the SAFE_RANGES in config.py handle flagging.
    HARD_BOUNDS = {
        "OTI":    (-30.0, 300.0),
        "WTI":    (-30.0, 300.0),
        "ATI":    (-50.0, 100.0),
        "OLI":    (0.0,   100.0),
        "VL1":    (0.0,  1000.0),
        "VL2":    (0.0,  1000.0),
        "VL3":    (0.0,  1000.0),
        "IL1":    (0.0,  5000.0),
        "IL2":    (0.0,  5000.0),
        "IL3":    (0.0,  5000.0),
        "FRQ":    (30.0,   70.0),
        "Avg_PF": (-1.0,    1.0),
        "Sum_PF": (-500.0,  500.0),
    }

    import math

    for field, value in data.items():
        # Skip fields not in our required list (allow extra fields silently)
        if field not in REQUIRED_API_FIELDS:
            continue

        # Numeric type check
        if not isinstance(value, (int, float)):
            val_str = repr(value)[:40]
            errors.append(
                f"'{field}' must be a numeric value, got {type(value).__name__!r} "
                f"(value: {val_str})"
            )
            continue

        # NaN / Infinity check
        if math.isnan(value):
            errors.append(f"'{field}' contains NaN (not a number).")
            continue
        if math.isinf(value):
            errors.append(f"'{field}' contains an infinite value.")
            continue

        # Hard physical plausibility check
        if field in HARD_BOUNDS:
            lo, hi = HARD_BOUNDS[field]
            if not (lo <= value <= hi):
                errors.append(
                    f"'{field}' value {value} is outside physically plausible range "
                    f"[{lo}, {hi}]."
                )

    if errors:
        logger.warning("Input validation failed: %s", errors)
        return {"valid": False, "errors": errors}

    return {"valid": True}


def detect_abnormal_parameters(feat: dict) -> list[dict]:
    """
    Compare all feature values against configured SAFE_RANGES.
    Returns a list of parameters that fall outside their safe range.

    Args:
        feat: engineered feature dict (output of preprocessing.engineer_features())

    Returns:
        List of dicts:
          {"parameter": str, "value": float, "status": "HIGH"|"LOW",
           "safe_min": float, "safe_max": float, "unit": str, "message": str}
    """
    from config import SAFE_RANGES

    flagged = []
    for param, bounds in SAFE_RANGES.items():
        val = feat.get(param)
        if val is None:
            continue
        try:
            val = float(val)
        except (TypeError, ValueError):
            continue

        lo, hi = bounds["min"], bounds["max"]
        unit   = bounds.get("unit", "")
        desc   = bounds.get("desc", param)

        if val > hi:
            flagged.append({
                "parameter": param,
                "value":     round(val, 4),
                "status":    "HIGH",
                "safe_min":  lo,
                "safe_max":  hi,
                "unit":      unit,
                "message":   f"{desc} ({val:.2f}{unit}) exceeds the configured safe maximum of {hi}{unit}.",
            })
        elif val < lo:
            flagged.append({
                "parameter": param,
                "value":     round(val, 4),
                "status":    "LOW",
                "safe_min":  lo,
                "safe_max":  hi,
                "unit":      unit,
                "message":   f"{desc} ({val:.2f}{unit}) is below the configured safe minimum of {lo}{unit}.",
            })

    return flagged
