"""
market_overview.py

Market Intelligence Dashboard page: "Market Intelligence Dashboard — ASX 200 vs RBA Cash Rate"

Audience: financially literate, non-technical bank management. Answers:
"How has market activity trended over the past 90 days, and is there
anything we should be watching?" — stated directly in the UI, not implied.

Reads only curated.metrics_daily for chart/metric content (per spec), plus
dq_log separately for the sidebar's last-refresh timestamp (its own,
explicitly named requirement). Both via a read-only DuckDB connection, so
the dashboard never competes for a write lock with the pipeline.
"""

import sys
from pathlib import Path

import duckdb
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingestion import dq_logger

DISPLAY_WINDOW_DAYS = 90

RAG_BADGE_STYLE = {
    "Green": ("#e6f4ea", "#1e7e34", "GREEN — normal volatility"),
    "Amber": ("#fff8e1", "#b26a00", "AMBER — elevated volatility, worth watching"),
    "Red": ("#fdecea", "#c62828", "RED — high volatility, active concern"),
    "insufficient signal": (
        "#f1f1f1",
        "#555555",
        "INSUFFICIENT SIGNAL — recent volatility too low to assess reliably",
    ),
}


@st.cache_data
def load_metrics() -> pd.DataFrame:
    con = duckdb.connect(str(dq_logger.DB_PATH), read_only=True)
    try:
        df = con.execute("SELECT * FROM curated.metrics_daily ORDER BY date").fetchdf()
    finally:
        con.close()
    df["date"] = pd.to_datetime(df["date"])
    return df


@st.cache_data
def load_last_refresh() -> str:
    con = duckdb.connect(str(dq_logger.DB_PATH), read_only=True)
    try:
        ts = con.execute("SELECT MAX(run_timestamp) FROM dq_log").fetchone()[0]
    finally:
        con.close()
    return ts.strftime("%Y-%m-%d %H:%M:%S") if ts is not None else "unknown"


metrics = load_metrics()
window = metrics.tail(DISPLAY_WINDOW_DAYS).copy()
latest = metrics.iloc[-1]

# --- Header ---
st.title("Market Intelligence Dashboard — ASX 200 vs RBA Cash Rate")
st.caption(
    "How has market activity trended over the past 90 days, "
    "and is there anything we should be watching?"
)
st.sidebar.markdown(f"**Data refreshed:** {load_last_refresh()}")

# --- Section 1: market activity (DASH-2) ---
# Price and volume are shown as two stacked panels, not one dual-axis chart
# -- price (~thousands) and volume (~hundreds of thousands) are different
# enough in scale that cramming both onto one axis would make one series
# unreadable. "Secondary panel" is explicitly offered as the alternative to
# "overlay" in the spec.
st.header("Market activity")
fig1 = make_subplots(
    rows=2,
    cols=1,
    shared_xaxes=True,
    row_heights=[0.65, 0.35],
    vertical_spacing=0.08,
    subplot_titles=("ASX 200 close price", "Volume, with 20-day rolling average"),
)
fig1.add_trace(
    go.Scatter(
        x=window["date"], y=window["close"], mode="lines",
        name="Close price", line=dict(color="#1f77b4", width=2),
    ),
    row=1, col=1,
)
fig1.add_trace(
    go.Bar(
        x=window["date"], y=window["volume"], name="Daily volume",
        marker_color="#d3d3d3", opacity=0.7,
    ),
    row=2, col=1,
)
fig1.add_trace(
    go.Scatter(
        x=window["date"], y=window["rolling_avg_volume_20d"], mode="lines",
        name="20-day avg volume", line=dict(color="#ff7f0e", width=2),
    ),
    row=2, col=1,
)
fig1.update_layout(
    height=500, showlegend=True, template="plotly_white",
    margin=dict(l=40, r=20, t=40, b=20),
)
fig1.update_yaxes(title_text="Price (points)", row=1, col=1)
fig1.update_yaxes(title_text="Shares traded", row=2, col=1)
st.plotly_chart(fig1, width="stretch")

# --- Section 2: macro overlay (DASH-3) ---
# Dual-axis here is the spec's own explicit suggestion, and is the
# legitimate case for it -- price and a policy rate are always on very
# different scales, and the whole point of this chart is to see both move
# (or not move) together over the same dates.
st.header("Macro overlay: ASX 200 vs RBA cash rate")
fig2 = make_subplots(specs=[[{"secondary_y": True}]])
fig2.add_trace(
    go.Scatter(
        x=window["date"], y=window["close"], name="ASX 200 close",
        line=dict(color="#1f77b4", width=2),
    ),
    secondary_y=False,
)
fig2.add_trace(
    go.Scatter(
        x=window["date"], y=window["cash_rate"], name="RBA cash rate (%)",
        line=dict(color="#2ca02c", width=2, dash="dot"),
    ),
    secondary_y=True,
)
fig2.update_layout(height=380, template="plotly_white", margin=dict(l=40, r=40, t=20, b=20))
fig2.update_yaxes(title_text="ASX 200 close price", secondary_y=False)
fig2.update_yaxes(title_text="Cash rate (%)", secondary_y=True)
st.plotly_chart(fig2, width="stretch")

# Auto-generated summary -- simple rule-based correlation, not ML. Guarded
# against a near-constant cash rate (common -- RBA holds for months at a
# time), which would otherwise make the correlation degenerate/near-random.
valid = window.dropna(subset=["close", "cash_rate"])
if len(valid) < 10 or valid["cash_rate"].std() < 1e-6:
    summary = (
        "The RBA cash rate has been unchanged over this window, so no meaningful "
        "correlation with market moves can be assessed."
    )
else:
    corr = valid["close"].corr(valid["cash_rate"])
    if corr > 0.3:
        summary = (
            f"Over the past {len(window)} trading days, ASX 200 and the RBA cash rate "
            f"have moved together (correlation ≈ {corr:.2f}) — both trending in the same direction."
        )
    elif corr < -0.3:
        summary = (
            f"Over the past {len(window)} trading days, ASX 200 and the RBA cash rate "
            f"have been diverging (correlation ≈ {corr:.2f}) — moving in opposite directions."
        )
    else:
        summary = (
            f"Over the past {len(window)} trading days, ASX 200 and the RBA cash rate show "
            f"little relationship (correlation ≈ {corr:.2f}) — market moves have not tracked "
            "rate changes closely in this window."
        )
st.caption(summary)

# --- Section 3: RAG signal (DASH-4) ---
st.header("Volatility signal")
rag = latest["rag_signal"]
vol = latest["volatility_14d_annualised"]

if pd.isna(rag):
    st.info(
        "RAG signal not yet available — needs roughly 104 trading days of history to "
        "compute (see docs/metric_definitions.md)."
    )
else:
    bg, fg, label = RAG_BADGE_STYLE.get(rag, ("#f1f1f1", "#555555", str(rag)))
    st.markdown(
        f'<div style="background-color:{bg}; color:{fg}; padding:16px 24px; '
        f'border-radius:8px; font-size:20px; font-weight:600;">{label}</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        f"Current 14-day annualised volatility: {vol:.1%}. Green = at or below 1.5x its own "
        "90-day trailing average; Amber = above 1.5x and up to 2.0x; Red = above 2.0x. Comparing "
        "today's volatility to the market's own recent average flags regime shifts without needing "
        "an externally sourced 'normal' baseline (see docs/metric_definitions.md section 4)."
    )
