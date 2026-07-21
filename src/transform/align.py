"""
align.py

Joins the RBA cash rate series and ASX200 series onto a common daily date
axis, with explicit timezone handling.

Responsibilities (to be implemented):
- Load the latest raw RBA and ASX200 Parquet files from data/raw/.
- Normalize both to a common `date` column (date type, no time component).
  RBA cash rate changes are published as of an effective date in AEST;
  yfinance ASX200 timestamps are typically US/Eastern or UTC-based —
  convert explicitly to AEST calendar dates before joining. Document the
  conversion logic inline (why it matters: avoiding off-by-one-day
  misalignment between the two series).
- Forward-fill the macro series onto every ASX200 trading day (RBA cash
  rate doesn't change daily) — a deliberate design decision, documented as
  such, not a bug.
- Left-join on `date`, keeping only ASX200 trading days in the final table.
- Write result to DuckDB table curated.aligned_daily in data/warehouse.duckdb.
- Log row count and any dropped/unmatched rows via dq_logger
  (status="warning" if gaps found).

NOT YET IMPLEMENTED — scaffold only.
"""

def align_daily():
    """Load raw RBA + ASX200 data, align on date, write curated.aligned_daily."""
    raise NotImplementedError


if __name__ == "__main__":
    align_daily()
