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
    "and how data quality is handled — for anyone new to the dashboard."
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
    "real data problem.\n\n"
    "Full detail and rationale for all of the above: `docs/metric_definitions.md`."
)
