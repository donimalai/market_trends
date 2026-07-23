"""
data_quality.py

Second dashboard page: pipeline/table statistics and data-quality status,
built directly off dq_log and dq_validation_log (see
src/ingestion/dq_logger.py) plus row counts across the raw/silver/mart
layers. This is the "DQ dashboard" those two tables were structured for
in the first place.

Read-only DuckDB connection throughout, same as market_overview.py.
"""

import sys
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingestion import dq_logger


@st.cache_data
def load_table_stats() -> pd.DataFrame:
    con = duckdb.connect(str(dq_logger.DB_PATH), read_only=True)
    try:
        existing = set(
            tuple(row)
            for row in con.execute(
                "SELECT table_schema, table_name FROM information_schema.tables"
            ).fetchall()
        )
        specs = [
            # Raw RBA's date column ("Title") is still an unparsed string
            # (e.g. "04-Jan-2011") at this layer -- MIN/MAX on it would sort
            # alphabetically, not chronologically, so no date range is shown
            # for it. Parsing that string is silver's job, not raw's.
            ("Raw — RBA cash rate", "raw", "rba_cash_rate", None),
            ("Raw — ASX200", "raw", "asx200", '"Date"'),
            ("Silver — RBA cash rate", "silver", "rba_cash_rate_daily", '"Title"'),
            ("Silver — ASX200", "silver", "asx200_daily", '"Date"'),
            ("Mart — aligned_daily", "curated", "aligned_daily", '"date"'),
            ("Mart — metrics_daily", "curated", "metrics_daily", '"date"'),
        ]
        # min_date/max_date are formatted to plain strings (not left as a mix
        # of None and datetime.date) -- pyarrow can't infer one Arrow type
        # for an object column mixing those, and st.dataframe would error.
        rows = []
        for label, schema, table, date_col in specs:
            if (schema, table) not in existing:
                rows.append({"table": label, "rows": None, "min_date": "—", "max_date": "—"})
                continue
            count = con.execute(f"SELECT COUNT(*) FROM {schema}.{table}").fetchone()[0]
            if date_col is None:
                min_d, max_d = "—", "—"
            else:
                raw_min, raw_max = con.execute(
                    f"SELECT MIN({date_col}), MAX({date_col}) FROM {schema}.{table}"
                ).fetchone()
                min_d, max_d = str(raw_min), str(raw_max)
            rows.append({"table": label, "rows": count, "min_date": min_d, "max_date": max_d})
        return pd.DataFrame(rows)
    finally:
        con.close()


@st.cache_data
def load_quarantine_counts() -> pd.DataFrame:
    con = duckdb.connect(str(dq_logger.DB_PATH), read_only=True)
    try:
        existing = set(
            row[0]
            for row in con.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'silver'"
            ).fetchall()
        )
        rows = []
        for label, table in [
            ("RBA cash rate", "rba_cash_rate_daily_quarantine"),
            ("ASX200", "asx200_daily_quarantine"),
        ]:
            count = (
                con.execute(f"SELECT COUNT(*) FROM silver.{table}").fetchone()[0]
                if table in existing
                else 0
            )
            rows.append({"source": label, "quarantined_rows": count})
        return pd.DataFrame(rows)
    finally:
        con.close()


@st.cache_data
def load_latest_pipeline_runs() -> pd.DataFrame:
    con = duckdb.connect(str(dq_logger.DB_PATH), read_only=True)
    try:
        return con.execute(
            """
            SELECT source, status, row_count, message, run_timestamp
            FROM (
                SELECT *, ROW_NUMBER() OVER (PARTITION BY source ORDER BY run_timestamp DESC) AS rn
                FROM dq_log
            )
            WHERE rn = 1
            ORDER BY source
            """
        ).fetchdf()
    finally:
        con.close()


@st.cache_data
def load_latest_dq_checks() -> pd.DataFrame:
    con = duckdb.connect(str(dq_logger.DB_PATH), read_only=True)
    try:
        return con.execute(
            """
            SELECT dataset, check_name, status, records_checked, records_failed,
                   records_warned, reason, run_timestamp
            FROM (
                SELECT *, ROW_NUMBER() OVER (
                    PARTITION BY dataset, check_name ORDER BY run_timestamp DESC
                ) AS rn
                FROM dq_validation_log
            )
            WHERE rn = 1
            ORDER BY dataset, check_name
            """
        ).fetchdf()
    finally:
        con.close()


st.title("Data statistics & quality")
st.caption("Row counts and freshness across the pipeline layers, plus the latest outcome of every data-quality check.")

try:
    run_df = load_latest_pipeline_runs()
    checks_df = load_latest_dq_checks()
    quarantine_df = load_quarantine_counts()
    table_stats_df = load_table_stats()
except duckdb.Error:
    st.warning("No pipeline data found yet — run `python run_pipeline.py` first.")
    st.stop()

# --- KPI row ---
total_quarantined = int(quarantine_df["quarantined_rows"].sum()) if not quarantine_df.empty else 0
checks_passing = int((checks_df["status"] == "pass").sum())
checks_total = len(checks_df)
any_run_failed = bool((run_df["status"] == "failure").any())
latest_mart_row = table_stats_df[table_stats_df["table"] == "Mart — metrics_daily"]
latest_date = latest_mart_row["max_date"].iloc[0] if not latest_mart_row.empty else "—"

with st.container(horizontal=True):
    st.metric(
        "Latest pipeline run",
        "Failed stage present" if any_run_failed else "All stages OK",
        border=True,
    )
    st.metric("DQ checks passing", f"{checks_passing}/{checks_total}", border=True)
    st.metric("Quarantined rows", total_quarantined, border=True)
    st.metric("Latest market data date", str(latest_date), border=True)

# --- Pipeline run history (latest per stage) ---
with st.container(border=True):
    st.subheader("Pipeline stages — latest run")
    st.dataframe(
        run_df,
        hide_index=True,
        width="stretch",
        column_config={
            "source": "Stage",
            "status": "Status",
            "row_count": "Rows",
            "message": "Message",
            "run_timestamp": st.column_config.DatetimeColumn("Last run", format="YYYY-MM-DD HH:mm:ss"),
        },
    )

# --- DQ validation checks (latest per check) ---
with st.container(border=True):
    st.subheader("Data-quality checks — latest result")
    st.dataframe(
        checks_df,
        hide_index=True,
        width="stretch",
        column_config={
            "dataset": "Dataset",
            "check_name": "Check",
            "status": "Status",
            "records_checked": "Checked",
            "records_failed": "Failed",
            "records_warned": "Warned",
            "reason": "Reason",
            "run_timestamp": st.column_config.DatetimeColumn("Last run", format="YYYY-MM-DD HH:mm:ss"),
        },
    )

# --- Table statistics across layers ---
with st.container(border=True):
    st.subheader("Table statistics (raw → silver → mart)")
    st.dataframe(
        table_stats_df,
        hide_index=True,
        width="stretch",
        column_config={
            "table": "Table",
            "rows": "Rows",
            "min_date": "Earliest date",
            "max_date": "Latest date",
        },
    )

# --- Quarantined records detail ---
if total_quarantined > 0:
    with st.container(border=True):
        st.subheader("Quarantined records")
        st.dataframe(quarantine_df, hide_index=True, width="stretch")
        st.caption(
            "Rows that failed a critical validation check are held here, not silently "
            "dropped — see silver_builder.py and docs/ai_agent_process_log.md Entry 9."
        )
else:
    st.success("No quarantined records — every row in the latest run passed critical validation.")
