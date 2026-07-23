"""
app.py

Entry point for the Streamlit app — routes between two pages via
st.navigation:
- Market overview (app_pages/market_overview.py): the required case-study
  dashboard (DASH-1..4).
- Data statistics & quality (app_pages/data_quality.py): pipeline/table
  row counts and the latest outcome of every dq_log / dq_validation_log
  entry, i.e. the DQ dashboard those tables were built to support.

Run: streamlit run src/dashboard/app.py
"""

import streamlit as st

st.set_page_config(page_title="Market Intelligence Dashboard", layout="wide")

page = st.navigation(
    [
        st.Page(
            "app_pages/market_overview.py",
            title="Market overview",
            icon=":material/monitoring:",
        ),
        st.Page(
            "app_pages/data_quality.py",
            title="Data statistics & quality",
            icon=":material/fact_check:",
        ),
    ]
)
page.run()
