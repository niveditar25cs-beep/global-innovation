"""
Schema detection and column mapping for transformer dataset ingestion.
"""

# Canonical column definitions and accepted aliases (lowercased and trimmed)
COLUMN_ALIASES: dict[str, list[str]] = {
    "transformer_id": [
        "transformer_id",
        "transformer",
        "device_id",
        "tr_id",
        "id",
        "transformerid",
        "tx_id",
        "unit_id",
        "station_tx_id",
    ],
    "timestamp": [
        "timestamp",
        "datetime",
        "time",
        "date_time",
        "reading_time",
        "ts",
        "recorded_at",
        "reading_timestamp",
    ],
    "voltage": [
        "voltage",
        "voltage_kv",
        "v_kv",
        "volts_kv",
        "volts",
        "voltage_v",
        "v",
        "voltagekv",
        "voltage_reading",
    ],
    "current": [
        "current",
        "current_a",
        "amps",
        "i_a",
        "current_amp",
        "currenta",
        "i",
        "current_reading",
    ],
    "temperature": [
        "temperature",
        "oil_temperature_c",
        "oil_temp",
        "oil_temperature",
        "temp_c",
        "temp",
        "oil_temp_c",
        "oiltemperaturec",
        "primary_temperature",
    ],
    # Additional recognized telemetry sensor fields
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
    "humidity_pct": ["humidity_pct", "humidity", "rel_humidity", "humidity_percent", "humiditypct"],
    "dissolved_gas_ppm": [
        "dissolved_gas_ppm",
        "dissolved_gas",
        "dga_ppm",
        "dga",
        "gas_ppm",
        "dissolvedgasppm",
    ],
}

# The mandatory fields required for a valid transformer reading
REQUIRED_COLUMNS: set[str] = {
    "transformer_id",
    "timestamp",
    "voltage",
    "current",
    "temperature",
}


class SchemaValidationError(Exception):
    """Raised when a dataset does not meet schema requirements."""

    def __init__(
        self,
        message: str,
        missing_columns: list[str] | None = None,
        detected_columns: list[str] | None = None,
    ):
        super().__init__(message)
        self.missing_columns = missing_columns or []
        self.detected_columns = detected_columns or []


def sanitize_column_name(col: str) -> str:
    """Normalize a column header to lowercase alphanumeric with underscores."""
    s = str(col).strip().lower()
    return s.replace(" ", "_").replace("-", "_").replace(".", "_")


def detect_and_normalize_columns(raw_columns: list[str]) -> tuple[dict[str, str], list[str]]:
    """
    Map raw column names to canonical names and detect any missing required columns.

    Returns:
        col_mapping: Dict mapping original column name -> canonical name
        missing_required: List of required canonical column names not found in dataset
    """
    col_mapping: dict[str, str] = {}
    found_canonicals: set[str] = set()

    for raw_col in raw_columns:
        sanitized = sanitize_column_name(raw_col)
        matched_canonical = None

        for canonical, aliases in COLUMN_ALIASES.items():
            if sanitized in aliases or sanitized == canonical:
                matched_canonical = canonical
                break

        if matched_canonical and matched_canonical not in found_canonicals:
            col_mapping[raw_col] = matched_canonical
            found_canonicals.add(matched_canonical)
        else:
            # Preserve unknown columns with their sanitized name for potential sensor_data inclusion
            col_mapping[raw_col] = sanitized

    missing_required = sorted(REQUIRED_COLUMNS - found_canonicals)
    return col_mapping, missing_required
