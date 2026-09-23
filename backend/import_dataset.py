#!/usr/bin/env python
"""
Reusable Dataset Import Command for Transformer Failure Risk Monitoring System.

Usage:
    python import_dataset.py
    python import_dataset.py --file data/sample_transformer_data.csv
    python import_dataset.py --file path/to/dataset.csv --dry-run
    python import_dataset.py --file path/to/dataset.csv --report-file rejected_audit.json
"""
import argparse
import json
import os
import sys
import asyncio
from pathlib import Path

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.ingestion.service import DatasetIngestionService
from app.config import settings


def parse_args():
    parser = argparse.ArgumentParser(
        description="Ingest transformer telemetry CSV dataset into PostgreSQL with validation and deduplication."
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        default=str(settings.resolved_sample_dataset_path),
        help=f"Path to CSV dataset (default: {settings.resolved_sample_dataset_path})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and check dataset without writing to PostgreSQL."
    )
    parser.add_argument(
        "--batch-size", "-b",
        type=int,
        default=500,
        help="Batch size for database insertions (default: 500)"
    )
    parser.add_argument(
        "--report-file", "-r",
        type=str,
        default=None,
        help="Optional path to save JSON audit report of rejected/skipped records."
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed rejection reasons to console."
    )
    return parser.parse_args()


async def run_import():
    args = parse_args()
    file_path = Path(args.file)

    print("=" * 64)
    print("  Transformer Dataset Ingestion Pipeline")
    print("  Architecture: CSV -> Validation -> Transformation -> PostgreSQL")
    print("=" * 64)
    print(f"  Target File : {file_path}")
    print(f"  Execution   : {'DRY RUN (no DB writes)' if args.dry_run else 'LIVE PERSISTENCE'}")
    print(f"  Batch Size  : {args.batch_size}")
    print("-" * 64)

    if not file_path.exists():
        print(f"\n[ERROR] File does not exist: {file_path}", file=sys.stderr)
        sys.exit(1)

    service = DatasetIngestionService(batch_size=args.batch_size)
    report = await service.ingest_async(
        source=file_path,
        filename=file_path.name,
        dry_run=args.dry_run
    )

    # Print Summary Table
    print("\n--- INGESTION RESULTS ---")
    print(f"  Filename             : {report.filename}")
    print(f"  Total Raw Rows       : {report.total_raw_rows}")
    print(f"  Valid Rows           : {report.valid_rows_count}")
    print(f"  Inserted Rows        : {report.inserted_rows_count}")
    print(f"  Skipped (Duplicates) : {report.skipped_duplicates_count}")
    print(f"  Rejected Rows        : {report.rejected_rows_count}")
    print(f"  Transformers Found   : {len(report.transformers_detected)} {report.transformers_detected}")
    print(f"  Elapsed Time         : {report.duration_seconds:.3f}s")

    if report.warnings:
        print("\n--- WARNINGS & SCHEMA ISSUES ---")
        for w in report.warnings:
            print(f"  [WARN] {w}")

    if report.rejected_records:
        print(f"\n--- REJECTED / QUARANTINED RECORDS ({len(report.rejected_records)} total) ---")
        display_count = len(report.rejected_records) if args.verbose else min(5, len(report.rejected_records))
        for item in report.rejected_records[:display_count]:
            print(f"  Row {item.row_number}: {item.reason}")
        if len(report.rejected_records) > display_count:
            print(f"  ... and {len(report.rejected_records) - display_count} more records.")
            print("  (Use --verbose to view all or --report-file <path.json> to export full audit)")

    # Save JSON report if requested
    if args.report_file:
        report_path = Path(args.report_file)
        report_data = {
            "summary": report.summary_dict(),
            "warnings": report.warnings,
            "rejected_records": [r.model_dump() for r in report.rejected_records]
        }
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
        print(f"\n  [OK] Detailed audit report written to: {report_path.resolve()}")

    print("=" * 64)
    if report.rejected_rows_count > 0 and report.valid_rows_count == 0:
        print("  Status: FAILED - Entire dataset rejected")
        sys.exit(1)
    else:
        print("  Status: SUCCESS / COMPLETED")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(run_import())
