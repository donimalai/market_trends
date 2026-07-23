# Silver Layer Schema

Generated from `data/warehouse.duckdb` as built by `src/transform/raw_loader.py` (raw layer) and `src/transform/silver_builder.py` (silver layer). Column names and types are unchanged from each source — silver only applies type casting, dedup, and validation (see `docs/silver_dq_checks.md`-equivalent logic in `silver_builder.py` for the full check list).

Each source produces two tables:
- **`silver.<name>`** — records that passed or only warned; warned rows carry a `dq_warning_reason`.
- **`silver.<name>_quarantine`** — records that failed a critical check, with `quarantine_reason` explaining why. Failed rows are never silently dropped.

Both tables in a pair share the same schema except the last column (`dq_warning_reason` vs `quarantine_reason`).

---

## silver.rba_cash_rate_daily

Source: RBA table F1 (`raw.rba_cash_rate`), validated by `_validate_rba()` in `silver_builder.py`. Primary key: `Title` (the effective date).

| Column | Type | Notes |
|---|---|---|
| `Title` | DATE | Effective date of the rate (primary key) |
| `Cash Rate Target` | DOUBLE | The RBA's policy rate — validated field for this table (range, increments, consistency checks) |
| `Change in the Cash Rate Target` | DOUBLE | Recorded change from previous value; only populated on change days |
| `Interbank Overnight Cash Rate` | DOUBLE | Market-realized overnight rate (not the validated field here) |
| `Highest Interbank Overnight Cash Rate` | DOUBLE | |
| `Lowest Interbank Overnight Cash Rate` | DOUBLE | |
| `Volume of Cash Market Transactions` | DOUBLE | $m |
| `Number of Cash Market Transactions` | DOUBLE | |
| `Total Return Index` | DOUBLE | |
| `EOD 1-month BABs/NCDs` | DOUBLE | |
| `EOD 3-month BABs/NCDs` | DOUBLE | |
| `EOD 6-month BABs/NCDs` | DOUBLE | |
| `1-month OIS` | DOUBLE | |
| `3-month OIS` | DOUBLE | |
| `6-month OIS` | DOUBLE | |
| `1-month Treasury Note` | DOUBLE | |
| `3- month Treasury Note` | DOUBLE | note the source's own column name has a stray space |
| `6- month Treasury Note` | DOUBLE | note the source's own column name has a stray space |
| `load_date` | TIMESTAMP | When this silver build ran (not when raw was ingested) |
| `dq_warning_reason` | VARCHAR | `NULL` if no warning; semicolon-joined reasons if multiple checks warned |

Last verified row count: **3,934**.

---

## silver.rba_cash_rate_daily_quarantine

Same 18 source columns + `load_date` as above, with `quarantine_reason` (VARCHAR, always populated — semicolon-joined if multiple critical checks failed) in place of `dq_warning_reason`.

Last verified row count: **0**.

---

## silver.asx200_daily

Source: yfinance `^AXJO` OHLCV (`raw.asx200`), validated by `_validate_asx200()` in `silver_builder.py`. Primary key: `Date` (the trading date).

| Column | Type | Notes |
|---|---|---|
| `Date` | DATE | Trading date (primary key) |
| `Open` | DOUBLE | |
| `High` | DOUBLE | Validated: must be >= Open/Close/Low |
| `Low` | DOUBLE | Validated: must be <= Open/Close/High |
| `Close` | DOUBLE | Validated: must be > 0 and not null |
| `Volume` | BIGINT | Validated: must be >= 0 |
| `Dividends` | DOUBLE | |
| `Stock Splits` | DOUBLE | |
| `load_date` | TIMESTAMP | When this silver build ran |
| `dq_warning_reason` | VARCHAR | `NULL` if no warning; semicolon-joined reasons if multiple checks warned |

Last verified row count: **103**.

---

## silver.asx200_daily_quarantine

Same 8 source columns + `load_date` as above, with `quarantine_reason` (VARCHAR) in place of `dq_warning_reason`.

Last verified row count: **0**.

---

## Related: dq_validation_log

Not a silver table itself, but directly tied to how these four tables get populated — one row per named check per `silver_builder.py` run (13 checks currently: 6 RBA + 7 ASX200), meant to back a DQ dashboard.

| Column | Type | Notes |
|---|---|---|
| `run_id` | VARCHAR | UUID per check |
| `run_timestamp` | TIMESTAMP | |
| `dataset` | VARCHAR | `RBA_CashRate` or `ASX200` |
| `check_name` | VARCHAR | e.g. `completeness`, `valid_range`, `no_duplicates` |
| `status` | VARCHAR | `pass` / `warning` / `fail` / `not_applicable` |
| `records_checked` | INTEGER | |
| `records_failed` | INTEGER | |
| `records_warned` | INTEGER | |
| `reason` | VARCHAR | Human-readable summary for this check's outcome |

Lives in the `main` schema (via `src/ingestion/dq_logger.py`), alongside `dq_log` (run-level pipeline log).
