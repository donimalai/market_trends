# Market Intelligence Platform

Local data pipeline + dashboard: 90-day ASX 200 market trend, watched
alongside the RBA cash rate, for financially literate but non-technical
management. Built as a case study for a Data & Analytics Engineering Lead
role — data as infrastructure, not a one-off report.

**Repo:** private by design (no LICENSE file — this is a case study
submission, not an open-source release; the case study doesn't require a
public repo). [github.com/donimalai/market_trends](https://github.com/donimalai/market_trends)

**Dashboard:** run locally via `streamlit run src/dashboard/app.py` (see Run Instructions below) — no hosted link for this submission.

## Overview

Bank management wants one question answered without reading a data pipeline:
*"How has ASX 200 market activity trended over the past 90 days, and is
there anything we should be watching?"* This platform answers it with three
things on one dashboard — price/volume trend, a macro overlay against the
RBA cash rate, and a single Red/Amber/Green volatility signal — backed by a
local pipeline that pulls both sources daily, validates them, and refreshes
one DuckDB file. RBA cash rate + ASX 200 was chosen because it's the case
study's own suggested pairing and sits naturally alongside a Sydney/Market
Services context.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Run Instructions

```bash
python run_pipeline.py
streamlit run src/dashboard/app.py
```

`run_pipeline.py` runs the full 6-stage chain end-to-end (extraction ->
raw -> silver -> mart -> metrics) and prints a DQ summary; the dashboard
then reads the result. To demo the failure-handling path instead:
`python scripts/simulate_failure.py`.

## Architecture

```
data/raw/*.parquet  (immutable, gitignored)
        |
        v
raw.*        -- straight load into DuckDB, zero transformation, + load_date
        |
        v
silver.*     -- typed, deduped, validated (13 checks); failures quarantined
        |      to silver.*_quarantine, every check logged to dq_validation_log
        v
curated.*    -- star schema: dim_date + fact_market_daily + fact_macro_daily
        |      + fact_metrics_daily, joined into the two required wide
        |      tables (aligned_daily, metrics_daily) -- see docs/mart_data_model.md
        v
src/dashboard/app.py  -- reads ONLY curated.metrics_daily
```

Layer separation exists so each stage can be re-run, tested, and debugged
independently — e.g. a silver validation bug (see Data Quality Notes below)
can be fixed and re-run without re-pulling raw data. `data/warehouse.duckdb`
holds every layer; `dq_log` (one row per pipeline stage per run) and
`dq_validation_log` (one row per named DQ check) both live there too, so a
DQ dashboard could be built directly off this file.

## Design Decisions

- **Source choice:** RBA Cash Rate (table F1) + ASX 200 daily OHLCV via
  `yfinance` (`^AXJO`) — the case study's own suggested combination.
- **Metric definitions:** defined in plain language, by the human lead,
  *before* any agent implementation — see
  [`docs/metric_definitions.md`](docs/metric_definitions.md). `metrics.py`
  implements exactly what's specified there.
- **RAG threshold:** self-relative (current 14-day volatility vs. its own
  90-day trailing average), not a fixed number — flags *regime shifts*
  without needing an externally sourced "normal" baseline. Full rationale,
  the finalized 1.5x/2.0x boundary logic, the ~104-trading-day warm-up rule,
  and the 3%-annualised near-zero guard are in
  [`docs/metric_definitions.md`](docs/metric_definitions.md) section 4.
- **Timezone handling:** lives in exactly one place (`silver_builder.py`,
  which needs typed dates for its own checks). Verified live that
  `^AXJO`'s yfinance timestamps are already tz-aware `Australia/Sydney` —
  not UTC/US-Eastern, the usual assumption for a generic yfinance ticker —
  so no actual cross-timezone shift happens, just a documented read of an
  already-local date.
- **Raw layer fidelity:** `data/raw/` and `raw.*` hold every source column,
  original names, original row order, no filtering. Column selection,
  typing, and cleaning all happen downstream in `silver_builder.py`, so a
  requirement change never means re-pulling source data.
- **Flexible mart model:** the case study's two required wide tables
  (`curated.aligned_daily`, `curated.metrics_daily`) still exist unchanged,
  but sit on top of a small star schema (`dim_date` + fact tables) so a
  future custom dashboard isn't stuck widening those tables further — see
  [`docs/mart_data_model.md`](docs/mart_data_model.md).

## Data Quality Notes

The real issue: while building the DQ validation suite itself, the RBA
`valid_range` check initially miscounted a *missing* value as *out of
range*. `pandas.Series.between()` returns `False` for `NaN`, and the check
negated that result to find violations — so today's not-yet-published rate
(a genuine `NULL`, not an implausible number) got flagged as "outside
[0,15]%". Caught by inspecting the one flagged row rather than trusting the
aggregate count. Fixed by splitting it into two separate checks (missing
vs. out-of-range), regression-tested in
[`tests/test_silver_builder.py`](tests/test_silver_builder.py).

A second, separate issue is worth a line too: the RAG signal requires
~104 trading days of history before its first value, but the original
150-calendar-day ASX200 lookback only yielded 103 trading rows — the
dashboard's required RAG badge would have shipped blank on real data.
Caught by checking the actual populated-row count after running
`metrics.py`, not just that it ran without error. Fixed by widening the
lookback to 220 calendar days. Full detail on both: `ai_agent_process_log.md`
Entries 9 and 12.

## AI Agent Log

Every file under `src/` and `run_pipeline.py` was AI-drafted this session
and human-reviewed/iterated in the same conversation (not a one-shot
generate-and-accept — see `docs/ai_agent_process_log.md` for the full
turn-by-turn record, 12 entries). `docs/metric_definitions.md` is the one
exception: authored by the human lead first, with the agent explicitly
excluded from writing it, per the case study's AI Agent Lens requirement.

**One specific incomplete AI output, caught and corrected:** when
`silver_builder.py`'s quarantine tables have zero failed rows (the common
case), pandas' dtype inference on an empty `.apply()` result silently gave
the `quarantine_reason` column an `INTEGER` type instead of `VARCHAR` in
DuckDB. This wasn't a crash — it would only have broken the moment a real
quarantined row with a differently-typed value showed up, and local testing
with 0 quarantined rows is the *common* path. Caught by inspecting
`DESCRIBE` output on the table, not the row count. Fixed with an explicit
`.astype(str)` forced even on the empty-row path, and now has a dedicated
regression test for both RBA and ASX200 (`test_clean_data_produces_no_quarantine_with_correct_reason_column_type`).

## Handoff Notes

**Coding standards:** one ingestion module per source (retry + timeout via
`tenacity`, raw output untouched, every run logged via `dq_logger` —
success or failure). Raw layer must never be pre-cleaned or narrowed —
column selection/typing/validation belong in `silver_builder.py`, not the
extractors. `src/ingestion/dq_logger.py` has zero dependency on extractor
or transform code (one-way imports only) to avoid circular imports.

**Adding a new source:** mirror `rba_extractor.py`/`yahoo_extractor.py`
(retry/timeout, write every source column untouched to `data/raw/`, log via
`dq_logger.log_run`), then add a load step in `raw_loader.py`, a validation
function in `silver_builder.py` (checks + `dq_logger.log_validation` per
check), and wire the new fact into `align.py`'s mart tables.

**How DQ logging works:** two tables. `dq_log` — one row per pipeline
*stage* per run (source, row_count, status, message); `dq_validation_log` —
one row per named *check* per run (structured checked/failed/warned counts,
not free text), specifically so a DQ dashboard can chart pass rates per
check over time.

**Guardrails for AI-assisted changes:** (1) metric/threshold definitions
must be human-authored and approved *before* prompting an agent to
implement them — never let the same pass draft the spec and the code. (2)
Any schema-level change (new mart tables, new columns) gets a written
design doc reviewed before code, the same gate applied to
`docs/mart_data_model.md`. (3) Trust nothing from an AI-generated module
until it's run against real pipeline output and the *actual* row/column
counts are checked — not just "no exception was raised" (this is what
caught both issues in Data Quality Notes above).
