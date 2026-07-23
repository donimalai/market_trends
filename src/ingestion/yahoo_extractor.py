"""
yahoo_extractor.py

Pulls daily OHLCV data for ^AXJO (S&P/ASX 200) via yfinance and writes the
raw table to data/raw/ as Parquet, untouched.

Lookback window is 220 calendar days, not the spec's original 120 (an
earlier revision used 150 -- also insufficient, see below). 120 calendar
days only yields ~83 ASX trading rows (weekends + public holidays), and 150
yields ~103 -- both below what the mart layer actually needs: the RAG
signal (curated.metrics_daily) requires ~104 trading days of history before
its first non-null value (14-day volatility + a 90-day trailing average of
it -- see docs/metric_definitions.md section 4), and the dashboard's
90-day chart window additionally wants its own 20-day rolling-volume
warm-up before that, i.e. >=110 trading days for a gap-free visible window.
220 calendar days reliably clears ~150 trading rows, comfortably covering
both.

Raw layer contract: every column yfinance returns (Open, High, Low, Close,
Volume, Dividends, Stock Splits) is kept as-is, with yfinance's own column
names — no selection, renaming, or dropna. The only structural step is
resetting the Date index into a plain column, since Parquet doesn't
round-trip a pandas index. Column selection/renaming, and any timezone
conversion, happens downstream in align.py, not here.

Note on timestamps: yfinance's index for ^AXJO is already tz-aware in
Australia/Sydney (verified live), not UTC/US-Eastern as might be assumed for
a generic yfinance ticker. The raw Date column here is left exactly as
yfinance returns it (tz-aware); align.py is the one place that should reason
about what that means for joining against the RBA series.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ingestion import dq_logger

TICKER = "^AXJO"
LOOKBACK_DAYS = 220
MIN_EXPECTED_ROWS = 110
REQUEST_TIMEOUT_SECONDS = 15
RAW_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def _download_asx200(start: datetime, end: datetime) -> pd.DataFrame:
    raw = yf.Ticker(TICKER).history(
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        interval="1d",
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if raw is None or raw.empty:
        raise ValueError("yfinance returned no ASX200 data.")
    return raw.reset_index()


def extract_asx200() -> pd.DataFrame:
    """Download and return the raw ^AXJO OHLCV history as a DataFrame, columns unchanged."""
    run_date = datetime.now().strftime("%Y%m%d_%H%M%S")
    end = datetime.now()
    start = end - timedelta(days=LOOKBACK_DAYS)

    try:
        df = _download_asx200(start, end)
    except Exception as exc:
        dq_logger.log_run(
            source="YahooFinance_ASX200", row_count=0, status="failure", message=str(exc)
        )
        raise RuntimeError(f"ASX200 extraction failed: {exc}") from exc

    required_cols = ["Open", "High", "Low", "Close", "Volume"]
    all_null_cols = [c for c in required_cols if df[c].isna().all()]
    warnings = []
    if len(df) < MIN_EXPECTED_ROWS:
        warnings.append(f"only {len(df)} rows returned (< {MIN_EXPECTED_ROWS} expected)")
    if all_null_cols:
        warnings.append(f"columns entirely null: {', '.join(all_null_cols)}")

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RAW_DATA_DIR / f"asx200_{run_date}.parquet"
    df.to_parquet(output_path, index=False)

    # Decision: a missing-data scenario is logged as a warning, not a hard
    # failure -- the pipeline still proceeds. A short gap (holiday-heavy
    # stretch, yfinance briefly missing a day) shouldn't block align.py and
    # metrics.py, which degrade gracefully (rolling windows just carry more
    # nulls near the start). Only zero rows at all aborts the run, above.
    if warnings:
        dq_logger.log_run(
            source="YahooFinance_ASX200",
            row_count=len(df),
            status="warning",
            message="; ".join(warnings) + f" | wrote {output_path.name}",
        )
    else:
        dq_logger.log_run(
            source="YahooFinance_ASX200",
            row_count=len(df),
            status="success",
            message=f"Wrote {output_path.name}",
        )
    return df


if __name__ == "__main__":
    extract_asx200()
