# Requirement Specification — Data Ingestion Layer

Formal requirements for the two ingestion modules (`src/ingestion/rba_extractor.py`, `src/ingestion/yahoo_extractor.py`), derived from Prompts 2 and 3 of `claude_code_build_prompts_refined.md` plus the implementation facts discovered while actually building them (real source URL, real row counts, real timezone behavior). This is the spec a junior engineer — or an AI agent — should be able to implement against without needing to re-derive any of these decisions from scratch.

---

## 1. RBA Cash Rate Extractor (`rba_extractor.py`)

### 1.1 Purpose
Pull the RBA's daily cash rate target series so it can serve as the macro overlay against ASX 200 price movement.

### 1.2 Source
- **URL:** `https://www.rba.gov.au/statistics/tables/csv/f1-data.csv` (RBA statistical table F1, daily).
- **Explicitly not** the F1.1 table (monthly) — too coarse to align against daily ASX200 trading days.
- **Verified live:** 3,934 rows, 18 columns, series begins 2011-01-04.

### 1.3 Functional Requirements
| ID | Requirement |
|---|---|
| FR-1 | Download the F1 CSV over HTTP. |
| FR-2 | Parse into a DataFrame preserving **all 18 source columns**, original names, original row order — no selection, renaming, type coercion, or null-dropping at this stage. |
| FR-3 | Write the raw DataFrame to `data/raw/rba_cash_rate_{run_date}.parquet`. |
| FR-4 | Expose a standalone entry point (`if __name__ == "__main__":`) for manual runs. |

### 1.4 Non-Functional Requirements
| ID | Requirement |
|---|---|
| NFR-1 | Retry failed HTTP requests with exponential backoff, max 3 attempts, via `tenacity`. |
| NFR-2 | Enforce a request timeout — do not hang indefinitely on a slow/unresponsive endpoint. |

### 1.5 Error Handling / Data Quality
| ID | Requirement |
|---|---|
| DQ-1 | On failure after retries, or an empty/malformed response: log a `failure` row via `dq_logger.log_run(source="RBA", ...)` **and** raise — never fail silently or return partial data as if it succeeded. |
| DQ-2 | On success: log a `success` row via `dq_logger.log_run(source="RBA", row_count=<n>, status="success")`. |

### 1.6 Explicitly Out of Scope (deferred to `align.py`)
Column selection (which of the 18 columns matter — specifically `Title`/effective date and `Interbank Overnight Cash Rate`), renaming to `date`/`cash_rate`, date-string parsing (`%d-%b-%Y`), numeric coercion, and dropping unparseable rows. This module's only job is a faithful, unmodified copy of the source into `data/raw/`.

### 1.7 Acceptance Criteria
- Running the module standalone produces one `.parquet` file in `data/raw/` and exactly one row in `dq_log`.
- Re-running with a deliberately broken URL (see `scripts/simulate_failure.py`) produces a `failure` row in `dq_log`, not a crash with no logged trace.

---

## 2. ASX 200 Market Data Extractor (`yahoo_extractor.py`)

### 2.1 Purpose
Pull daily OHLCV data for the S&P/ASX 200 (`^AXJO`) as the market-activity series the dashboard is built around.

### 2.2 Source
- **Library:** `yfinance`, ticker `^AXJO`.
- **Lookback window:** 150 calendar days (not 120). 120 days was verified live to return only ~83 ASX trading rows — under the 90-row minimum this module itself checks for, which would trip the "insufficient data" DQ warning on every single run. 150 days reliably clears 90+ trading rows.
- **Timezone fact (verified live):** yfinance's index for `^AXJO` is already tz-aware `Australia/Sydney`, not UTC or US/Eastern as might be assumed for a generic yfinance ticker. This module does not need to convert it — it's left untouched in the raw `Date` column. `align.py` is where this fact actually gets used (see its spec).

### 2.3 Functional Requirements
| ID | Requirement |
|---|---|
| FR-1 | Pull daily OHLCV for `^AXJO` over the last 150 calendar days. |
| FR-2 | Return/write a DataFrame preserving **all** columns yfinance returns (`Date`, `Open`, `High`, `Low`, `Close`, `Volume`, `Dividends`, `Stock Splits`), original names — no renaming, no column dropping. |
| FR-3 | The only structural transformation permitted: reset the `Date` index into a plain column (Parquet doesn't round-trip a pandas index). |
| FR-4 | Write the raw DataFrame to `data/raw/asx200_{run_date}.parquet`. |
| FR-5 | Expose a standalone entry point (`if __name__ == "__main__":`) for manual runs. |

### 2.4 Non-Functional Requirements
| ID | Requirement |
|---|---|
| NFR-1 | Retry the API call with backoff on transient failure. |
| NFR-2 | Enforce a timeout on the call. |

### 2.5 Error Handling / Data Quality
| ID | Requirement |
|---|---|
| DQ-1 | If fewer than 90 rows are returned, or any required column is entirely null: log a `warning` (not necessarily a hard failure) via `dq_logger.log_run(source="YahooFinance_ASX200", ...)`. |
| DQ-2 | The decision of whether the pipeline proceeds or aborts on that warning must be explicit and documented in code — not left implicit. |
| DQ-3 | On success: log a `success` row via `dq_logger.log_run(source="YahooFinance_ASX200", row_count=<n>, status="success")`. |

### 2.6 Explicitly Out of Scope (deferred to `align.py`)
Column renaming (`Open`→`open`, etc.), dropping `Dividends`/`Stock Splits`, and any timezone conversion. This module's job is a faithful copy of what yfinance returns.

### 2.7 Acceptance Criteria
- Running standalone produces one `.parquet` file in `data/raw/` with 90+ rows under normal conditions, and exactly one row in `dq_log`.
- A run that returns fewer than 90 rows produces a `warning` row in `dq_log`, not a silent pass-through.

---

## 3. Shared Contract Between Both Modules

Both extractors follow the same raw-layer fidelity principle established after Prompts 2/3 were first drafted: **`data/raw/` holds each source's own columns, unmodified — no selection, renaming, or cleaning at ingestion time.** All cleaning, column mapping, type parsing, and timezone handling happens once, downstream, in `align.py`. This keeps the raw layer genuinely raw (useful if a future source column is needed that today's `align.py` doesn't select) and keeps the timezone/schema logic in exactly one place rather than duplicated across extractors.

Both modules also share the DQ logging contract: every run — success, warning, or failure — writes exactly one row to `dq_log` via `dq_logger.log_run(...)`, per `docs/claude_code_build_prompts_refined.md` Prompt 4.
