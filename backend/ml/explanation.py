"""
explanation.py — Human-readable prediction explanations
Smart City Transformer Monitoring — Backend Member 2 (ML Integration)

Generates non-causal, transparent explanations for every prediction.
Wording uses "associated with", "detected", "contributing factor" —
not "caused by" — since we're interpreting model output, not proving causation.
"""

import logging

logger = logging.getLogger(__name__)


def generate_explanation(
    risk_level: str,
    risk_score: float | None,
    abnormal_parameters: list[dict],
    regression_result: dict | None = None,
    anomaly_result:    dict | None = None,
) -> str:
    """
    Generate a plain-language explanation of the prediction.

    Args:
        risk_level:           "NORMAL" | "WARNING" | "HIGH_RISK"
        risk_score:           float 0–1 from predict_proba, or None
        abnormal_parameters:  list of dicts from detect_abnormal_parameters()
        regression_result:    optional dict with predicted_oti
        anomaly_result:       optional dict with is_anomaly, anomaly_score

    Returns:
        str: A concise human-readable explanation (1–5 sentences)
    """
    from config import CLASS_LABELS

    # ── Base sentence ──────────────────────────────────────────────────────────
    score_str = (
        f" (risk score: {risk_score:.2f} / 1.00)"
        if risk_score is not None else ""
    )

    base_map = {
        "NORMAL":    f"The transformer monitoring system assessed the current operating state as NORMAL{score_str}. "
                     "All primary electrical parameters appear to be within acceptable bounds.",
        "WARNING":   f"The monitoring system detected a WARNING condition{score_str}. "
                     "One or more electrical parameters are associated with elevated risk and warrant closer attention.",
        "HIGH_RISK": f"The monitoring system flagged a HIGH RISK condition{score_str}. "
                     "Multiple electrical parameters are associated with a potentially critical fault state — "
                     "immediate inspection is recommended.",
    }
    explanation = base_map.get(
        risk_level,
        f"Risk level '{risk_level}' was returned by the model{score_str}."
    )

    # ── Abnormal parameter details ─────────────────────────────────────────────
    if abnormal_parameters:
        param_strs = []
        for p in abnormal_parameters[:5]:   # cap at 5 to keep explanation concise
            val = p.get("value", "N/A")
            name = p.get("parameter", "?")
            status = p.get("status", "")
            val_str = f"{val:.2f}" if isinstance(val, float) else str(val)
            param_strs.append(f"{name}={val_str} ({status})")

        joined = ", ".join(param_strs)
        explanation += (
            f" The following parameters were detected outside their configured safe ranges "
            f"and may be contributing factors: {joined}."
        )
        if len(abnormal_parameters) > 5:
            explanation += f" ({len(abnormal_parameters) - 5} additional parameters also flagged.)"

    # ── OTI regression insight ─────────────────────────────────────────────────
    if regression_result and regression_result.get("predicted_oti") is not None:
        oti = regression_result["predicted_oti"]
        if oti > 90:
            explanation += (
                f" The oil temperature model estimates an OTI of {oti:.1f}°C, "
                f"which is associated with elevated thermal stress."
            )
        elif oti > 70:
            explanation += (
                f" The oil temperature model estimates an OTI of {oti:.1f}°C — "
                f"within operating range but elevated."
            )
        else:
            explanation += (
                f" The oil temperature model estimates an OTI of {oti:.1f}°C, "
                f"which is within normal thermal operating range."
            )

    # ── Anomaly detector insight ───────────────────────────────────────────────
    if anomaly_result:
        is_anom = anomaly_result.get("is_anomaly")
        anom_score = anomaly_result.get("anomaly_score")
        if is_anom is True:
            score_detail = (
                f" (anomaly score: {anom_score:.4f})" if anom_score is not None else ""
            )
            explanation += (
                f" The anomaly detector also flagged this reading as statistically "
                f"unusual compared to historical patterns{score_detail}."
            )
        elif is_anom is False and risk_level != "NORMAL":
            explanation += (
                " Note: the anomaly detector did not flag this reading as statistically "
                "anomalous, but the fault classifier indicates elevated risk."
            )

    return explanation.strip()
