"""
align.py

Builds the normalized fact layer (dim_date, fact_market_daily,
fact_macro_daily) from the two silver tables, then the required wide
curated.aligned_daily table as a join of the two facts. See
docs/mart_data_model.md for the full proposed shape and rationale.

Timezone handling already happened in silver_builder.py: silver needs typed
DATE columns to run its own checks (freshness, completeness), so the
tz-aware-to-AEST-calendar-date conversion for ^AXJO lives there now (see
its docstring), not here. This module's job is forward-fill + join, working
on data that's already clean, typed DATE.

RBA's validated rate field is "Cash Rate Target" (see silver_builder.py's
docstring for why -- it's the field with a paired "change from previous"
column, and it's what "the RBA cash rate" means in market/press usage).
Used consistently here as the mart's `cash_rate`.

Layers this module writes, in data/warehouse.duckdb:
- curated.dim_date          -- one row per ASX200 trading date, calendar attributes
- curated.fact_market_daily -- date, OHLCV, source_load_date
- curated.fact_macro_daily  -- date, cash_rate (forward-filled onto ASX200 trading days), source_load_date
- curated.aligned_daily     -- fact_market_daily left-joined to fact_macro_daily on date
"""

import sys
from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ingestion import dq_logger


def _load_market(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    df = con.execute(
        'SELECT "Date" AS date, "Open" AS open, "High" AS high, "Low" AS low, '
        '"Close" AS close, "Volume" AS volume, load_date AS source_load_date '
        "FROM silver.asx200_daily"
    ).fetchdf()
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def _load_macro(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    df = con.execute(
        'SELECT "Title" AS date, "Cash Rate Target" AS cash_rate, load_date AS source_load_date '
        "FROM silver.rba_cash_rate_daily WHERE \"Cash Rate Target\" IS NOT NULL"
    ).fetchdf()
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def _build_dim_date(dates: pd.Series) -> pd.DataFrame:
    d = pd.DataFrame({"date": pd.to_datetime(sorted(dates.unique()))})
    d["year"] = d["date"].dt.year
    d["quarter"] = d["date"].dt.quarter
    d["month"] = d["date"].dt.month
    d["month_name"] = d["date"].dt.month_name()
    d["week_of_year"] = d["date"].dt.isocalendar().week.astype(int)
    d["day_of_week"] = d["date"].dt.dayofweek + 1  # 1=Monday .. 7=Sunday
    d["day_name"] = d["date"].dt.day_name()
    d["is_month_end"] = d["date"].dt.is_month_end
    d["is_quarter_end"] = d["date"].dt.is_quarter_end
    d["date"] = d["date"].dt.date
    return d


def align_daily():
    """Build dim_date, fact_market_daily, fact_macro_daily, curated.aligned_daily."""
    con = duckdb.connect(str(dq_logger.DB_PATH))
    try:
        con.execute("CREATE SCHEMA IF NOT EXISTS curated")

        market = _load_market(con)
        macro = _load_macro(con)
        if market.empty or macro.empty:
            raise ValueError("Loaded silver market or macro data is empty.")

        # Forward-fill: for each ASX200 trading date, take the most recent
        # Cash Rate Target (and its source_load_date) at or before that date
        # -- a deliberate design decision (RBA's rate doesn't change daily),
        # not a bug. This also naturally left-joins onto ASX200's trading
        # calendar.
        forward_filled = pd.merge_asof(
            market[["date"]],
            macro[["date", "cash_rate", "source_load_date"]],
            on="date",
            direction="backward",
        )
        unmatched = int(forward_filled["cash_rate"].isna().sum())

        dim_date = _build_dim_date(market["date"])

        fact_market = market.copy()
        fact_market["date"] = fact_market["date"].dt.date

        fact_macro = forward_filled.copy()
        fact_macro["date"] = fact_macro["date"].dt.date

        aligned_out = market.merge(
            forward_filled[["date", "cash_rate"]], on="date", how="left"
        )[["date", "open", "high", "low", "close", "volume", "cash_rate"]]
        aligned_out["date"] = aligned_out["date"].dt.date

        for name, frame in [
            ("dim_date", dim_date),
            ("fact_market_daily", fact_market),
            ("fact_macro_daily", fact_macro),
            ("aligned_daily", aligned_out),
        ]:
            con.register("view_tmp", frame)
            con.execute(f"CREATE OR REPLACE TABLE curated.{name} AS SELECT * FROM view_tmp")
            con.unregister("view_tmp")
    except Exception as exc:
        dq_logger.log_run(source="Align", row_count=0, status="failure", message=str(exc))
        raise RuntimeError(f"Alignment failed: {exc}") from exc
    finally:
        con.close()

    if unmatched:
        dq_logger.log_run(
            source="Align",
            row_count=len(aligned_out),
            status="warning",
            message=f"{unmatched} ASX200 trading day(s) had no matching RBA cash rate "
            "(likely predate the earliest available RBA data). Wrote curated.dim_date, "
            "fact_market_daily, fact_macro_daily, aligned_daily.",
        )
    else:
        dq_logger.log_run(
            source="Align",
            row_count=len(aligned_out),
            status="success",
            message="Wrote curated.dim_date, fact_market_daily, fact_macro_daily, aligned_daily.",
        )
    return aligned_out


if __name__ == "__main__":
    align_daily()
