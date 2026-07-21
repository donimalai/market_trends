"""
app.py

Streamlit dashboard: "Market Intelligence Dashboard — ASX 200 vs RBA Cash Rate"

Audience: financially literate, non-technical bank management. Answers:
"How has market activity trended over the past 90 days, and is there
anything we should be watching?" — that question should appear directly
in the UI, not just be implied.

Responsibilities (to be implemented):
- Section 1: ASX200 close price (90d) + 20-day rolling avg volume overlay
  (plotly).
- Section 2: Macro overlay — close price vs RBA cash rate (90d), with a
  1-2 sentence rule-based summary (rolling correlation) noting correlation
  or divergence.
- Section 3: RAG signal badge (green/amber/red) with plain-English caption
  on the threshold logic.
- Reads from curated.metrics_daily in data/warehouse.duckdb via DuckDB's
  Python connector.
- Sidebar note: "Data refreshed: {last run timestamp from dq_log}".

NOT YET IMPLEMENTED — scaffold only.
"""

import streamlit as st

st.set_page_config(page_title="Market Intelligence Dashboard", layout="wide")
st.title("Market Intelligence Dashboard — ASX 200 vs RBA Cash Rate")
st.caption("How has market activity trended over the past 90 days, and is there anything we should be watching?")
st.info("Dashboard not yet implemented — scaffold only.")
