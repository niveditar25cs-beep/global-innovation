import os
import pandas as pd
from sqlalchemy import create_engine, text

# PostgreSQL connection
DATABASE_URL = "postgresql+psycopg2://postgres:Nivedita11*@localhost:5432/transformer_monitoring"

DATA_DIR = "./data"
TRANSFORMER_ID = "ML-TRANSFORMER-01"


def load_and_merge_csvs():
    files = [
        "Alarm.csv",
        "CurrentVoltage.csv",
        "Power.csv",
        "PowerFactor.csv",
        "TotalPower.csv",
    ]

    dataframes = {}

    for filename in files:
        path = os.path.join(DATA_DIR, filename)

        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing file: {path}")

        df = pd.read_csv(path)

        df["DeviceTimeStamp"] = pd.to_datetime(df["DeviceTimeStamp"])
        df.sort_values("DeviceTimeStamp", inplace=True)

        dataframes[filename] = df

        print(f"{filename}: {len(df)} rows")

    merged = dataframes["Alarm.csv"]

    for filename in files[1:]:
        merged = merged.merge(
            dataframes[filename],
            on="DeviceTimeStamp",
            how="inner"
        )

    merged.sort_values("DeviceTimeStamp", inplace=True)
    merged.reset_index(drop=True, inplace=True)

    return merged


def import_data():
    print("=" * 60)
    print("TRANSFORMER CSV → POSTGRESQL IMPORT")
    print("=" * 60)

    df = load_and_merge_csvs()

    print(f"\nMerged records: {len(df)}")
    print(f"Columns: {len(df.columns)}")

    engine = create_engine(DATABASE_URL)

    # Check existing records
    with engine.connect() as conn:
        existing = conn.execute(
            text("SELECT COUNT(*) FROM transformer_readings")
        ).scalar()

    print(f"Existing database records: {existing}")

    inserted = 0
    skipped = 0

    for _, row in df.iterrows():

        values = {
            "transformer_id": TRANSFORMER_ID,
            "device_timestamp": row["DeviceTimeStamp"],
        }

        # Copy all telemetry columns
        for column in df.columns:
            if column == "DeviceTimeStamp":
                continue

            values[column.lower()] = row[column]

        columns = ", ".join(values.keys())
        placeholders = ", ".join(f":{column}" for column in values.keys())

        sql = text(f"""
            INSERT INTO transformer_readings ({columns})
            VALUES ({placeholders})
            ON CONFLICT (transformer_id, device_timestamp)
            DO NOTHING
        """)

        with engine.begin() as conn:
            result = conn.execute(sql, values)

        if result.rowcount == 1:
            inserted += 1
        else:
            skipped += 1

    print("\n" + "=" * 60)
    print("IMPORT COMPLETE")
    print("=" * 60)
    print(f"Total CSV records : {len(df)}")
    print(f"Inserted          : {inserted}")
    print(f"Skipped duplicates: {skipped}")


if __name__ == "__main__":
    import_data()