"""
Validation and data cleaning routines for dataset ingestion.
"""

import math
import re
from datetime import UTC, datetime
from typing import Any, cast

import pandas as pd

from app.ingestion.models import ProcessedReading, RejectedRecord

# Unit stripping regex (e.g., '132.5 kV', '450.0 A', '75.2 °C', '88 %', '1.58 mm/s')
UNIT_REGEX = re.compile(
    r"^([+\-]?(?:[0-9]*[.])?[0-9]+(?:[eE][+\-]?[0-9]+)?)\s*(?:[a-zA-Z°%/_]+)?$", re.IGNORECASE
)

# Known non-numeric sentinel string values
NON_NUMERIC_SENTINELS = {
    "",
    "na",
    "n/a",
    "nan",
    "null",
    "none",
    "nil",
    "inf",
    "-inf",
    "+inf",
    "undefined",
    "?",
    "-",
    "--",
    "err",
    "error",
    "missing",
}

# Core required column keys
CORE_REQUIRED_FIELDS = ("transformer_id", "timestamp", "voltage", "current", "temperature")


def clean_transformer_id(val: Any) -> str | None:
    """
    Preserve transformer ID as exact trimmed string.
    Returns None if missing, blank, or NaN.
    """
    if val is None or pd.isna(val):
        return None
    s = str(val).strip()
    return s if s else None


def clean_numeric_value(val: Any) -> float | None:
    """
    Safely parse and clean a numeric sensor reading.
    Strips trailing units, ensures value is a finite float.
    Returns None if missing, unparseable, or non-finite.
    """
    if val is None or pd.isna(val):
        return None

    if isinstance(val, (int, float)):
        f_val = float(val)
        return f_val if math.isfinite(f_val) else None

    # Handle string representation
    s = str(val).strip().replace(",", "")
    if s.lower() in NON_NUMERIC_SENTINELS:
        return None

    # Standard float conversion
    try:
        f_val = float(s)
        return f_val if math.isfinite(f_val) else None
    except ValueError:
        pass

    # Regex extraction of leading number from units string
    match = UNIT_REGEX.match(s)
    if match:
        try:
            f_val = float(match.group(1))
            return f_val if math.isfinite(f_val) else None
        except ValueError:
            pass

    return None


def clean_timestamp(val: Any) -> datetime | None:
    """
    Parse a timestamp safely into a timezone-aware UTC datetime.
    Returns None if unparseable or missing.
    """
    if val is None or pd.isna(val):
        return None

    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=UTC)
        return val.astimezone(UTC)

    s = str(val).strip()
    if not s or s.lower() in NON_NUMERIC_SENTINELS:
        return None

    try:
        ts = pd.to_datetime(s)
        if pd.isna(ts):
            return None
        dt = cast(datetime, ts.to_pydatetime())
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except Exception:
        return None


def validate_and_transform_row(
    row: dict[str, Any], row_number: int
) -> tuple[ProcessedReading | None, RejectedRecord | None]:
    """
    Validate a single normalized row.

    Guarantees:
    - Never hardcodes or fabricates core readings.
    - Captures missing or malformed required values as a RejectedRecord.
    - Preserves exact transformer_id string.
    - Places optional sensor telemetry into sensor_data dictionary.
    """
    raw_copy = dict(row)

    # 1. Validate transformer_id
    tr_id = clean_transformer_id(row.get("transformer_id"))
    if not tr_id:
        return None, RejectedRecord(
            row_number=row_number, reason="Missing or empty transformer_id", raw_values=raw_copy
        )

    # 2. Validate timestamp
    raw_ts = row.get("timestamp")
    ts = clean_timestamp(raw_ts)
    if not ts:
        return None, RejectedRecord(
            row_number=row_number,
            reason=f"Missing or invalid timestamp '{raw_ts}'",
            raw_values=raw_copy,
        )

    # 3. Validate core required numerical metrics
    raw_v = row.get("voltage")
    voltage = clean_numeric_value(raw_v)
    if voltage is None:
        return None, RejectedRecord(
            row_number=row_number,
            reason=f"Missing or invalid numerical value for required 'voltage' (raw: '{raw_v}')",
            raw_values=raw_copy,
        )

    raw_c = row.get("current")
    current = clean_numeric_value(raw_c)
    if current is None:
        return None, RejectedRecord(
            row_number=row_number,
            reason=f"Missing or invalid numerical value for required 'current' (raw: '{raw_c}')",
            raw_values=raw_copy,
        )

    raw_t = row.get("temperature")
    temperature = clean_numeric_value(raw_t)
    if temperature is None:
        return None, RejectedRecord(
            row_number=row_number,
            reason=(
                f"Missing or invalid numerical value for required 'temperature' (raw: '{raw_t}')"
            ),
            raw_values=raw_copy,
        )

    # 4. Assemble optional / extensible sensor telemetry into sensor_data dict
    sensor_data: dict[str, Any] = {}
    for k, v in row.items():
        if k in CORE_REQUIRED_FIELDS:
            continue
        # If it's a numeric sensor metric, clean it; otherwise preserve string/structure
        num_val = clean_numeric_value(v)
        if num_val is not None:
            sensor_data[k] = num_val
        elif v is not None and not pd.isna(v) and str(v).strip() != "":
            sensor_data[k] = str(v).strip()

    reading = ProcessedReading(
        transformer_id=tr_id,
        timestamp=ts,
        voltage=voltage,
        current=current,
        temperature=temperature,
        sensor_data=sensor_data,
        original_row_number=row_number,
    )
    return reading, None
