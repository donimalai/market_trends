"""
dq_logger.py

Shared data-quality logging utility. Every extraction run — success,
warning, or failure — writes exactly one row to dq_log. No silent failures.

Also owns dq_validation_log: one row per named data-quality check (not per
pipeline run), with structured pass/fail/warning counts rather than a
free-text message — this is the table a DQ dashboard would actually chart
(e.g. "pass rate of the valid_range check over time"), which dq_log's
run-level shape can't support on its own.

Zero dependency on the extractor/transform modules — they import this
module, never the reverse (avoids circular imports).
"""

import uuid
from datetime import datetime
from pathlib import Path

import duckdb

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "warehouse.duckdb"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS dq_log (
    run_id VARCHAR,
    run_timestamp TIMESTAMP,
    source VARCHAR,
    row_count INTEGER,
    status VARCHAR,
    message VARCHAR
)
"""

CREATE_VALIDATION_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS dq_validation_log (
    run_id VARCHAR,
    run_timestamp TIMESTAMP,
    dataset VARCHAR,
    check_name VARCHAR,
    status VARCHAR,
    records_checked INTEGER,
    records_failed INTEGER,
    records_warned INTEGER,
    reason VARCHAR
)
"""


def log_run(source: str, row_count: int, status: str, message: str = None):
    """Insert one DQ log row and print a console summary line."""
    run_id = str(uuid.uuid4())
    run_timestamp = datetime.now()

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))
    try:
        con.execute(CREATE_TABLE_SQL)
        con.execute(
            "INSERT INTO dq_log VALUES (?, ?, ?, ?, ?, ?)",
            [run_id, run_timestamp, source, row_count, status, message],
        )
    finally:
        con.close()

    print(
        f"[DQ] {status.upper():7s} | source={source} | rows={row_count} | "
        f"{message or ''}"
    )


def log_validation(
    dataset: str,
    check_name: str,
    status: str,
    records_checked: int,
    records_failed: int = 0,
    records_warned: int = 0,
    reason: str = None,
):
    """Insert one row per named DQ check and print a console summary line."""
    run_id = str(uuid.uuid4())
    run_timestamp = datetime.now()

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))
    try:
        con.execute(CREATE_VALIDATION_TABLE_SQL)
        con.execute(
            "INSERT INTO dq_validation_log VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                run_id,
                run_timestamp,
                dataset,
                check_name,
                status,
                records_checked,
                records_failed,
                records_warned,
                reason,
            ],
        )
    finally:
        con.close()

    print(
        f"[DQ-CHECK] {status.upper():14s} | {dataset:12s} | {check_name:22s} | "
        f"checked={records_checked} failed={records_failed} warned={records_warned} | {reason or ''}"
    )
