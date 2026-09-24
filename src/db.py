import os

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:Nivedita11*@localhost:5432/transformer_monitoring"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)


# Database column name → ML model feature name
DB_TO_ML_COLUMNS = {
    "oti": "OTI",
    "wti": "WTI",
    "ati": "ATI",
    "oli": "OLI",
    "oti_a": "OTI_A",
    "oti_t": "OTI_T",
    "mog_a": "MOG_A",

    "vl1": "VL1",
    "vl2": "VL2",
    "vl3": "VL3",
    "il1": "IL1",
    "il2": "IL2",
    "il3": "IL3",
    "vl12": "VL12",
    "vl23": "VL23",
    "vl31": "VL31",
    "inut": "INUT",

    "wl1": "WL1",
    "wl2": "WL2",
    "wl3": "WL3",
    "val1": "VAL1",
    "val2": "VAL2",
    "val3": "VAL3",
    "rval1": "RVAL1",
    "rval2": "RVAL2",
    "rval3": "RVAL3",

    "pfl1": "PFL1",
    "pfl2": "PFL2",
    "pfl3": "PFL3",
    "avg_pf": "Avg_PF",
    "sum_pf": "Sum_PF",
    "frq": "FRQ",
    "thdvl1": "THDVL1",
    "thdvl2": "THDVL2",
    "thdvl3": "THDVL3",
    "thdil1": "THDIL1",
    "thdil2": "THDIL2",
    "thdil3": "THDIL3",
    "mdil1": "MDIL1",
    "mdil2": "MDIL2",
    "mdil3": "MDIL3",

    "kwh": "KWH",
    "kwh_i": "KWH_I",
    "kvarh": "KVARH",
    "kw": "KW",
    "kva": "KVA",
    "kvar": "KVAR",
    "mpd": "MPD",
    "mkvad": "MKVAD",
}


def get_latest_reading():
    query = text("""
        SELECT *
        FROM transformer_readings
        ORDER BY device_timestamp DESC
        LIMIT 1
    """)

    with engine.connect() as connection:
        row = connection.execute(query).mappings().first()

    if not row:
        return None

    db_reading = dict(row)

    # Convert database column names to the names
    # expected by the trained ML model.
    ml_reading = {}

    for db_column, value in db_reading.items():
        if db_column in DB_TO_ML_COLUMNS:
            ml_column = DB_TO_ML_COLUMNS[db_column]
            ml_reading[ml_column] = value

    # Timestamp is needed by the ML feature engineering
    # to calculate Hour, DayOfWeek and Month.
    ml_reading["DeviceTimeStamp"] = db_reading["device_timestamp"]

    return ml_reading
def get_historical_readings(limit=50):
    query = text("""
        SELECT *
        FROM transformer_readings
        ORDER BY device_timestamp DESC
        LIMIT :limit
    """)

    with engine.connect() as connection:
        rows = connection.execute(
            query,
            {"limit": limit}
        ).mappings().all()

    historical_readings = []

    for row in rows:
        db_reading = dict(row)
        ml_reading = {}

        for db_column, value in db_reading.items():
            if db_column in DB_TO_ML_COLUMNS:
                ml_column = DB_TO_ML_COLUMNS[db_column]
                ml_reading[ml_column] = value

        ml_reading["DeviceTimeStamp"] = db_reading["device_timestamp"]

        historical_readings.append(ml_reading)

    return historical_readings