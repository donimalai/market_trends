# Prompt Specification — Data Curation & Management Dashboard

Derived directly from the case study brief's "Data Curation" and "Management Dashboard" sections (verbatim requirements quoted below, each traced to the prompt requirement it produces). Purpose: make sure the actual Claude Code prompts are requirement-complete against the rubric text itself, not a paraphrase of it — same discipline as `requirement_specification.md` applied to ingestion. Cross-check against Prompts 5–7 in `claude_code_build_prompts_refined.md`; this file is the traceability layer underneath those.

---

## Source: case study text (verbatim)

**Data Curation**
> Build two or three calculated metrics (e.g. rolling average volume, rate of change, or a 14 day volatility measure)
> Join or align the two sources on a common time axis. You must handle date and timezone differences explicitly.
> Document one data quality issue you encountered and how you fixed it.

*AI Agent Lens:* If you are using an AI agent – before using the agent to write the transformation logic, define your metric requirements in plain language. Include this definition in your submission.
*Leadership Lens:* Be ready to discuss how you would set and enforce data modelling standards.

**Management Dashboard**
> The target audience for your dashboard are financially literate but non-technical users. The dashboard should answer "how has market activity trended over the past 90 days, and is there anything we should be watching?"
> The dashboard must include:
> - Index volume or price over 90 days, with a rolling average overlay
> - Macro overlay – your macro data series alongside market data. Show any correlation or divergence
> - One signal – Red/Amber/Green signal based on a threshold you define and justify

*AI Agent Lens:* You may use an agent to generate dashboard code. Note how you iterated on the prompt or output to ensure appropriateness for the intended audience.
*Leadership Lens:* Discuss how you would help a team of analysts present information that helps convey a story or message.

---

## Requirement Traceability

| Rubric line | Requirement ID | Where it's satisfied |
|---|---|---|
| "two or three calculated metrics" | DC-1 | 3 metrics defined in `docs/metric_definitions.md`, implemented in `metrics.py` |
| "Join or align the two sources on a common time axis" | DC-2 | `align.py` |
| "handle date and timezone differences explicitly" | DC-3 | `align.py`, commented inline |
| "Document one data quality issue you encountered and how you fixed it" | DC-4 | README "Data Quality Notes" — **must be a real issue from the actual build, not invented** |
| "define your metric requirements in plain language...before using the agent" | DC-5 | `docs/metric_definitions.md`, authored before `metrics.py` is prompted (see Prompt 6 Step A/B split) |
| "set and enforce data modelling standards" (Leadership Lens) | DC-6 | Not code — presentation talking point. See note at bottom. |
| "answer 'how has market activity trended...'" | DASH-1 | Literal subtitle text in `app.py` |
| "Index volume or price over 90 days, with a rolling average overlay" | DASH-2 | Dashboard Section 1 |
| "Macro overlay...show any correlation or divergence" | DASH-3 | Dashboard Section 2 |
| "Red/Amber/Green signal based on a threshold you define and justify" | DASH-4 | Dashboard Section 3 + plain-English caption |
| "note how you iterated on the prompt or output" (AI Agent Lens) | DASH-5 | Not code — process log entry. See note at bottom. |
| "help a team of analysts present information...convey a story" (Leadership Lens) | DASH-6 | Not code — presentation talking point. See note at bottom. |

Six of the twelve rubric lines (DC-6, DASH-5, DASH-6, and the two Leadership Lens items) are not satisfiable by a code prompt at all — they're process/discussion requirements. Flagging that explicitly so "the prompt ran successfully" doesn't get mistaken for "the requirement is met." These are logged in `ai_agent_process_log.md` and need to surface in the presentation, not the codebase.

---

## PROMPT — Data Curation (metrics + alignment)

*Precondition (DC-5): `docs/metric_definitions.md` must already be filled in with the approved plain-language definitions before this prompt is run — do not let the agent write both the definitions and the implementation in the same pass. If that file is still a placeholder, stop and fill it in first.*

```
Implement src/transform/align.py and src/transform/metrics.py.

align.py (DC-2, DC-3):
- Load the latest raw RBA and ASX200 Parquet files from data/raw/.
- Select and rename only the columns needed (see docs/requirement_specification.md
  section 3 for what each raw source actually contains).
- Explicitly convert both series to a common `date` axis in AEST calendar-date terms.
  RBA cash rate is published as of an AEST effective date. ASX200 timestamps from
  yfinance for ^AXJO are tz-aware Australia/Sydney (verified — see
  requirement_specification.md section 2.2), so no UTC conversion is actually needed,
  but this fact must be stated explicitly in a comment rather than assumed silently,
  since it is not true for yfinance tickers in general.
- Forward-fill the RBA cash rate onto every ASX200 trading day (documented as
  deliberate, not a bug, since cash rate doesn't change daily).
- Left-join on `date`, keeping only ASX200 trading days in the final table.
- Write to DuckDB table curated.aligned_daily.
- Log row count and any dropped/unmatched rows via dq_logger (status="warning" if
  gaps found).

metrics.py (DC-1, DC-5):
- Implement exactly the three metrics and the RAG threshold logic specified in
  docs/metric_definitions.md — do not redefine or reinterpret them.
- Write to DuckDB table curated.metrics_daily.
- Reference docs/metric_definitions.md in a comment at the top of the file rather
  than re-deriving the definitions from scratch.

Do not fabricate a data quality issue for the README — DC-4 gets filled in after
this prompt runs, based on whatever actually goes wrong (or doesn't) when it's
run against real data.
```

---

## PROMPT — Management Dashboard

```
Implement src/dashboard/app.py as a Streamlit app for financially literate,
non-technical bank management.

- Page title: "Market Intelligence Dashboard — ASX 200 vs RBA Cash Rate"
- Subtitle, verbatim (DASH-1): "How has market activity trended over the past
  90 days, and is there anything we should be watching?" — this is the exact
  question being answered; state it, don't imply it.
- Section 1 (DASH-2): ASX200 close price over the last 90 days, with the
  20-day rolling average volume shown as an overlay or secondary panel.
  Use plotly, not matplotlib.
- Section 2 (DASH-3): Macro overlay — ASX200 close price alongside RBA cash
  rate over the same 90-day window (dual-axis or stacked). Include a 1-2
  sentence auto-generated summary noting whether they're currently
  correlated or diverging — simple rule-based logic on rolling correlation,
  not ML.
- Section 3 (DASH-4): RAG signal as a prominent colored badge (green/amber/red)
  showing the current volatility signal, with a short caption in plain English
  explaining the threshold logic (pull the justification from
  docs/metric_definitions.md section 4 — don't re-justify it differently here).
- Read data from curated.metrics_daily in data/warehouse.duckdb via DuckDB's
  Python connector — no other table.
- Sidebar note: "Data refreshed: {last run timestamp from dq_log}".
- Self-contained, commented chart code, clean minimal theme suitable for an
  executive audience — no jargon in labels or titles.
```

**DASH-5 note (not part of the prompt itself):** whatever gets changed between the first version of this prompt's output and what actually ships — chart type swapped, copy simplified, a section reordered because a first draft buried the RAG signal below the fold, etc. — log it as an entry in `ai_agent_process_log.md`. That log entry *is* the answer to "note how you iterated on the prompt or output to ensure appropriateness for the intended audience." Don't let this happen invisibly.

---

## Non-code requirements this file does not produce

- **DC-6 / DASH-6 (Leadership Lens):** "how would you set and enforce data modelling standards" and "how would you help a team of analysts present information that conveys a story" are presentation talking points, not implementation work. Draft these as part of the "Team and standards" presentation section, informed by the actual delegation pattern already forming in `ai_agent_process_log.md`'s work-breakdown table.
- **DC-4:** the one real data-quality issue for the README must come from an actual pipeline run, not be pre-written here.
