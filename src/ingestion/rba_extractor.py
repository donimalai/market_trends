"""
rba_extractor.py

Downloads RBA Interbank Overnight Cash Rate historical data (F1.1 series,
rba.gov.au statistical tables) and writes it to data/raw/ as Parquet.

Responsibilities (to be implemented):
- Locate and download the correct public CSV/XLS URL for the Cash Rate series.
- Parse into a clean DataFrame with columns: date, cash_rate.
- Retry with exponential backoff (max 3 attempts) + request timeout, via tenacity.
- On failure after retries, or empty/malformed response: log a failure row via
  dq_logger and raise — do not silently continue.
- On success: log a success row via dq_logger (source="RBA") and write
  data/raw/rba_cash_rate_{run_date}.parquet.
- Runnable standalone via `if __name__ == "__main__":` for manual testing.

NOT YET IMPLEMENTED — scaffold only.
"""

def extract_rba_cash_rate():
    """Download and return RBA cash rate history as a DataFrame[date, cash_rate]."""
    raise NotImplementedError


if __name__ == "__main__":
    extract_rba_cash_rate()
