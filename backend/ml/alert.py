"""
alert.py — Generate structured alert messages based on risk level
Smart City Transformer Monitoring — Backend Member 2 (ML Integration)

Maps NORMAL / WARNING / HIGH_RISK to severity, alert flag, and message.
All alert text is configured in config.py (ALERT_CONFIG).
"""

import logging

logger = logging.getLogger(__name__)


def generate_alert(risk_level: str) -> dict:
    """
    Generate an alert object from a risk level string.

    Args:
        risk_level: "NORMAL" | "WARNING" | "HIGH_RISK"

    Returns:
        {
            "required":  bool,
            "severity":  "LOW" | "MEDIUM" | "HIGH",
            "message":   str,
            "risk_level": str,
        }
    """
    from config import ALERT_CONFIG

    cfg = ALERT_CONFIG.get(risk_level)

    if cfg is None:
        logger.error("Unknown risk_level '%s' passed to generate_alert", risk_level)
        return {
            "required":   True,
            "severity":   "HIGH",
            "message":    f"Unknown risk level '{risk_level}'. Manual inspection required.",
            "risk_level": risk_level,
        }

    if cfg["alert"]:
        logger.warning(
            "ALERT [%s]: %s", cfg["severity"], cfg["message"]
        )

    return {
        "required":   cfg["alert"],
        "severity":   cfg["severity"],
        "message":    cfg["message"],
        "risk_level": risk_level,
    }
