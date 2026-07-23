"""
run_pipeline.py

Runs the full pipeline end-to-end, in order:
  1. RBA cash rate extraction  -> data/raw/rba_cash_rate_*.parquet
  2. ASX200 extraction         -> data/raw/asx200_*.parquet
  3. Raw layer load            -> raw.rba_cash_rate, raw.asx200
  4. Silver layer build        -> silver.*, quarantine tables, dq_validation_log
  5. Alignment (mart facts)    -> curated.dim_date, fact_market_daily, fact_macro_daily, aligned_daily
  6. Metrics                   -> curated.fact_metrics_daily, curated.metrics_daily

This is the single command referenced in the README for "how to run
locally": `python run_pipeline.py`. Prints clear stage-by-stage console
output, then a summary of this run's dq_log outcomes.

Extraction stages (1-2) are independent sources -- one failing doesn't
block the other from running (raw_loader will just fall back to the latest
existing Parquet file, and the failure is still visible in dq_log, not
silent). Stages 3-6 each depend on the previous stage's output, so the run
stops immediately if one of them fails.
"""

import sys
from datetime import datetime
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.ingestion import dq_logger
from src.ingestion.rba_extractor import extract_rba_cash_rate
from src.ingestion.yahoo_extractor import extract_asx200
from src.transform.align import align_daily
from src.transform.metrics import compute_metrics
from src.transform.raw_loader import load_raw_tables
from src.transform.silver_builder import build_silver_tables


def _run_stage(label: str, fn, required: bool = True) -> bool:
    print(f"\n--- {label} ---")
    try:
        fn()
        print(f"[OK] {label} complete.")
        return True
    except Exception as exc:
        print(f"[FAILED] {label}: {exc}")
        if required:
            print("Stopping run -- downstream stages depend on this one's output.")
        return False


def _print_run_summary(run_start: datetime) -> None:
    con = duckdb.connect(str(dq_logger.DB_PATH), read_only=True)
    try:
        log_df = con.execute(
            "SELECT run_timestamp, source, status, row_count, message "
            "FROM dq_log WHERE run_timestamp >= ? ORDER BY run_timestamp",
            [run_start],
        ).fetchdf()
    finally:
        con.close()

    print("\n=== DQ Log Summary (this run) ===")
    if log_df.empty:
        print("No dq_log rows written this run.")
        return
    for _, row in log_df.iterrows():
        print(f"[{row['status'].upper():7s}] {row['source']:22s} rows={row['row_count']:<6} {row['message']}")
    print(f"\nTotals: {log_df['status'].value_counts().to_dict()}")


def main():
    run_start = datetime.now()
    print("=" * 60)
    print("Market Intelligence Platform -- Pipeline Run")
    print(f"Started: {run_start.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Extraction: independent sources, one failing doesn't block the other.
    _run_stage("1/6 RBA cash rate extraction", extract_rba_cash_rate, required=False)
    _run_stage("2/6 ASX200 extraction", extract_asx200, required=False)

    # Transform: each stage depends on the previous one's output, so stop
    # immediately (not silently continue on stale/missing data) if one fails.
    for label, fn in [
        ("3/6 Raw layer load", load_raw_tables),
        ("4/6 Silver layer build (validation + quarantine)", build_silver_tables),
        ("5/6 Alignment (mart facts)", align_daily),
        ("6/6 Metrics computation", compute_metrics),
    ]:
        if not _run_stage(label, fn):
            _print_run_summary(run_start)
            sys.exit(1)

    _print_run_summary(run_start)

    print("\nDashboard: streamlit run src/dashboard/app.py")
    print("# To run on a schedule: cron (Linux/Mac) e.g. '0 7 * * 1-5 python run_pipeline.py' or Task Scheduler (Windows)")


if __name__ == "__main__":
    main()
