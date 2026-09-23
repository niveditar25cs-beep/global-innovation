"""
Async database verification suite for the Transformer Failure Risk Monitoring System.

Tests:
1. Alembic migration version
2. Table existence
3. Column types and constraints (via information_schema)
4. Indexes
5. Foreign keys & check constraints
6. Async CRUD operations using SQLAlchemy 2.0 AsyncSession
7. Relationship loading
8. Unique & check constraint enforcement
9. Cascade delete behavior
"""
import asyncio
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text, select
from sqlalchemy.orm import selectinload

from app.data_access.database import AsyncSessionLocal, async_engine
from app.models.transformer import Transformer
from app.models.reading import TransformerReading
from app.models.network_connection import NetworkConnection

PASS = "[PASS]"
FAIL = "[FAIL]"

results = []


def report(label: str, passed: bool, detail: str = ""):
    icon = PASS if passed else FAIL
    msg = f"  {icon}  {label}"
    if detail:
        msg += f" -- {detail}"
    print(msg)
    results.append((label, passed))


# ---------------------------------------------------------------------------
# 1. Migration version
# ---------------------------------------------------------------------------
async def verify_migration_version():
    print("\n-- 1. Alembic Migration Version --")
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT version_num FROM alembic_version"))
        version = result.scalar()
        report("alembic_version populated", version is not None, f"version_num = {version!r}")


# ---------------------------------------------------------------------------
# 2. Table existence
# ---------------------------------------------------------------------------
async def verify_tables():
    print("\n-- 2. Table Existence --")
    expected = {"transformers", "transformer_readings", "network_connections", "alembic_version"}
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        )
        actual = {row[0] for row in result.fetchall()}
        for t in sorted(expected):
            report(f"Table '{t}' exists", t in actual)


# ---------------------------------------------------------------------------
# 3. Column / constraint inspection
# ---------------------------------------------------------------------------
async def verify_columns_and_constraints():
    print("\n-- 3. Columns, Types & NOT NULL Constraints --")
    async with AsyncSessionLocal() as session:

        # transformers
        result = await session.execute(text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'transformers' AND table_schema = 'public'
            ORDER BY ordinal_position
        """))
        cols = {r[0]: {"type": r[1], "nullable": r[2], "default": r[3]} for r in result.fetchall()}

        report("transformers.id bigint NOT NULL",
               cols.get("id", {}).get("type") == "bigint" and cols.get("id", {}).get("nullable") == "NO")
        report("transformers.transformer_id varchar NOT NULL",
               "character varying" in cols.get("transformer_id", {}).get("type", "") and
               cols.get("transformer_id", {}).get("nullable") == "NO")
        report("transformers.metadata jsonb NOT NULL with default",
               cols.get("metadata", {}).get("type") == "jsonb" and
               cols.get("metadata", {}).get("nullable") == "NO" and
               cols.get("metadata", {}).get("default") is not None)
        report("transformers.created_at timestamptz NOT NULL",
               "timestamp" in cols.get("created_at", {}).get("type", "") and
               cols.get("created_at", {}).get("nullable") == "NO")
        report("transformers.updated_at timestamptz NOT NULL",
               "timestamp" in cols.get("updated_at", {}).get("type", "") and
               cols.get("updated_at", {}).get("nullable") == "NO")

        # transformer_readings
        result2 = await session.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'transformer_readings' AND table_schema = 'public'
            ORDER BY ordinal_position
        """))
        cols2 = {r[0]: {"type": r[1], "nullable": r[2]} for r in result2.fetchall()}

        report("transformer_readings.reading_sequence bigint NOT NULL",
               cols2.get("reading_sequence", {}).get("type") == "bigint" and
               cols2.get("reading_sequence", {}).get("nullable") == "NO")
        report("transformer_readings.voltage double precision NOT NULL",
               cols2.get("voltage", {}).get("type") == "double precision" and
               cols2.get("voltage", {}).get("nullable") == "NO")
        report("transformer_readings.current double precision NOT NULL",
               cols2.get("current", {}).get("type") == "double precision" and
               cols2.get("current", {}).get("nullable") == "NO")
        report("transformer_readings.temperature double precision NOT NULL",
               cols2.get("temperature", {}).get("type") == "double precision" and
               cols2.get("temperature", {}).get("nullable") == "NO")
        report("transformer_readings.sensor_data jsonb NOT NULL",
               cols2.get("sensor_data", {}).get("type") == "jsonb" and
               cols2.get("sensor_data", {}).get("nullable") == "NO")
        report("transformer_readings.timestamp timestamptz NOT NULL",
               "timestamp" in cols2.get("timestamp", {}).get("type", "") and
               cols2.get("timestamp", {}).get("nullable") == "NO")

        # network_connections
        result3 = await session.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'network_connections' AND table_schema = 'public'
            ORDER BY ordinal_position
        """))
        cols3 = {r[0]: {"type": r[1], "nullable": r[2]} for r in result3.fetchall()}
        report("network_connections.source_transformer_id bigint NOT NULL",
               cols3.get("source_transformer_id", {}).get("type") == "bigint" and
               cols3.get("source_transformer_id", {}).get("nullable") == "NO")
        report("network_connections.target_transformer_id bigint NOT NULL",
               cols3.get("target_transformer_id", {}).get("type") == "bigint" and
               cols3.get("target_transformer_id", {}).get("nullable") == "NO")
        report("network_connections.metadata jsonb NOT NULL",
               cols3.get("metadata", {}).get("type") == "jsonb" and
               cols3.get("metadata", {}).get("nullable") == "NO")


# ---------------------------------------------------------------------------
# 4. Indexes
# ---------------------------------------------------------------------------
async def verify_indexes():
    print("\n-- 4. Indexes --")
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("""
            SELECT indexname, tablename
            FROM pg_indexes
            WHERE schemaname = 'public'
        """))
        indexes = {r[0]: r[1] for r in result.fetchall()}

        checks = [
            ("pk_transformers", "transformers"),
            ("uq_transformer_id", "transformers"),
            ("ix_transformers_metadata_gin", "transformers"),
            ("pk_transformer_readings", "transformer_readings"),
            ("uq_transformer_reading_seq", "transformer_readings"),
            ("ix_transformer_reading_lookup", "transformer_readings"),
            ("ix_transformer_readings_timestamp", "transformer_readings"),
            ("ix_transformer_readings_sensor_data_gin", "transformer_readings"),
            ("pk_network_connections", "network_connections"),
            ("uq_network_connection_edge", "network_connections"),
            ("ix_network_connections_source", "network_connections"),
            ("ix_network_connections_target", "network_connections"),
            ("ix_network_connections_metadata_gin", "network_connections"),
        ]
        for idx_name, table_name in checks:
            report(f"Index '{idx_name}' on '{table_name}'",
                   indexes.get(idx_name) == table_name)


# ---------------------------------------------------------------------------
# 5. Foreign keys & check constraints
# ---------------------------------------------------------------------------
async def verify_fk_and_checks():
    print("\n-- 5. Foreign Keys & Check Constraints --")
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("""
            SELECT c.conname, c.contype::text
            FROM pg_constraint c
            JOIN pg_namespace n ON n.oid = c.connamespace
            WHERE n.nspname = 'public'
              AND c.contype IN ('f', 'c')
        """))
        constraints = {r[0]: (r[1].decode() if isinstance(r[1], bytes) else str(r[1])) for r in result.fetchall()}

        fks = [
            "fk_transformer_readings_transformer_id",
            "fk_network_connections_source",
            "fk_network_connections_target",
        ]
        for fk in fks:
            report(f"Foreign key '{fk}' exists",
                   fk in constraints and constraints[fk] == "f")

        report("Check constraint 'ck_network_connection_no_self_loop' exists",
               "ck_network_connection_no_self_loop" in constraints and
               constraints["ck_network_connection_no_self_loop"] == "c")


# ---------------------------------------------------------------------------
# 6. Async CRUD & relationship loading
# ---------------------------------------------------------------------------
async def verify_async_crud():
    print("\n-- 6. Async CRUD Operations --")

    # Clean up test records if any remain from a prior run
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("DELETE FROM transformers WHERE transformer_id IN ('TEST-TX-001', 'TEST-TX-002')")
        )
        await session.commit()

    # Insert two transformers
    async with AsyncSessionLocal() as session:
        t1 = Transformer(
            transformer_id="TEST-TX-001",
            name="Substation Alpha TX-1",
            metadata_payload={
                "rating_mva": 100.0,
                "voltage_rating_kv": 132.0,
                "manufacturer": "ABB",
                "installation_date": "2020-01-15",
                "location": "Substation Alpha",
                "coordinates": {"lat": 12.971599, "lng": 77.594566},
            }
        )
        t2 = Transformer(
            transformer_id="TEST-TX-002",
            name="Substation Beta TX-1",
            metadata_payload={
                "rating_mva": 50.0,
                "voltage_rating_kv": 66.0,
                "manufacturer": "Siemens",
                "location": "Substation Beta",
            }
        )
        session.add_all([t1, t2])
        await session.commit()
        await session.refresh(t1)
        await session.refresh(t2)

        report("Transformer t1 inserted (id assigned)", t1.id is not None, f"id={t1.id}")
        report("Transformer t2 inserted (id assigned)", t2.id is not None, f"id={t2.id}")
        t1_id = t1.id
        t2_id = t2.id

    # Insert readings
    async with AsyncSessionLocal() as session:
        now = datetime.now(timezone.utc)
        readings = [
            TransformerReading(
                transformer_id=t1_id,
                reading_sequence=i,
                voltage=132.5 + i * 0.1,
                current=450.0 + i * 5.0,
                temperature=65.0 + i * 0.5,
                timestamp=now,
                sensor_data={
                    "oil_temperature_c": 72.3 + i,
                    "winding_temperature_c": 85.1 + i,
                    "oil_level_pct": 98.5,
                    "vibration_mm_s": 0.03,
                    "dissolved_gas_ppm": 12.7,
                    "humidity_pct": 65.0,
                    "ambient_temperature_c": 30.5,
                }
            )
            for i in range(1, 6)
        ]
        session.add_all(readings)
        await session.commit()
    report("5 readings inserted for t1", True)

    # Insert network connection
    async with AsyncSessionLocal() as session:
        conn = NetworkConnection(
            source_transformer_id=t1_id,
            target_transformer_id=t2_id,
            connection_metadata={
                "line_length_km": 12.5,
                "resistance_ohm_km": 0.206,
                "reactance_ohm_km": 0.395,
                "capacity_mva": 80.0,
                "status": "active",
            }
        )
        session.add(conn)
        await session.commit()
    report("NetworkConnection inserted (t1 -> t2)", True)

    # Query with relationship loading
    async with AsyncSessionLocal() as session:
        stmt = (
            select(Transformer)
            .where(Transformer.transformer_id == "TEST-TX-001")
            .options(
                selectinload(Transformer.readings),
                selectinload(Transformer.outgoing_connections),
            )
        )
        result = await session.execute(stmt)
        loaded = result.scalar_one()

        report("Transformer loaded by transformer_id", loaded is not None, f"name={loaded.name!r}")
        report("Readings relationship loaded (5 items)", len(loaded.readings) == 5,
               f"count={len(loaded.readings)}")
        report("Outgoing connections loaded (1 item)", len(loaded.outgoing_connections) == 1,
               f"count={len(loaded.outgoing_connections)}")
        report("metadata_payload rating_mva accessible",
               loaded.metadata_payload.get("rating_mva") == 100.0,
               f"rating_mva={loaded.metadata_payload.get('rating_mva')}")
        first_reading = sorted(loaded.readings, key=lambda r: r.reading_sequence)[0]
        report("sensor_data JSONB accessible on reading",
               "oil_temperature_c" in first_reading.sensor_data,
               f"keys={list(first_reading.sensor_data.keys())[:3]}")
        report("reading_sequence correct (first=1)",
               first_reading.reading_sequence == 1,
               f"seq={first_reading.reading_sequence}")

    return t1_id, t2_id


# ---------------------------------------------------------------------------
# 7. Unique & check constraint enforcement
# ---------------------------------------------------------------------------
async def verify_unique_constraints(t1_id: int):
    print("\n-- 7. Constraint Enforcement --")

    # Self-loop check constraint
    async with AsyncSessionLocal() as session:
        try:
            bad_conn = NetworkConnection(
                source_transformer_id=t1_id,
                target_transformer_id=t1_id,
                connection_metadata={}
            )
            session.add(bad_conn)
            await session.commit()
            report("CHECK blocks self-loop", False, "Should have raised")
        except Exception as e:
            await session.rollback()
            report("CHECK constraint blocks self-loop",
                   "ck_network_connection_no_self_loop" in str(e) or
                   "check" in str(e).lower() or
                   "violates" in str(e).lower(),
                   "constraint violation raised correctly")

    # Duplicate reading_sequence unique constraint
    async with AsyncSessionLocal() as session:
        try:
            now = datetime.now(timezone.utc)
            dup = TransformerReading(
                transformer_id=t1_id,
                reading_sequence=1,  # Already exists
                voltage=132.0,
                current=450.0,
                temperature=65.0,
                timestamp=now,
            )
            session.add(dup)
            await session.commit()
            report("UNIQUE blocks duplicate reading_sequence", False, "Should have raised")
        except Exception as e:
            await session.rollback()
            report("UNIQUE constraint blocks duplicate reading_sequence",
                   "uq_transformer_reading_seq" in str(e) or
                   "unique" in str(e).lower() or
                   "duplicate" in str(e).lower(),
                   "unique violation raised correctly")


# ---------------------------------------------------------------------------
# 8. Cascade delete
# ---------------------------------------------------------------------------
async def verify_cascade_delete(t1_id: int, t2_id: int):
    print("\n-- 8. Cascade Delete --")

    async with AsyncSessionLocal() as session:
        t1 = await session.get(Transformer, t1_id)
        await session.delete(t1)
        await session.commit()

    async with AsyncSessionLocal() as session:
        r2 = await session.execute(
            select(TransformerReading).where(TransformerReading.transformer_id == t1_id)
        )
        remaining_readings = r2.scalars().all()
        report("Cascade delete removed transformer_readings", len(remaining_readings) == 0,
               f"remaining={len(remaining_readings)}")

        r3 = await session.execute(
            select(NetworkConnection).where(NetworkConnection.source_transformer_id == t1_id)
        )
        remaining_conns = r3.scalars().all()
        report("Cascade delete removed network_connections", len(remaining_conns) == 0,
               f"remaining={len(remaining_conns)}")

    # Cleanup t2
    async with AsyncSessionLocal() as session:
        t2 = await session.get(Transformer, t2_id)
        if t2:
            await session.delete(t2)
            await session.commit()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main():
    print("=" * 62)
    print("  Transformer DB Verification Suite")
    print("  Stack: PostgreSQL + SQLAlchemy 2.0 Async + asyncpg + Alembic")
    print("=" * 62)

    await verify_migration_version()
    await verify_tables()
    await verify_columns_and_constraints()
    await verify_indexes()
    await verify_fk_and_checks()
    t1_id, t2_id = await verify_async_crud()
    await verify_unique_constraints(t1_id)
    await verify_cascade_delete(t1_id, t2_id)

    await async_engine.dispose()

    passed = sum(1 for _, ok in results if ok)
    failed = sum(1 for _, ok in results if not ok)
    total = len(results)

    print("\n" + "=" * 62)
    if failed:
        print(f"  Results: {passed}/{total} passed, {failed} FAILED")
        for label, ok in results:
            if not ok:
                print(f"    {FAIL} {label}")
        sys.exit(1)
    else:
        print(f"  Results: {passed}/{total} passed -- ALL PASSED [OK]")
    print("=" * 62)


if __name__ == "__main__":
    asyncio.run(main())
