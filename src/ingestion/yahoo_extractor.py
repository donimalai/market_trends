"""
yahoo_extractor.py

Pulls daily OHLCV data for ^AXJO (S&P/ASX 200) via yfinance and writes it to
data/raw/ as Parquet.

Responsibilities (to be implemented):
- Pull the last 120 calendar days (buffer beyond the 90-day analysis window
  for rolling-window calculations).
- Return a clean DataFrame with columns: date, open, high, low, close, volume.
- Retry with backoff + timeout on the API call.
- If fewer than 90 rows are returned, or any required column is entirely
  null: log a DQ *warning* (not necessarily a hard failure) via dq_logger,
  and document explicitly whether the pipeline proceeds or aborts in that case.
- Log outcome via dq_logger (source="YahooFinance_ASX200") on success/failure.
- Write data/raw/asx200_{run_date}.parquet.
- Runnable standalone via `if __name__ == "__main__":`.

NOT YET IMPLEMENTED — scaffold only.
"""

def extract_asx200():
    """Download and return ASX200 OHLCV history as a DataFrame."""
    raise NotImplementedError


if __name__ == "__main__":
    extract_asx200()
