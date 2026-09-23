import io
import logging
import re
from datetime import datetime
from typing import Any, cast

import pandas as pd

logger = logging.getLogger(__name__)

# Canonical column definitions and known aliases
COLUMN_ALIASES: dict[str, list[str]] = {
    "transformer_id": [
        "transformer_id",
        "transformer",
        "device_id",
        "tr_id",
        "id",
        "transformerid",
    ],
    "timestamp": ["timestamp", "datetime", "time", "date_time", "reading_time", "ts"],
    "voltage_kv": [
        "voltage_kv",
        "voltage",
        "v_kv",
        "volts_kv",
        "voltage_rating",
        "voltagekv",
    ],
    "current_a": ["current_a", "current", "amps", "i_a", "current_amp", "currenta"],
    "oil_temperature_c": [
        "oil_temperature_c",
        "oil_temp",
        "oil_temperature",
        "oil_temp_c",
        "oiltemperaturec",
    ],
    "winding_temperature_c": [
        "winding_temperature_c",
        "winding_temp",
        "winding_temperature",
        "winding_temp_c",
        "windingtemperaturec",
    ],
    "oil_level_pct": ["oil_level_pct", "oil_level", "oil_pct", "level_pct", "oillevelpct"],
    "vibration_mm_s": ["vibration_mm_s", "vibration", "vib_mm_s", "vib", "vibrationmms"],
    "load_percentage": [
        "load_percentage",
        "load_pct",
        "load",
        "loading_pct",
        "load_percent",
        "loadpercentage",
    ],
    "ambient_temperature_c": [
        "ambient_temperature_c",
        "ambient_temp",
        "ambient_temperature",
        "amb_temp_c",
        "ambienttemperaturec",
    ],
    "humidity_pct": [
        "humidity_pct",
        "humidity",
        "rel_humidity",
        "humidity_percent",
        "humiditypct",
    ],
    "dissolved_gas_ppm": [
        "dissolved_gas_ppm",
        "dissolved_gas",
        "dga_ppm",
        "dga",
        "gas_ppm",
        "dissolvedgasppm",
    ],
}

# Unit cleaning regular expression (matches trailing units like 'kV', 'A', '°C', 'mm/s', '%')
UNIT_PATTERN = re.compile(
    r"([0-9\.\-]+)\s*(?:kv|volts?|amps?|a|°c|degc|c|mm/s|ppm|%|\b)*",
    re.IGNORECASE,
)


def clean_numeric_value(val: Any) -> float | None:
    """
    Safely parse and clean a numeric sensor reading.
    Strips out common unit suffixes, percent signs, commas, and whitespace.
    Returns float or None if unparseable.
    """
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (int, float)):
        return float(val)

    s = str(val).strip().replace(",", "")
    if s == "" or s.lower() in ["na", "n/a", "null", "none", "nan", "err", "error", "?", "-"]:
        return None

    # Try standard float conversion first
    try:
        return float(s)
    except ValueError:
        pass

    # Extract leading numeric component using regex
    match = UNIT_PATTERN.match(s)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass

    return None


def clean_timestamp(val: Any, default_time: datetime | None = None) -> datetime:
    """Parse timestamp safely with graceful fallback."""
    if val is None or pd.isna(val):
        return default_time or datetime.utcnow()
    if isinstance(val, datetime):
        return val
    try:
        dt = pd.to_datetime(val)
        if pd.isna(dt):
            return default_time or datetime.utcnow()
        return cast(datetime, dt.to_pydatetime())
    except Exception:
        return default_time or datetime.utcnow()


def normalize_column_mapping(columns: list[str]) -> dict[str, str]:
    """
    Map raw column names to canonical internal names.
    Preserves unmatched columns with their original sanitized names.
    """
    mapping = {}
    found_cols = [str(c).strip().lower().replace(" ", "_") for c in columns]

    for orig_col, sanitized in zip(columns, found_cols, strict=False):
        matched_canonical = None
        for canonical, aliases in COLUMN_ALIASES.items():
            if sanitized in aliases:
                matched_canonical = canonical
                break
        if matched_canonical:
            mapping[orig_col] = matched_canonical
        else:
            mapping[orig_col] = sanitized

    return mapping


class DatasetParseResult:
    """Encapsulates the complete result of parsing and validating a dataset."""

    def __init__(self):
        self.valid_records: list[dict[str, Any]] = []
        self.invalid_records: list[dict[str, Any]] = []
        self.warnings: list[str] = []
        self.total_raw_rows: int = 0
        self.available_fields: list[str] = []
        self.transformer_ids: list[str] = []
        self.imputed_fields_count: int = 0


def parse_and_validate_dataset(
    file_bytes_or_path: Any, filename: str = "dataset.csv"
) -> DatasetParseResult:
    """
    Reliably load, parse, and validate transformer dataset.

    Guarantees:
    - Never crashes the server on malformed, corrupted, or missing records.
    - Preserves Transformer IDs as exact cleaned strings.
    - Parses numerical values (voltage, current, temperature, etc.) handling units safely.
    - Captures invalid rows in an audit trail rather than failing the whole load.
    - Returns a structured DatasetParseResult.
    """
    result = DatasetParseResult()

    # Step 1: Read raw CSV with multi-encoding fallback
    df = None
    encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
    last_err = None

    for enc in encodings:
        try:
            if isinstance(file_bytes_or_path, (bytes, bytearray)):
                df = pd.read_csv(io.BytesIO(file_bytes_or_path), encoding=enc, on_bad_lines="skip")
            elif hasattr(file_bytes_or_path, "read"):
                content = file_bytes_or_path.read()
                if isinstance(content, str):
                    df = pd.read_csv(io.StringIO(content), on_bad_lines="skip")
                else:
                    df = pd.read_csv(io.BytesIO(content), encoding=enc, on_bad_lines="skip")
            else:
                df = pd.read_csv(file_bytes_or_path, encoding=enc, on_bad_lines="skip")
            break
        except Exception as e:
            last_err = e

    if df is None or df.empty:
        if last_err:
            result.warnings.append(f"Could not parse CSV file: {last_err!s}")
        else:
            result.warnings.append("Dataset file is empty.")
        return result

    result.total_raw_rows = len(df)

    # Step 2: Map and normalize columns
    col_mapping = normalize_column_mapping(list(df.columns))
    df = df.rename(columns=col_mapping)
    result.available_fields = list(df.columns)

    # Verify transformer_id column exists
    if "transformer_id" not in df.columns:
        result.warnings.append(
            f"Missing 'transformer_id' column in dataset. Found columns: {list(df.columns)}"
        )
        return result

    # Step 3: Row-by-row safe record extraction
    default_base_time = datetime.utcnow()

    for idx, row in df.iterrows():
        row_num = idx + 2  # 1-indexed including header row

        # Validate transformer ID
        raw_tr_id = row.get("transformer_id")
        if raw_tr_id is None or pd.isna(raw_tr_id) or str(raw_tr_id).strip() == "":
            result.invalid_records.append(
                {
                    "row_number": row_num,
                    "reason": "Missing or blank transformer_id",
                    "raw_values": row.to_dict(),
                }
            )
            continue

        transformer_id = str(raw_tr_id).strip()

        # Parse timestamp safely
        raw_ts = row.get("timestamp")
        timestamp = clean_timestamp(raw_ts, default_base_time)

        # Parse critical electrical & thermal numerical parameters
        v_raw = row.get("voltage_kv")
        c_raw = row.get("current_a")
        t_raw = row.get("oil_temperature_c")

        voltage_kv = clean_numeric_value(v_raw)
        current_a = clean_numeric_value(c_raw)
        oil_temperature_c = clean_numeric_value(t_raw)

        # If any essential numerical values are completely invalid, quarantine the record
        if voltage_kv is None or current_a is None or oil_temperature_c is None:
            reasons = []
            if voltage_kv is None:
                reasons.append(f"Invalid voltage ('{v_raw}')")
            if current_a is None:
                reasons.append(f"Invalid current ('{c_raw}')")
            if oil_temperature_c is None:
                reasons.append(f"Invalid oil temperature ('{t_raw}')")

            result.invalid_records.append(
                {
                    "row_number": row_num,
                    "transformer_id": transformer_id,
                    "reason": "; ".join(reasons),
                    "raw_values": row.to_dict(),
                }
            )
            continue

        # Parse secondary numerical parameters with safe fallback defaults
        winding_temperature_c = clean_numeric_value(row.get("winding_temperature_c"))
        if winding_temperature_c is None:
            winding_temperature_c = round(oil_temperature_c + 8.0, 2)
            result.imputed_fields_count += 1

        load_percentage = clean_numeric_value(row.get("load_percentage"))
        if load_percentage is None:
            load_percentage = 50.0
            result.imputed_fields_count += 1

        oil_level_pct = clean_numeric_value(row.get("oil_level_pct"))
        if oil_level_pct is None:
            oil_level_pct = 85.0
            result.imputed_fields_count += 1

        vibration_mm_s = clean_numeric_value(row.get("vibration_mm_s"))
        if vibration_mm_s is None:
            vibration_mm_s = 1.2
            result.imputed_fields_count += 1

        dissolved_gas_ppm = clean_numeric_value(row.get("dissolved_gas_ppm"))
        if dissolved_gas_ppm is None:
            dissolved_gas_ppm = 35.0
            result.imputed_fields_count += 1

        ambient_temperature_c = clean_numeric_value(row.get("ambient_temperature_c"))
        if ambient_temperature_c is None:
            ambient_temperature_c = 25.0
            result.imputed_fields_count += 1

        humidity_pct = clean_numeric_value(row.get("humidity_pct"))
        if humidity_pct is None:
            humidity_pct = 60.0
            result.imputed_fields_count += 1

        # Assemble clean, strongly-typed record dictionary
        record = {
            "transformer_id": transformer_id,
            "timestamp": timestamp,
            "voltage_kv": float(voltage_kv),
            "current_a": float(current_a),
            "oil_temperature_c": float(oil_temperature_c),
            "winding_temperature_c": float(winding_temperature_c),
            "load_percentage": float(load_percentage),
            "oil_level_pct": float(oil_level_pct),
            "vibration_mm_s": float(vibration_mm_s),
            "dissolved_gas_ppm": float(dissolved_gas_ppm),
            "ambient_temperature_c": float(ambient_temperature_c),
            "humidity_pct": float(humidity_pct),
        }
        result.valid_records.append(record)

    # Sort valid records by transformer_id, then timestamp
    result.valid_records.sort(key=lambda r: (r["transformer_id"], r["timestamp"]))
    result.transformer_ids = sorted({r["transformer_id"] for r in result.valid_records})

    if result.invalid_records:
        result.warnings.append(
            f"Handled {len(result.invalid_records)} invalid/malformed records "
            f"out of {result.total_raw_rows} total rows."
        )

    return result


# Compatibility aliases
parse_and_validate_csv = parse_and_validate_dataset
normalize_column_names = normalize_column_mapping
