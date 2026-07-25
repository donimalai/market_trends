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

STATUS_BADGES = {
    "success": "🟢 success",
    "pass": "🟢 pass",
    "warning": "🟡 warning",
    "failure": "🔴 failure",
    "fail": "🔴 fail",
    "not_applicable": "⚪ not_applicable",
}


def _badge(series: pd.Series) -> pd.Series:
    return series.map(lambda s: STATUS_BADGES.get(s, s))


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


@st.cache_data
def load_dq_trend(limit_runs: int = 10) -> pd.DataFrame:
    """Pass/warning/fail counts per pipeline run, most recent last.

    dq_validation_log has one row per (dataset, check_name) per run, each
    stamped with its own datetime.now() a few milliseconds apart within a
    single silver_builder.py execution -- rounding to the minute clusters
    each run's ~13 checks together without needing a separate run-id column.
    """
    con = duckdb.connect(str(dq_logger.DB_PATH), read_only=True)
    try:
        df = con.execute(
            """
            SELECT date_trunc('minute', run_timestamp) AS run_bucket, status, COUNT(*) AS n
            FROM dq_validation_log
            GROUP BY 1, 2
            """
        ).fetchdf()
    finally:
        con.close()
    if df.empty:
        return df
    pivot = df.pivot_table(index="run_bucket", columns="status", values="n", fill_value=0)
    for col in ["pass", "warning", "fail", "not_applicable"]:
        if col not in pivot.columns:
            pivot[col] = 0
    pivot = pivot.sort_index().tail(limit_runs).reset_index()
    pivot["run_bucket"] = pivot["run_bucket"].dt.strftime("%Y-%m-%d %H:%M")
    return pivot.rename(columns={"run_bucket": "Run"})


@st.cache_data
def build_quarantine_worked_example():
    """Deliberately inject one invalid ASX200 row (Low > High, an
    impossible OHLC state) alongside real recent rows, and run it through
    the actual validation function from silver_builder.py -- this proves
    the quarantine mechanism really works by executing the real code, not
    by hardcoding what a quarantine row "would" look like. This is a
    synthetic test case: the real ingested data has never produced a
    quarantined row (0 quarantined in every run so far), so there is no
    genuine historical example to show instead.
    """
    from src.transform.silver_builder import _validate_asx200

    con_real = duckdb.connect(str(dq_logger.DB_PATH), read_only=True)
    try:
        base = con_real.execute('SELECT * FROM raw.asx200 ORDER BY "Date" DESC LIMIT 10').fetchdf()
    finally:
        con_real.close()

    if base.empty:
        return pd.DataFrame(), pd.DataFrame()

    bad_row = base.iloc[[0]].copy()
    bad_row["Date"] = bad_row["Date"] + pd.Timedelta(days=1)
    bad_row["Low"] = bad_row["High"] + 500  # deliberately impossible: Low > High
    injected = pd.concat([base, bad_row], ignore_index=True)

    scratch = duckdb.connect(":memory:")
    try:
        scratch.execute("CREATE SCHEMA raw")
        scratch.register("seed", injected)
        scratch.execute("CREATE TABLE raw.asx200 AS SELECT * FROM seed")
        _, quarantine, _ = _validate_asx200(scratch)
    finally:
        scratch.close()
    return quarantine, bad_row


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
    run_display = run_df.copy()
    run_display["status"] = _badge(run_display["status"])
    st.dataframe(
        run_display,
        hide_index=True,
        width="stretch",
        column_config={
            "source": st.column_config.Column("Stage", width="small"),
            "status": st.column_config.Column("Status", width="small"),
            "row_count": st.column_config.Column("Rows", width="small"),
            "message": st.column_config.Column("Message", width="large"),
            "run_timestamp": st.column_config.DatetimeColumn(
                "Last run", format="YYYY-MM-DD HH:mm:ss", width="small"
            ),
        },
    )

# --- DQ validation checks (latest per check) ---
with st.container(border=True):
    st.subheader("Data-quality checks — latest result")

    # UX fix: define exactly what triggers each status, since "warning"
    # with 0 failed rows (e.g. completeness) otherwise reads as confusing.
    with st.expander("What do pass / warning / fail mean here?"):
        st.markdown(
            "- 🟢 **pass** — the check found nothing to flag.\n"
            "- 🟡 **warning** — something unusual but not necessarily wrong. "
            "For **completeness** specifically: a business day has no matching record "
            "(most often a public holiday neither source publishes on) — rows are still "
            "kept, this is informational, not a data integrity problem.\n"
            "- 🔴 **fail** — a critical rule was broken (e.g. `High < Low`, a missing "
            "primary key, a duplicate date with conflicting values). Failing rows are "
            "quarantined, not silently dropped — see the Quarantine section below.\n"
            "- ⚪ **not_applicable** — the check can't be evaluated at all with the "
            "current data source (see note below the table)."
        )

    checks_display = checks_df.copy()
    checks_display["status"] = _badge(checks_display["status"])
    st.dataframe(
        checks_display,
        hide_index=True,
        width="stretch",
        column_config={
            "dataset": st.column_config.Column("Dataset", width="small"),
            "check_name": st.column_config.Column("Check", width="medium"),
            "status": st.column_config.Column("Status", width="small"),
            "records_checked": st.column_config.Column("Checked", width="small"),
            "records_failed": st.column_config.Column("Failed", width="small"),
            "records_warned": st.column_config.Column("Warned", width="small"),
            "reason": st.column_config.Column("Reason", width="large"),
            "run_timestamp": st.column_config.DatetimeColumn(
                "Last run", format="YYYY-MM-DD HH:mm:ss", width="small"
            ),
        },
    )
    st.caption(
        "**Why `index_composition` (ASX200) always shows not_applicable:** the current "
        "ASX200 source (Yahoo Finance OHLCV) doesn't include a \"number of companies in "
        "the index\" field at all, so this check can't be evaluated — logged explicitly "
        "as not_applicable rather than silently skipped or faked. Enforcing it for real "
        "would need a separate ASX index-constituent data source. Kept in this table "
        "rather than removed, so the gap stays visible instead of silently disappearing."
    )

# --- DQ trend across recent runs ---
with st.container(border=True):
    st.subheader("DQ trend — recent pipeline runs")
    trend_df = load_dq_trend()
    if trend_df.empty:
        st.caption("Not enough run history yet to show a trend.")
    else:
        st.caption(
            f"Pass/warning/fail counts across the last {len(trend_df)} pipeline run(s) "
            "(all 13 checks × both datasets, combined) — this is a continuously monitored "
            "system, not a one-off check."
        )
        st.bar_chart(
            trend_df.set_index("Run")[["pass", "warning", "fail"]],
            color=["#1e7e34", "#b26a00", "#c62828"],
        )
        st.dataframe(trend_df, hide_index=True, width="stretch")

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
with st.container(border=True):
    st.subheader("Quarantined records")
    if total_quarantined > 0:
        st.dataframe(quarantine_df, hide_index=True, width="stretch")
    else:
        st.success("No quarantined records in the real pipeline — every row in the latest run passed critical validation.")

    st.markdown("**Worked example: does the quarantine mechanism actually work?**")
    st.caption(
        "The real data has never produced a quarantined row, so this is a **deliberately "
        "injected synthetic test case** — one invalid row (an impossible `Low > High`) is "
        "appended to real recent ASX200 rows and run through the actual "
        "`_validate_asx200()` function from `silver_builder.py`. Not a hardcoded mock: "
        "the reason text below is the real function's real output."
    )
    example_quarantine, example_bad_row = build_quarantine_worked_example()
    if example_quarantine.empty:
        st.info("No raw ASX200 data available yet to build the worked example — run the pipeline first.")
    else:
        st.dataframe(
            example_quarantine[["Date", "Open", "High", "Low", "Close", "quarantine_reason"]],
            hide_index=True,
            width="stretch",
        )
