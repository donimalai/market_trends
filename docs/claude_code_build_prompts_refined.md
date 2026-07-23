# Market Intelligence Platform — Build Spec for Claude Code (Refined)

Refined against the actual case study PDF (not just the paraphrase). Changes from the original draft are marked **[CHANGED]**; new additions are marked **[NEW]**. Rationale for each change is inline so you know what to push back on.

## Context (for reference, not a prompt)
5-day case study for a Senior Data Analytics/BI Specialist (Data & Analytics Engineering Lead, Associate Director) role at Macquarie Market Services (post-trade transformation team). The JD's framing — data as infrastructure, instrumented OKRs replacing manual reporting, self-service analytics, observability built-in not bolted-on, human-AI-agent hybrid delivery — is worth echoing in the README/dashboard language, since it signals you read the JD, not just the case study brief.

The case study is graded on four parts (Pipeline, Curation, Dashboard, Presentation), plus an optional bonus slide. **[NEW]** Note that only the first three are code — the Presentation itself is a separate deliverable (a talk/deck) these prompts don't produce. Don't treat "finish the 11 prompts" as "finished the case study."

## Chosen Design
- **Macro source:** RBA Cash Rate historical data (rba.gov.au)
- **Market source:** Yahoo Finance — ASX 200 daily OHLCV (via yfinance)
- **Stack:** Python, DuckDB (storage + transform), Streamlit (dashboard), all local, no cloud dependency
- **Metrics:** 20-day rolling average volume, day-over-day rate of change, 14-day realised volatility (annualised)
- **RAG signal:** Volatility > 1.5x its 90-day trailing mean = Amber; > 2x = Red; else Green
- **Layers:** raw (DuckDB/Parquet, immutable) → DQ log table → transform (align/join on date, timezone-normalized) → curated (DuckDB tables) → dashboard (Streamlit)

**[NEW]** This pairing directly matches the case study's own suggested combo (RBA macro + ASX 200 market index) and sits naturally alongside the JD's Sydney/Market Services/ASX context — no changes needed here.

**[CHANGED]** "Raw, immutable" is now enforced literally: `data/raw/` holds every column each source returns, original names, original row order — no selection, renaming, or dropna at ingestion time. Column selection, renaming, date/type parsing, and timezone handling all happen downstream in `align.py` (Prompt 5), not in the extractors. See the updated Prompts 2, 3, and 5.

---

## PROMPT 0 — Repo & git setup **[NEW]**

Before scaffolding, initialize the project as a git repo and connect it to the existing GitHub repo `<your-repo-url-here>`. Create an initial commit after Prompt 1's scaffold lands. Add a `LICENSE`-free, private-by-default assumption (case study doesn't require public). This closes the gap between "runs locally" and the actual submission format, which is "GitHub repo, plus dashboard link."

*(Fill in `<your-repo-url-here>` with your actual repo before running this.)*

---

## PROMPT 1 — Repo scaffold

Create a Python project scaffold for a local data pipeline + dashboard called "market-intelligence-platform". Structure:
- `src/ingestion/` — one module per source (rba_extractor.py, yahoo_extractor.py), each with retry + timeout handling using `tenacity` or manual backoff, writing raw output to `data/raw/` as Parquet with a run timestamp.
- `src/ingestion/dq_logger.py` — a shared utility that logs each extraction run's outcome (source, timestamp, row count, status, error message if any) to a DuckDB table `dq_log` in `data/warehouse.duckdb`. No silent failures — every run must write a log row, including failures.
- `src/transform/` — `align.py` (join RBA and ASX200 data on a common daily date axis, explicitly converting/normalizing timezones — RBA dates are AEST, Yahoo Finance ASX200 timestamps may be UTC or exchange-local; document the conversion logic in comments) and `metrics.py` (compute: 20-day rolling average volume, day-over-day % rate of change on close price, 14-day realised volatility annualised from log returns).
- `src/dashboard/app.py` — Streamlit app (placeholder for now).
- `tests/` — pytest structure with placeholder test files for ingestion, transform, and metrics.
- `data/raw/`, `data/curated/` folders with `.gitkeep`.
- `requirements.txt` with: duckdb, pandas, yfinance, requests, streamlit, plotly, tenacity, pytest, python-dateutil, pytz.
- `README.md` with placeholder sections: Overview, Setup, Run Instructions, Architecture, Design Decisions, Data Quality Notes, AI Agent Log, Handoff Notes.
- `.gitignore` for Python, DuckDB files, and Streamlit cache.
- **[NEW]** `docs/metric_definitions.md` — placeholder that will hold the human-authored plain-language metric definitions (see Prompt 6 change below). Scaffold it empty; do not let the agent fill this in.

Do not implement business logic yet — just scaffold with clear docstrings stating what each module should do.

---

## PROMPT 2 — RBA macro data extractor **[CHANGED]**

**Why this changed:** raw output must be the source's own columns, unmodified — see the Chosen Design note above. Originally this step both downloaded *and* cleaned (selected `date`/`cash_rate`, parsed types, dropped nulls) in one pass, which meant `data/raw/` was never actually raw.

Implement `src/ingestion/rba_extractor.py`. It must:
- Download the RBA Cash Rate historical data (the F1.1 or equivalent series from rba.gov.au statistical tables — find the correct public CSV/XLS URL for the Interbank Overnight Cash Rate).
- Parse the CSV into a DataFrame keeping **all** columns the source table returns, with their original names and row order (**[CHANGED]** — no column selection, renaming, type coercion, or dropna at this stage).
- Implement retry with exponential backoff (max 3 attempts) and a timeout on the HTTP request, using `tenacity`.
- Handle the failure scenario explicitly: if the download fails after retries, or the response is empty/malformed, log a failure row via `dq_logger` and raise a clear exception rather than silently continuing.
- On success, log a success row via `dq_logger` (source="RBA", row_count, status="success") and write the raw DataFrame to `data/raw/rba_cash_rate_{run_date}.parquet`.
- Include a `if __name__ == "__main__":` block to run standalone for testing.

**Actual URL used:** `https://www.rba.gov.au/statistics/tables/csv/f1-data.csv` (table F1, daily — carries the "Interbank Overnight Cash Rate" column among 18 total; the monthly F1.1 table is not granular enough to align against daily ASX200 trading days). Verified live: 3,934 rows, all 18 source columns preserved, 2011-01-04 onward.

---

## PROMPT 3 — Yahoo Finance market data extractor **[CHANGED]**

**Why this changed:** same raw-layer fidelity rule as Prompt 2 — column renaming (`Open`→`open` etc.) and column selection (dropping `Dividends`/`Stock Splits`) used to happen before the Parquet write; that's now deferred to `align.py`.

Implement `src/ingestion/yahoo_extractor.py`. It must:
- Use `yfinance` to pull daily OHLCV data for `^AXJO` (S&P/ASX 200). **[CHANGED]** Lookback is 150 calendar days, not the original 120 — verified live that 120 days only yields ~83 ASX trading rows (below the 90-row minimum this module checks for), which would leave the dashboard's 90-day view underfilled and make the "fewer than 90 rows" DQ warning fire on every single run. 150 days reliably clears 90+ trading rows.
- Return a DataFrame keeping **all** columns yfinance returns (`Date`, `Open`, `High`, `Low`, `Close`, `Volume`, `Dividends`, `Stock Splits`), original names — **[CHANGED]** no renaming or column dropping. The only structural step is resetting the `Date` index into a plain column, since Parquet doesn't round-trip a pandas index.
- Implement retry with backoff and timeout handling for the API call.
- Handle a missing-data failure scenario explicitly (e.g. if fewer than 90 rows are returned, or any required column is entirely null) — log this as a DQ warning row (not necessarily a hard failure) via `dq_logger`, and document the decision on whether to proceed or abort.
- On success/failure, log outcome via `dq_logger` (source="YahooFinance_ASX200", row_count, status, message).
- Write raw output to `data/raw/asx200_{run_date}.parquet`.
- Include a `if __name__ == "__main__":` block to run standalone.

**Note on timestamps:** yfinance's index for `^AXJO` is already tz-aware `Australia/Sydney` (verified live), not UTC/US-Eastern as might be assumed for a generic yfinance ticker — left untouched in the raw `Date` column; `align.py` is where that fact should actually get used.

---

## PROMPT 4 — DQ logger utility

*(unchanged)*

Implement `src/ingestion/dq_logger.py`. It must:
- Connect to `data/warehouse.duckdb` and create a `dq_log` table if it doesn't exist, with columns: `run_id` (uuid), `run_timestamp`, `source`, `row_count`, `status` (success/failure/warning), `message`.
- Expose a single function `log_run(source, row_count, status, message=None)` that inserts a row and prints a concise console log line.
- Ensure this module has zero dependency on the extractor modules (extractors import this, not vice versa) to avoid circular imports.

---

## PROMPT 5 — Alignment and timezone handling **[CHANGED]**

**Why this changed:** since Prompts 2 and 3 now write the raw source tables untouched (18 RBA columns, 8 yfinance columns), this step also absorbs the cleaning work that used to happen at ingestion time — column selection and renaming, RBA date-string parsing, and numeric coercion — on top of its original join/timezone/forward-fill scope.

Implement `src/transform/align.py`. It must:
- Load the latest raw RBA and ASX200 Parquet files from `data/raw/`.
- **[NEW]** Select and rename the columns actually needed from each raw source: from RBA, the date column (source header literally `Title`) and `Interbank Overnight Cash Rate` → `date`, `cash_rate`; from ASX200, `Date`, `Open`, `High`, `Low`, `Close`, `Volume` → `date`, `open`, `high`, `low`, `close`, `volume`. Parse the RBA date strings (format `%d-%b-%Y`) and coerce `cash_rate` to numeric; drop rows that fail to parse.
- Normalize both to a common `date` column of type `date` (no time component), explicitly handling: RBA cash rate changes are published as of an effective date in AEST; ASX200 trading data timestamps from yfinance are typically US/Eastern or UTC-based — convert explicitly to AEST calendar dates before joining, and add inline comments explaining the conversion logic and why it matters (avoiding off-by-one-day misalignment). **[NEW]** For this specific pairing, `^AXJO`'s yfinance timestamps are already tz-aware `Australia/Sydney` (verified when building Prompt 3) — so for this ticker there's no actual cross-timezone shift to perform, just a `.dt.date` read of an already-local timestamp; still worth an inline comment so a future source swap doesn't inherit a wrong assumption.
- Since RBA cash rate doesn't change daily, forward-fill the macro series onto every ASX200 trading day (documented as a deliberate design decision, not a bug).
- Outer-join or left-join on `date`, keeping only trading days present in the ASX200 series for the final aligned table.
- Write the aligned result to a DuckDB table `curated.aligned_daily` in `data/warehouse.duckdb`.
- Log the row count and any dropped/unmatched rows via `dq_logger` (status="warning" if any gaps found).

---

## PROMPT 6 — Metrics calculation **[CHANGED]**

**Why this changed:** the case study's AI Agent Lens requirement for this section is specific — *"before using the agent to write the transformation logic, define your metric requirements in plain language. Include this definition in your submission."* The original Prompt 6 had the agent write the plain-language docstring and the code in the same pass, which doesn't actually demonstrate human-first specification — it just produces a docstring that looks human-authored. Fixed by splitting it into two steps.

**Step A (do this first, manually — not a Claude Code prompt):** Write `docs/metric_definitions.md` yourself in plain language, defining the three metrics and the RAG threshold logic, before opening Claude Code for this step. (Draft available in `metric_definitions_draft.md` for you to review/edit — that's the version to paste in.)

**Step B (the actual prompt to Claude Code):**

Implement `src/transform/metrics.py` on top of `curated.aligned_daily`, using the metric definitions in `docs/metric_definitions.md` as the authoritative spec — do not redefine or reinterpret the metrics, implement exactly what's written there. Compute and add as new columns:
1. `rolling_avg_volume_20d` — 20-day rolling average of ASX200 volume.
2. `rate_of_change_pct` — day-over-day percentage change in ASX200 close price.
3. `volatility_14d_annualised` — 14-day rolling standard deviation of log returns of close price, annualised (multiply by sqrt(252)).

Reference `docs/metric_definitions.md` in a comment at the top of the file rather than re-deriving the definitions from scratch.

Write the result to a DuckDB table `curated.metrics_daily`. Also compute a `rag_signal` column: Green if `volatility_14d_annualised` <= 1.5x its own 90-day trailing mean, Amber if between 1.5x-2x, Red if > 2x. Reference the threshold rationale from `docs/metric_definitions.md` in a comment rather than inventing new justification.

---

## PROMPT 7 — Streamlit dashboard **[CHANGED — minor]**

**Why this changed:** the case study defines the dashboard's exact target question — *"how has market activity trended over the past 90 days, and is there anything we should be watching?"* The original prompt didn't require that question to appear anywhere in the UI. A non-technical reader shouldn't have to infer what question they're being answered.

Implement `src/dashboard/app.py`. Requirements:
- Audience: financially literate, non-technical bank management. Minimal jargon, clear titles, one clear takeaway per chart.
- Page title: "Market Intelligence Dashboard — ASX 200 vs RBA Cash Rate"
- **[NEW]** Subtitle directly under the title, verbatim or near-verbatim: "How has market activity trended over the past 90 days, and is there anything we should be watching?" — this is the brief the whole dashboard is answering; make that explicit rather than implicit.
- Section 1: Line chart — ASX200 close price over the last 90 days with the 20-day rolling average volume shown as an overlay or secondary panel (use plotly, not matplotlib).
- Section 2: Macro overlay — dual-axis or stacked chart showing ASX200 close price alongside RBA cash rate over the same 90-day window, with a 1-2 sentence auto-generated text summary noting whether they are currently correlated or diverging (simple rule-based logic on rolling correlation, not ML).
- Section 3: RAG signal — a prominent colored badge/box (green/amber/red) showing current volatility signal, with a short caption explaining the threshold logic in plain English.
- Read data from `curated.metrics_daily` in `data/warehouse.duckdb` via DuckDB's Python connector.
- Add a sidebar note: "Data refreshed: {last run timestamp from dq_log}".
- Keep all chart code self-contained and commented, using plotly with a clean, minimal theme suitable for executive audiences.

---

## PROMPT 8 — Pipeline orchestration script **[CHANGED — minor]**

**Why this changed:** the case study requires ingestion "on a scheduled or repeatable basis." A single manually-run script is repeatable but doesn't demonstrate the "scheduled" half. Adding a README note (see Prompt 10) rather than building actual scheduling infra, since standing up a scheduler is disproportionate to a local case study — but it should at least be *addressed*, not silently dropped.

Create `run_pipeline.py` at the repo root that runs the full pipeline end-to-end in order: RBA extraction → Yahoo extraction → alignment → metrics → prints a summary of DQ log outcomes from this run. This is the single command referenced in the README for "how to run locally". Include clear console output at each stage (using `print` or `logging`) so a non-technical observer can follow progress.

**[NEW]** Also print, at the end of the run, a one-line suggestion: `# To run on a schedule: cron (Linux/Mac) e.g. '0 7 * * 1-5 python run_pipeline.py' or Task Scheduler (Windows)` — this demonstrates the pipeline was designed to be schedulable even though no scheduler is wired up locally.

---

## PROMPT 9 — Tests

*(unchanged)*

Write pytest unit tests for:
- `src/transform/metrics.py` — test rolling average, rate of change, and volatility calculations against a small synthetic DataFrame with known expected outputs.
- `src/transform/align.py` — test that timezone/date alignment correctly forward-fills the macro series and doesn't introduce off-by-one-day errors, using synthetic fixture data.
- `src/ingestion/dq_logger.py` — test that `log_run` correctly inserts a row into a temporary/test DuckDB file.

---

## PROMPT 10 — README **[CHANGED — minor]**

**Why this changed:** the case study's actual submission line is *"GitHub repo, plus dashboard link. README must include set up steps, key design decisions, a brief note on how you would hand the work to a team member, and an agent log summarising your AI tool use."* That's slightly different wording/emphasis than the original prompt's section list — added the two things called out explicitly (handoff note, agent log) as their own required lines rather than folding them into generic headers.

Write the full `README.md` including:
- Overview of the platform and business question it answers (90-day market trend + macro watch-points).
- Setup steps (venv, pip install -r requirements.txt).
- Run instructions: `python run_pipeline.py` then `streamlit run src/dashboard/app.py`.
- Architecture description (raw → DQ log → transform/align → metrics → dashboard), referencing the layer separation.
- Key design decisions: source choice rationale, metric definitions (plain language, link to `docs/metric_definitions.md`), RAG threshold rationale, timezone handling approach.
- Data quality notes: the one real DQ issue encountered and how it was fixed (fill in after running the pipeline and reviewing actual output/logs — must be a real issue, not a hypothetical one).
- **[NEW]** A one-line link to the GitHub repo and to the dashboard/how to view it (satisfies the literal submission line, not just "runs locally").
- AI Agent Log: which files were AI-generated vs. human-reviewed/modified, and **one specific example of an incorrect or incomplete AI output that was caught and corrected** (fill in based on actual build experience — this is explicitly graded; don't skip it even if nothing went wrong, keep an eye out during the actual build for something to report honestly).
- Handoff notes: what a junior engineer would need to know to maintain/extend this (coding standards, where to add a new source, how DQ logging works, guardrails for AI-assisted changes) — **[NEW]** frame this section so it can be lifted near-verbatim into the presentation's required "pipeline walkthrough / handoff approach" section, since the case study asks for this content twice (once in README, once live in the presentation).

---

## PROMPT 11 — Error scenario test / demo

*(unchanged)*

Add a small script `scripts/simulate_failure.py` that deliberately breaks one extractor (e.g. points to an invalid URL or malformed date) to demonstrate the failure-handling and DQ logging behavior end-to-end. This is for the presentation demo of the "handle at least one failure scenario" requirement — make it easy to run and show the DQ log capturing the failure gracefully rather than crashing silently.

---

## Out of scope for these prompts **[NEW]**

These are graded parts of the case study that this file does not produce. Flagging so they don't get lost:

1. **The Presentation itself** (≤20 min: framing, pipeline walkthrough, data decisions, dashboard demo, AI agent reflection, team & standards, "if I had more time"). The README's Architecture, Design Decisions, and Handoff sections (Prompt 10) are written to be reusable as presentation content, but the deck/talk itself is a separate build.
2. **The optional bonus slide** (data product owner partnership, concept-to-delivery process, influencing with data). One slide, not assessed, but worth doing if time allows — it's a leadership-lens question the JD leans on heavily (Product Analytics Architecture mandate).
3. **Actually deploying** the dashboard for a live link, versus a local `streamlit run` demo — confirm which the submission needs before the deadline.
