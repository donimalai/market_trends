"""
metrics.py

Computes the platform's three metrics plus the RAG signal on top of
curated.aligned_daily, per docs/metric_definitions.md — the authoritative,
human-authored spec, finalized before this file was implemented. This
module implements exactly what's specified there; it does not redefine or
reinterpret the metrics, thresholds, warm-up rules, or the near-zero guard.

Writes two tables, in data/warehouse.duckdb, matching the mart model in
docs/mart_data_model.md:
- curated.fact_metrics_daily — the four measures alone
- curated.metrics_daily      — aligned_daily left-joined to fact_metrics_daily
  (the wide table app.py reads; contract unchanged from the original spec)
"""

import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ingestion import dq_logger

# RAG thresholds and rules -- see docs/metric_definitions.md section 4.
RAG_GREEN_MAX = 1.5
RAG_AMBER_MAX = 2.0
RAG_MIN_VOLATILITY_FLOOR = 0.03  # 3% annualised; below this, ratio is unreliable


def _rag_signal(ratio: float, trailing_mean: float) -> object:
    if pd.isna(trailing_mean):
        return None  # warm-up: not enough history yet (see docs/metric_definitions.md)
    if trailing_mean < RAG_MIN_VOLATILITY_FLOOR:
        return "insufficient signal"  # divide-by-near-zero guard
    if ratio <= RAG_GREEN_MAX:
        return "Green"
    if ratio <= RAG_AMBER_MAX:
        return "Amber"
    return "Red"


def compute_metrics():
    """Compute all metrics + RAG signal from curated.aligned_daily, write curated.fact_metrics_daily + metrics_daily."""
    con = duckdb.connect(str(dq_logger.DB_PATH))
    try:
        df = con.execute(
            "SELECT * FROM curated.aligned_daily ORDER BY date"
        ).fetchdf()
        if df.empty:
            raise ValueError("curated.aligned_daily is empty.")

        # 1. Rolling average volume (20-day) -- docs/metric_definitions.md #1.
        # min_periods=20 enforces the null warm-up rather than a misleading
        # partial-window average for the first 19 rows.
        df["rolling_avg_volume_20d"] = df["volume"].rolling(20, min_periods=20).mean()

        # 2. Day-over-day rate of change (%) -- docs/metric_definitions.md #2.
        # pct_change() is null (not zero) on the first row, matching the spec.
        df["rate_of_change_pct"] = df["close"].pct_change() * 100

        # 3. 14-day realised volatility, annualised -- docs/metric_definitions.md #3.
        log_return = np.log(df["close"] / df["close"].shift(1))
        df["volatility_14d_annualised"] = log_return.rolling(14, min_periods=14).std() * np.sqrt(252)

        # 4. RAG signal -- docs/metric_definitions.md #4. Needs a 90-day
        # trailing mean of the volatility figure itself, on top of that
        # figure's own 14-day warm-up -- ~104 trading days total before the
        # first non-null signal, documented as its own, longer warm-up
        # period rather than folded into the shorter warm-ups above.
        df["volatility_90d_trailing_mean"] = (
            df["volatility_14d_annualised"].rolling(90, min_periods=90).mean()
        )
        rag_ratio = df["volatility_14d_annualised"] / df["volatility_90d_trailing_mean"]
        df["rag_signal"] = [
            _rag_signal(r, m)
            for r, m in zip(rag_ratio, df["volatility_90d_trailing_mean"])
        ]

        fact_metrics = df[
            [
                "date",
                "rolling_avg_volume_20d",
                "rate_of_change_pct",
                "volatility_14d_annualised",
                "volatility_90d_trailing_mean",
                "rag_signal",
            ]
        ]
        metrics_daily = df[
            [
                "date",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "cash_rate",
                "rolling_avg_volume_20d",
                "rate_of_change_pct",
                "volatility_14d_annualised",
                "rag_signal",
            ]
        ]

        con.register("fact_metrics_view", fact_metrics)
        con.execute(
            "CREATE OR REPLACE TABLE curated.fact_metrics_daily AS SELECT * FROM fact_metrics_view"
        )
        con.unregister("fact_metrics_view")

        con.register("metrics_daily_view", metrics_daily)
        con.execute(
            "CREATE OR REPLACE TABLE curated.metrics_daily AS SELECT * FROM metrics_daily_view"
        )
        con.unregister("metrics_daily_view")
    except Exception as exc:
        dq_logger.log_run(source="Metrics", row_count=0, status="failure", message=str(exc))
        raise RuntimeError(f"Metrics computation failed: {exc}") from exc
    finally:
        con.close()

    rag_populated = int(metrics_daily["rag_signal"].notna().sum())
    dq_logger.log_run(
        source="Metrics",
        row_count=len(metrics_daily),
        status="success" if rag_populated else "warning",
        message=f"Wrote curated.fact_metrics_daily, metrics_daily. "
        f"{rag_populated}/{len(metrics_daily)} row(s) have a populated RAG signal "
        "(requires ~104 trading days of history).",
    )
    return metrics_daily


if __name__ == "__main__":
    compute_metrics()
