"""
simulate_failure.py

Deliberately breaks each extractor (RBA: invalid URL; ASX200: invalid
ticker) to demonstrate the failure-handling + DQ logging behavior end to
end -- for the case study's "handle at least one failure scenario" demo.

Run: python scripts/simulate_failure.py

What each simulation shows:
1. The extraction fails after 3 retries (tenacity backoff visibly runs --
   not silently retried forever, not silently ignored).
2. A failure row is written to dq_log *before* the exception propagates --
   the core "no silent failures" rule holds even when things break.
3. The script catches the (expected) exception and re-queries dq_log to
   prove the failure was actually captured, not just that the script didn't
   crash.

Only module-level URL/ticker constants are monkeypatched for the duration
of this script, then restored -- the real modules and data/raw/ are never
permanently modified.
"""

import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ingestion import dq_logger, rba_extractor, yahoo_extractor

INVALID_RBA_URL = "https://www.rba.gov.au/statistics/tables/csv/this-does-not-exist.csv"
INVALID_TICKER = "NOT_A_REAL_TICKER_XYZ"


def _latest_failure_row(source: str):
    con = duckdb.connect(str(dq_logger.DB_PATH), read_only=True)
    try:
        return con.execute(
            "SELECT run_timestamp, source, row_count, status, message FROM dq_log "
            "WHERE source = ? AND status = 'failure' ORDER BY run_timestamp DESC LIMIT 1",
            [source],
        ).fetchone()
    finally:
        con.close()


def simulate_rba_failure():
    print("=" * 60)
    print("Simulated failure 1/2: RBA cash rate extraction")
    print(f"Pointing rba_extractor at an invalid URL:\n  {INVALID_RBA_URL}")
    print("=" * 60)

    original_url = rba_extractor.RBA_CASH_RATE_URL
    rba_extractor.RBA_CASH_RATE_URL = INVALID_RBA_URL
    try:
        rba_extractor.extract_rba_cash_rate()
        print("\n[UNEXPECTED] Extraction succeeded -- the failure scenario did not trigger.")
    except Exception as exc:
        print(f"\n[EXPECTED] Extraction raised {type(exc).__name__}: {exc}")
        print("This is correct: a clear exception after retries, not a silent failure.")
    finally:
        rba_extractor.RBA_CASH_RATE_URL = original_url

    row = _latest_failure_row("RBA")
    if row is None:
        print("\n[DEMO FAILED] No failure row found in dq_log -- something is wrong.")
        sys.exit(1)
    print(f"\nVerified in dq_log: {row}")


def simulate_asx200_failure():
    print("\n" + "=" * 60)
    print("Simulated failure 2/2: ASX200 extraction")
    print(f"Pointing yahoo_extractor at an invalid ticker: {INVALID_TICKER}")
    print("=" * 60)

    original_ticker = yahoo_extractor.TICKER
    yahoo_extractor.TICKER = INVALID_TICKER
    try:
        yahoo_extractor.extract_asx200()
        print("\n[UNEXPECTED] Extraction succeeded -- the failure scenario did not trigger.")
    except Exception as exc:
        print(f"\n[EXPECTED] Extraction raised {type(exc).__name__}: {exc}")
        print("This is correct: a clear exception after retries, not a silent failure.")
    finally:
        yahoo_extractor.TICKER = original_ticker

    row = _latest_failure_row("YahooFinance_ASX200")
    if row is None:
        print("\n[DEMO FAILED] No failure row found in dq_log -- something is wrong.")
        sys.exit(1)
    print(f"\nVerified in dq_log: {row}")


if __name__ == "__main__":
    simulate_rba_failure()
    simulate_asx200_failure()
    print("\n" + "=" * 60)
    print("Demo complete: both failures were caught, logged (not silently")
    print("dropped), and are now visible in dq_log -- ready for a DQ dashboard.")
    print("=" * 60)
