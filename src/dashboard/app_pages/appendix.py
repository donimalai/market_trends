"""
appendix.py

Third dashboard page: a plain-language explainer for the Market overview
page — what each measure means, why those specific windows/thresholds
were chosen, how data quality is handled, and the assumptions behind the
platform. Static/explanatory content, not live query results (that's the
Data statistics & quality page). Content mirrors docs/metric_definitions.md
so there's one source of truth, not two slightly-different explanations.
"""

import streamlit as st

st.title("Appendix: how to read this dashboard")
st.caption(
    "What each measure means, why these specific windows and thresholds were chosen, "
    "and how data quality is handled — for anyone new to the dashboard, with extra "
    "methodology detail below for analysts reviewing or extending it."
)

st.header("The measures, at a glance")
st.dataframe(
    {
        "Measure": [
            "Rolling average volume",
            "Rate of change",
            "14-day volatility (annualised)",
            "RAG signal",
        ],
        "Window": ["20 trading days (~1 month)", "1 day (day-over-day)", "14 trading days", "14-day volatility vs. its own 90-day average"],
        "What it measures": [
            "Smoothed daily trading volume — a proxy for market participation/liquidity",
            "% change in the closing price vs. the previous trading day",
            "How much the price has been swinging recently, expressed as a single comparable number",
            "A Green/Amber/Red flag on current market turbulence",
        ],
    },
    hide_index=True,
    width="stretch",
)

st.header("14-day volatility, briefly")
st.markdown(
    "Price direction alone doesn't say anything about risk — two markets can end up at the "
    "same price having gotten there smoothly, or via wild swings. Volatility captures that "
    "difference. It's calculated from the day-to-day % changes in price over the trailing "
    "14 trading days, turned into a single annualised number so it's comparable over time "
    "(the market-standard way of doing this is to multiply by the square root of 252, the "
    "approximate number of trading days in a year). Higher = more turbulent over the last "
    "two weeks; it says nothing about *direction*, only about how bumpy the ride has been."
)

st.header("The RAG signal's logic")
st.markdown(
    "- 🟢 **Green** — current 14-day volatility is at or below 1.5× its own 90-day trailing average\n"
    "- 🟡 **Amber** — above 1.5× and up to 2.0×\n"
    "- 🔴 **Red** — above 2.0×\n\n"
    "This compares today's volatility to the market's **own recent average**, rather than a fixed "
    "number like \"20% = red\". A fixed threshold would need constant re-tuning and ages badly — "
    "what counted as \"high\" volatility a decade ago is unremarkable today. Comparing to a "
    "rolling baseline instead flags *regime shifts*, which is what's actually useful for an "
    "early warning. The honest tradeoff: this is backward-looking, so it can't catch the very "
    "first day something unusual starts, and it gets less sensitive for a while right after a "
    "genuinely volatile stretch, since the 90-day average itself will have risen.\n\n"
    "Two extra states beyond the traffic light: **\"not yet available\"** (needs about 5 months "
    "of trading history before the first signal can be produced — both the 14-day figure and a "
    "90-day average of *that* figure have to build up first), and **\"insufficient signal\"** "
    "(shown instead of a ratio during an unusually calm stretch, where the math could otherwise "
    "produce a misleadingly alarming reading)."
)

st.header("Data sources")
st.markdown(
    "- **ASX 200 price/volume** — Yahoo Finance (`^AXJO`), a free public feed, not a paid/licensed "
    "exchange data source. Fine for internal monitoring; not a source of record for anything "
    "needing an audited feed.\n"
    "- **Macro overlay** — RBA Cash Rate Target (the officially announced policy rate), the only "
    "macro series shown, per the brief's \"your macro data series\" (singular)."
)

st.header("How data quality is handled")
st.markdown(
    "Every pipeline stage logs its outcome — success, warning, or failure — so nothing fails "
    "silently. On top of that, both source datasets go through a full validation suite (13 checks "
    "combined: completeness, valid ranges/values, internal consistency, duplicates, freshness, "
    "and a few source-specific checks) before they're used. **Rows that fail a critical check are "
    "quarantined** — held in a separate table with the specific reason — rather than silently "
    "dropped or allowed to break the rest of the pipeline. Rows that only trigger a warning "
    "(unusual but not necessarily wrong) stay in, tagged with why. See the **Data statistics & "
    "quality** tab for the live, current numbers behind all of this."
)

st.subheader("The 13 checks, in full")
st.dataframe(
    {
        "Dataset": ["RBA Cash Rate"] * 6 + ["ASX 200"] * 7,
        "Check": [
            "completeness",
            "valid_range",
            "internal_consistency",
            "freshness",
            "no_duplicates",
            "unusual_movement",
            "completeness",
            "valid_values",
            "internal_consistency",
            "no_duplicates",
            "freshness",
            "index_composition",
            "missing_or_zero_close",
        ],
        "What it verifies": [
            "Every RBA business day has a record — gaps are flagged, not assumed benign",
            "Cash Rate Target sits within 0–15% and moves in multiples of 0.05%",
            "The recorded \"Change in the Cash Rate Target\" matches the actual difference from the previous rate",
            "Most recent record is no more than ~3 calendar days old",
            "No effective date appears twice with conflicting rate values",
            "Flags single-day rate moves bigger than 0.50% (unusual, not necessarily wrong)",
            "Every ASX200 business day has a record — gaps are flagged (most are public holidays)",
            "Low ≤ Open/Close/High; High ≥ Open/Close/Low; Close > 0; Volume ≥ 0",
            "Flags a day-over-day price change bigger than 15%",
            "No trading date appears twice with conflicting OHLCV values",
            "Latest record is no more than 1 business day behind today",
            "Number of companies in the index — **not applicable**: the current source (Yahoo Finance OHLCV) carries no constituent-count field, logged explicitly rather than silently skipped",
            "Close price is not missing or zero on a trading day",
        ],
    },
    hide_index=True,
    width="stretch",
)
st.caption(
    "6 checks on RBA Cash Rate, 7 on ASX 200 — 13 total. Source: `src/transform/silver_builder.py` "
    "(`_validate_rba` / `_validate_asx200`), logged live to `dq_validation_log` on every pipeline run."
)

st.header("Market overview: design choices worth knowing")
st.markdown(
    "**KPI row + bottom-line summary** — the four cards (latest close, N-day change, "
    "N-day range, volatility signal) and the auto-generated sentence beneath them are "
    "rule-based, not ML or LLM-generated: period % change is "
    "`(last close − first close) / first close`, the range delta is "
    "`±(high − low) / 2 / latest close`, and the bottom-line sentence concatenates the "
    "direction, the current RAG state, and a count of RBA rate changes within the "
    "visible window — plain arithmetic and string templates, fully reproducible from "
    "`curated.metrics_daily`.\n\n"
    "**Macro overlay is single-axis, not dual-axis.** ASX 200 close is the only line; "
    "the RBA cash rate is shown as shaded background bands, one per rate level, each "
    "labeled with the rate. An earlier version used two lines on two independent scales "
    "(price in thousands, rate in single digits) — reconciling two axes took more "
    "deliberate reading than a glance should require. One caveat worth knowing: bands "
    "narrower than 5 trading days (a rate change landing only a couple of days into the "
    "visible window) are shaded but left unlabeled, to avoid two adjacent labels "
    "overlapping — the correlation sentence below the chart still accounts for every "
    "change, labeled or not, since it's computed from the full `cash_rate` series, not "
    "from the chart's annotations.\n\n"
    "**Volatility signal history strip** — the badge above shows only *today's* state; "
    "the strip below it repeats the same Green/Amber/Red/grey classification for every "
    "day in the visible window, so \"how long has it been this color\" is answerable at "
    "a glance rather than requiring a query. The legend above the strip uses the exact "
    "same hex values as the strip and the main badge — not a separate approximation."
)

st.header("Data statistics & quality: how to read it")
st.markdown(
    "**Status badges** (🟢/🟡/🔴/⚪) map directly from the `status` column already "
    "written by the pipeline — `dq_log` (success/warning/failure) and "
    "`dq_validation_log` (pass/warning/fail/not_applicable) — no severity is re-inferred "
    "or reclassified for display; the color is exactly what was logged at run time.\n\n"
    "**A \"warning\" is not a partial failure.** For most checks it means something was "
    "flagged but the rows were kept, not dropped. Completeness warnings are the clearest "
    "case: 0 rows failed, N business days simply had no record — most likely a public "
    "holiday neither source publishes on. The expander directly above the checks table "
    "spells out the exact trigger for every status, per check.\n\n"
    "**`index_composition` always reads `not_applicable`, deliberately.** The current "
    "ASX200 source (Yahoo Finance OHLCV) has no \"number of companies in the index\" "
    "field at all — this isn't a disabled or placeholder check, it's a documented "
    "limitation that would need a different data source to actually enforce. Kept "
    "visible in the table rather than removed, so the gap doesn't silently disappear.\n\n"
    "**The DQ trend chart buckets runs by the minute.** `dq_validation_log` stamps each "
    "of the ~13 checks with its own `datetime.now()`, milliseconds apart within one "
    "pipeline execution — grouping by `date_trunc('minute', run_timestamp)` clusters a "
    "single run's checks together without needing a dedicated run-id column. Reasonable "
    "given this pipeline runs well under a minute end to end, but worth revisiting if "
    "two runs could ever start within the same 60-second window.\n\n"
    "**The quarantine worked example is a synthetic test case, not a historical event.** "
    "The real pipeline has quarantined 0 rows in every run so far, so there's no genuine "
    "historical example available. Instead, the dashboard takes real recent ASX200 rows, "
    "appends one deliberately invalid row (`Low` set above `High` — an impossible OHLC "
    "state), and runs the batch through the actual `_validate_asx200()` function "
    "imported from `silver_builder.py`. The reason text shown is that function's real "
    "output, not hand-written copy — it demonstrates the mechanism by executing it, and "
    "should not be read as evidence the real data has ever actually failed this way."
)

st.header("Assumptions behind this build")
st.markdown(
    "A few judgment calls were made where the brief didn't specify an exact answer — flagging "
    "them here rather than leaving them invisible:\n\n"
    "1. Rolling average volume uses a 20-day window — not specified in the brief; chosen as a "
    "common ~monthly convention (long enough to smooth noise, short enough to stay responsive).\n"
    "2. The RAG signal's 90-day baseline is a simple average, not weighted or smoothed.\n"
    "3. Annualisation uses 252 trading days/year, the standard market convention.\n"
    "4. Warm-up periods (not enough history yet for a given measure) are left as genuine gaps, "
    "never backfilled or estimated.\n"
    "5. The cash rate shown is the RBA's **Cash Rate Target** (the officially announced rate), "
    "not the Interbank Overnight Cash Rate — the two track closely but aren't identical.\n"
    "6. \"Past 90 days\" means the last 90 **trading** rows, not the last 90 calendar days.\n"
    "7. Data-completeness checks are business-day-based; a missing weekday is reported as a gap "
    "since there's no external public-holiday calendar to tell an expected closure apart from a "
    "real data problem.\n"
    "8. Macro overlay bands narrower than 5 trading days are shaded but left unlabeled, to avoid "
    "adjacent labels overlapping on a narrow band.\n"
    "9. The DQ trend view groups checks into \"runs\" by rounding `run_timestamp` to the nearest "
    "minute — holds for this pipeline's sub-minute runtime, not a general-purpose run identifier.\n\n"
    "Full detail and rationale for all of the above: `docs/metric_definitions.md`."
)
