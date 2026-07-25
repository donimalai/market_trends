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

# --- KPI row + bottom-line summary ---
# Answers the subtitle's question directly, in numbers, rather than making
# the viewer eyeball a chart and do the arithmetic themselves.
period_pct_change = (window["close"].iloc[-1] - window["close"].iloc[0]) / window["close"].iloc[0] * 100
period_high = window["close"].max()
period_low = window["close"].min()
latest_close = window["close"].iloc[-1]
latest_move_pct = latest["rate_of_change_pct"]
latest_date_str = latest["date"].strftime("%d %b %Y")
rag = latest["rag_signal"]

with st.container(horizontal=True):
    st.metric(
        f"Latest close ({latest_date_str})",
        f"{latest_close:,.0f}",
        f"{latest_move_pct:+.2f}% today" if pd.notna(latest_move_pct) else None,
        border=True,
    )
    st.metric(f"{len(window)}-day change", f"{period_pct_change:+.1f}%", border=True)
    # UX fix (analyst feedback #4): raw absolute values aren't intuitively
    # "wide" or "narrow" to a non-technical viewer -- add the range as a
    # +/- percentage of the current price so it's readable without mental
    # math. delta_color="off" since a wider/narrower band isn't inherently
    # good or bad, so it shouldn't be colored green/red like a normal delta.
    band_half_width_pct = (period_high - period_low) / 2 / latest_close * 100
    st.metric(
        f"{len(window)}-day range",
        f"{period_low:,.0f} – {period_high:,.0f}",
        f"±{band_half_width_pct:.1f}% band",
        delta_color="off",
        border=True,
    )
    st.metric("Volatility signal", rag if pd.notna(rag) else "Not yet available", border=True)

# Rule-based, not ML -- same style as the correlation summary in Section 2.
direction = "up" if period_pct_change > 0.5 else "down" if period_pct_change < -0.5 else "roughly flat"
vol_clause = {
    "Green": "with normal volatility",
    "Amber": "with elevated volatility — worth monitoring",
    "Red": "with high volatility — an active watch item",
    "insufficient signal": "though the volatility signal is currently unreliable (unusually calm baseline)",
}.get(rag, "with volatility not yet assessable (insufficient trading history)")

rate_changes_in_window = window["cash_rate"].dropna().diff().fillna(0)
num_rate_changes = int((rate_changes_in_window != 0).sum())
rate_clause = (
    f", against {num_rate_changes} RBA rate change{'s' if num_rate_changes != 1 else ''} this period"
    if num_rate_changes
    else ""
)

st.info(
    f"**Bottom line:** ASX 200 is {direction} "
    f"({abs(period_pct_change):.1f}%) over the past {len(window)} trading days, "
    f"{vol_clause}{rate_clause}."
)

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
    margin=dict(l=40, r=20, t=50, b=20),
)
# UX fix (analyst feedback #2a): force the subplot title font size/margin
# explicitly -- Plotly's automatic subplot_titles sizing was letting the
# second title get clipped at some viewport widths.
fig1.update_annotations(font_size=14)
fig1.update_yaxes(title_text="Price (points)", row=1, col=1)
fig1.update_yaxes(title_text="Shares traded", row=2, col=1)
# UX fix (analyst feedback #2b): cap the volume axis at a percentile-based
# ceiling instead of the raw max -- a couple of extreme spikes were
# stretching the axis so far that the 20-day rolling-average line read as
# nearly flat. Bars taller than the cap simply extend past the visible
# top (still visible as "very high"), while the rolling average keeps
# its actual shape within a sensible range.
volume_cap = window["volume"].quantile(0.95) * 1.25
fig1.update_yaxes(range=[0, volume_cap], row=2, col=1)
st.plotly_chart(fig1, width="stretch")

# --- Section 2: macro overlay (DASH-3) ---
# ASX 200 stays on the primary (left) axis; RBA cash rate gets its own
# secondary (right) axis rather than being rescaled onto the price axis --
# each series is readable in its native units (points vs. %) without
# either one needing mental rescaling. Rendered as a step line ("hv"
# shape), not a straight interpolation, since the cash rate is genuinely
# constant between RBA decisions and jumps discretely on a change -- a
# straight line between two rate points would visually imply a gradual
# move that never happened.
st.header("Macro overlay: ASX 200 vs RBA cash rate")
fig2 = go.Figure()
fig2.add_trace(
    go.Scatter(
        x=window["date"], y=window["close"], name="ASX 200 close",
        line=dict(color="#1f77b4", width=2), yaxis="y1",
    )
)
fig2.add_trace(
    go.Scatter(
        x=window["date"], y=window["cash_rate"], name="RBA cash rate",
        line=dict(color="#e07b39", width=2, shape="hv"), yaxis="y2",
    )
)

fig2.update_layout(
    height=380, template="plotly_white", margin=dict(l=40, r=50, t=30, b=20), showlegend=True,
    yaxis=dict(title="ASX 200 close price"),
    yaxis2=dict(title="RBA cash rate (%)", overlaying="y", side="right", showgrid=False),
)
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

# History strip -- the badge above only shows *today's* state; this answers
# "how long has it been this color" at a glance, which matters for "is
# there anything to watch" (a signal that just turned Green reads very
# differently from one that's been Green for months).
STRIP_COLORS = {
    "Green": "#1e7e34",
    "Amber": "#b26a00",
    "Red": "#c62828",
    "insufficient signal": "#888888",
}
strip_colors = window["rag_signal"].map(STRIP_COLORS).fillna("#e0e0e0")
strip_fig = go.Figure(
    go.Bar(
        x=window["date"],
        y=[1] * len(window),
        marker_color=strip_colors,
        hovertext=window["rag_signal"].fillna("Not yet available"),
        hoverinfo="text+x",
        showlegend=False,
    )
)
strip_fig.update_layout(
    height=70,
    template="plotly_white",
    margin=dict(l=40, r=40, t=10, b=20),
    yaxis=dict(visible=False),
    bargap=0,
)
st.caption(f"Signal history — last {len(window)} trading days")

# UX fix (analyst feedback #3): colour-only encoding forced the viewer to
# read the paragraph above to decode green vs. grey. Add a compact inline
# swatch legend directly above the strip so it's self-explanatory on its own.
_legend_items = [
    ("#1e7e34", "Green — normal"),
    ("#b26a00", "Amber — elevated"),
    ("#c62828", "Red — high"),
    ("#888888", "Insufficient signal"),
    ("#e0e0e0", "Not yet available"),
]
_legend_html = "&nbsp;&nbsp;&nbsp;".join(
    f'<span style="display:inline-block;width:10px;height:10px;background-color:{color};'
    f'border-radius:2px;margin-right:4px;vertical-align:middle;"></span>'
    f'<span style="font-size:13px;">{label}</span>'
    for color, label in _legend_items
)
st.markdown(_legend_html, unsafe_allow_html=True)
st.plotly_chart(strip_fig, width="stretch")
