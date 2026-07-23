"""
rba_extractor.py

Downloads RBA Interest Rates and Yields - Money Market (daily) data — table
F1, which carries the "Interbank Overnight Cash Rate" series — and writes
the raw table to data/raw/ as Parquet, untouched.

Source: https://www.rba.gov.au/statistics/tables/csv/f1-data.csv
The file ships with ~10 metadata rows (title, description, frequency, type,
units, source, publication date, series ID) before the actual data starts,
and that row count isn't guaranteed stable across RBA revisions — so the
header and data start are located dynamically by scanning for the "Title,"
and "Series ID," marker rows rather than hardcoding a skiprows count.

Raw layer contract: every column RBA publishes (Cash Rate Target,
Interbank Overnight Cash Rate, BAB/NCD rates, OIS, Treasury Notes, ...) is
kept as-is, with the source's own column names and row order — no
selection, renaming, or dropna. Column selection (e.g. picking just
"Interbank Overnight Cash Rate") and any type/date parsing happens
downstream in align.py, not here.
"""

import io
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ingestion import dq_logger

RBA_CASH_RATE_URL = "https://www.rba.gov.au/statistics/tables/csv/f1-data.csv"
REQUEST_TIMEOUT_SECONDS = 15
RAW_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def _download_csv(url: str) -> str:
    response = requests.get(
        url,
        timeout=REQUEST_TIMEOUT_SECONDS,
        headers={"User-Agent": "market-intelligence-platform/1.0"},
    )
    response.raise_for_status()
    return response.text


def _parse_cash_rate_csv(csv_text: str) -> pd.DataFrame:
    lines = csv_text.splitlines()
    header_idx = next(i for i, line in enumerate(lines) if line.startswith("Title,"))
    series_id_idx = next(i for i, line in enumerate(lines) if line.startswith("Series ID,"))

    columns = pd.read_csv(io.StringIO(csv_text), skiprows=header_idx, nrows=0).columns
    return pd.read_csv(
        io.StringIO(csv_text), skiprows=series_id_idx + 1, header=None, names=columns
    )


def extract_rba_cash_rate() -> pd.DataFrame:
    """Download and return the raw RBA table F1 as a DataFrame, columns unchanged."""
    run_date = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        csv_text = _download_csv(RBA_CASH_RATE_URL)
        df = _parse_cash_rate_csv(csv_text)
        if df.empty:
            raise ValueError("Parsed RBA cash rate data is empty.")
    except Exception as exc:
        dq_logger.log_run(source="RBA", row_count=0, status="failure", message=str(exc))
        raise RuntimeError(f"RBA cash rate extraction failed: {exc}") from exc

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RAW_DATA_DIR / f"rba_cash_rate_{run_date}.parquet"
    df.to_parquet(output_path, index=False)

    dq_logger.log_run(
        source="RBA",
        row_count=len(df),
        status="success",
        message=f"Wrote {output_path.name}",
    )
    return df


if __name__ == "__main__":
    extract_rba_cash_rate()
