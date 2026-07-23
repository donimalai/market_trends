"""
raw_loader.py

Loads each source's latest raw Parquet file into DuckDB under a `raw`
schema — a straight, untouched load (all source columns, original names,
original row order) plus one added `load_date` column recording when this
load ran. No type casting, dedup, or validation happens here — that's
silver_builder.py's job.

Layers this module writes, in data/warehouse.duckdb:
- raw.rba_cash_rate  — latest rba_cash_rate_*.parquet, as-is + load_date
- raw.asx200         — latest asx200_*.parquet, as-is + load_date
"""

import sys
from datetime import datetime
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ingestion import dq_logger

RAW_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


def _latest_raw_file(pattern: str) -> Path:
    matches = sorted(RAW_DATA_DIR.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No raw file matching '{pattern}' found in {RAW_DATA_DIR}")
    return matches[-1]


def _load_parquet_to_table(
    con: duckdb.DuckDBPyConnection,
    schema: str,
    table: str,
    parquet_path: Path,
    load_date: datetime,
) -> int:
    con.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    con.execute(
        f"CREATE OR REPLACE TABLE {schema}.{table} AS "
        f"SELECT *, ?::TIMESTAMP AS load_date FROM read_parquet(?)",
        [load_date, str(parquet_path)],
    )
    return con.execute(f"SELECT COUNT(*) FROM {schema}.{table}").fetchone()[0]


def load_raw_tables():
    """Load the latest raw RBA and ASX200 Parquet files into the `raw` schema."""
    load_date = datetime.now()
    con = duckdb.connect(str(dq_logger.DB_PATH))
    try:
        rba_path = _latest_raw_file("rba_cash_rate_*.parquet")
        rba_count = _load_parquet_to_table(con, "raw", "rba_cash_rate", rba_path, load_date)
        dq_logger.log_run(
            source="Raw_RBA",
            row_count=rba_count,
            status="success",
            message=f"Loaded raw.rba_cash_rate from {rba_path.name}",
        )

        asx_path = _latest_raw_file("asx200_*.parquet")
        asx_count = _load_parquet_to_table(con, "raw", "asx200", asx_path, load_date)
        dq_logger.log_run(
            source="Raw_ASX200",
            row_count=asx_count,
            status="success",
            message=f"Loaded raw.asx200 from {asx_path.name}",
        )
    except Exception as exc:
        dq_logger.log_run(source="Raw_Load", row_count=0, status="failure", message=str(exc))
        raise RuntimeError(f"Raw layer load failed: {exc}") from exc
    finally:
        con.close()


if __name__ == "__main__":
    load_raw_tables()
