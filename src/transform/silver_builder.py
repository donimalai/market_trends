"""
silver_builder.py

Reads each source's `raw` table, applies type casting, then runs a full
data-quality validation suite against it. Every check produces a clear
pass/fail/warning result plus a human-readable reason, and every check's
outcome is logged to dq_validation_log (via dq_logger.log_validation) so a
DQ dashboard can be built directly off that table.

Records that fail a critical check are quarantined — written to a
`*_quarantine` table with the specific reason(s) — rather than silently
dropped or allowed to break downstream tables. Records that only trigger a
warning stay in the main silver table, tagged with a `dq_warning_reason`
column. Column names are otherwise kept exactly as the source uses them —
casting, dedup, and validation are the only transformations applied.

Layers this module writes, in data/warehouse.duckdb:
- silver.rba_cash_rate_daily            — passed/warned RBA rows
- silver.rba_cash_rate_daily_quarantine — failed RBA rows + reasons
- silver.asx200_daily                   — passed/warned ASX200 rows
- silver.asx200_daily_quarantine        — failed ASX200 rows + reasons

RBA validation is run against "Cash Rate Target" / "Change in the Cash Rate
Target" (not "Interbank Overnight Cash Rate", used elsewhere in this repo)
since those are the two columns that actually pair a value with a
same-row "change from previous" figure, matching this suite's field spec.
"""

import sys
from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ingestion import dq_logger


def _flag(df: pd.DataFrame, col: str, mask: pd.Series, message: str) -> None:
    for i in df.index[mask]:
        df.at[i, col].append(message)


def _validate_rba(con: duckdb.DuckDBPyConnection) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run all Cash Rate DQ checks. Returns (kept, quarantined, summary)."""
    df = con.execute("SELECT * FROM raw.rba_cash_rate").fetchdf()
    df["Title"] = pd.to_datetime(df["Title"], format="%d-%b-%Y", errors="coerce")
    df["Cash Rate Target"] = pd.to_numeric(df["Cash Rate Target"], errors="coerce")
    df["Change in the Cash Rate Target"] = pd.to_numeric(
        df["Change in the Cash Rate Target"], errors="coerce"
    )

    df["_fail"] = [[] for _ in range(len(df))]
    df["_warn"] = [[] for _ in range(len(df))]
    summary_rows = []
    run_ts = datetime.now()
    n = len(df)

    def record(check_name, status, checked, failed, warned, reason):
        dq_logger.log_validation(
            dataset="RBA_CashRate",
            check_name=check_name,
            status=status,
            records_checked=checked,
            records_failed=failed,
            records_warned=warned,
            reason=reason,
        )
        summary_rows.append(
            {
                "dataset": "RBA_CashRate",
                "check": check_name,
                "status": status,
                "checked": checked,
                "failed": failed,
                "warned": warned,
                "run_at": run_ts,
            }
        )

    # 1. Completeness -- RBA publishes on business days only; flag any
    # missing business-day gaps in the date range.
    full_bdays = pd.bdate_range(df["Title"].min(), df["Title"].max())
    missing_days = sorted(set(full_bdays.date) - set(df["Title"].dt.date))
    if missing_days:
        preview = ", ".join(str(d) for d in missing_days[:5])
        more = f" (+{len(missing_days) - 5} more)" if len(missing_days) > 5 else ""
        record(
            "completeness", "warning", n, 0, len(missing_days),
            f"{len(missing_days)} business day(s) missing from the series: {preview}{more}",
        )
    else:
        record("completeness", "pass", n, 0, 0, "No missing business days.")

    # 2. Valid range -- Cash Rate Target must sit within 0-15% and move in
    # multiples of 0.05%.
    rate = df["Cash Rate Target"]
    out_of_range = rate.notna() & ~rate.between(0, 15)
    missing_rate = rate.isna()
    not_multiple = rate.notna() & (((rate * 100).round() % 5) != 0)
    if out_of_range.any():
        _flag(df, "_fail", out_of_range, "Cash Rate Target value 17.25-style: outside expected range 0-15%")
    if missing_rate.any():
        _flag(df, "_warn", missing_rate, "Cash Rate Target is missing")
    if not_multiple.any():
        _flag(df, "_warn", not_multiple, "Cash Rate Target is not a multiple of 0.05%")
    record(
        "valid_range",
        "fail" if out_of_range.any() else ("warning" if (missing_rate.any() or not_multiple.any()) else "pass"),
        n, int(out_of_range.sum()), int(missing_rate.sum() + not_multiple.sum()),
        f"{int(out_of_range.sum())} outside [0,15]; {int(missing_rate.sum())} missing; "
        f"{int(not_multiple.sum())} not a 0.05 multiple",
    )

    # 3. Internal consistency -- recorded "Change" should match the actual
    # difference from the previous row's Cash Rate Target.
    actual_change = rate.diff()
    recorded_change = df["Change in the Cash Rate Target"]
    mismatch = recorded_change.notna() & ((actual_change - recorded_change).abs() > 0.001)
    if mismatch.any():
        _flag(df, "_fail", mismatch, "Recorded change does not match actual difference from previous rate")
    record(
        "internal_consistency", "fail" if mismatch.any() else "pass", n, int(mismatch.sum()), 0,
        f"{int(mismatch.sum())} row(s) where recorded change != actual difference",
    )

    # 4. Freshness -- most recent record shouldn't be more than ~3 calendar
    # days old (allows a normal weekend without flagging).
    latest = df["Title"].max()
    staleness_days = (pd.Timestamp(datetime.now().date()) - latest).days
    if staleness_days > 3:
        record("freshness", "warning", n, 0, 0, f"Latest record is {staleness_days} day(s) old ({latest.date()})")
    else:
        record("freshness", "pass", n, 0, 0, f"Latest record is {staleness_days} day(s) old.")

    # 5. No duplicates -- same effective date shouldn't appear twice with
    # conflicting values (identical-value repeats are a softer, warning-level issue).
    dup_groups = df.groupby("Title")["Cash Rate Target"].nunique(dropna=False)
    conflicting_dates = dup_groups[dup_groups > 1].index
    conflicting_mask = df["Title"].isin(conflicting_dates)
    dup_counts = df["Title"].value_counts()
    harmless_dup_dates = dup_counts[dup_counts > 1].index.difference(conflicting_dates)
    harmless_mask = df["Title"].isin(harmless_dup_dates)
    if conflicting_mask.any():
        _flag(df, "_fail", conflicting_mask, "Duplicate date with conflicting Cash Rate Target values")
    if harmless_mask.any():
        _flag(df, "_warn", harmless_mask, "Duplicate date with identical values")
    record(
        "no_duplicates",
        "fail" if conflicting_mask.any() else ("warning" if harmless_mask.any() else "pass"),
        n, int(conflicting_mask.sum()), int(harmless_mask.sum()),
        f"{len(conflicting_dates)} conflicting date(s), {len(harmless_dup_dates)} harmless duplicate date(s)",
    )

    # 6. Unusual movement -- flag single-day changes bigger than 0.50%.
    unusual = actual_change.abs() > 0.50
    if unusual.any():
        _flag(df, "_warn", unusual.fillna(False), "Rate change exceeds 0.50% in a single move")
    record(
        "unusual_movement", "warning" if unusual.any() else "pass", n, 0, int(unusual.fillna(False).sum()),
        f"{int(unusual.fillna(False).sum())} row(s) with a rate move > 0.50%",
    )

    df["_status"] = df.apply(lambda r: "fail" if r["_fail"] else ("warning" if r["_warn"] else "pass"), axis=1)
    quarantine = df[df["_status"] == "fail"].copy()
    # .astype(str) matters even (especially) when quarantine is empty: pandas
    # can't infer a string dtype from zero samples via plain .apply(), and
    # silently produces a numeric dtype instead -- which DuckDB would then
    # give the wrong column type (e.g. INTEGER for a text column).
    quarantine["quarantine_reason"] = quarantine["_fail"].apply(lambda x: "; ".join(x)).astype(str)
    kept = df[df["_status"] != "fail"].copy()
    # .astype(object) for the same empty-slice dtype-inference reason as
    # quarantine_reason above -- but object, not str, since None here must
    # stay a real NULL, not become the literal string "None".
    kept["dq_warning_reason"] = (
        kept["_warn"].apply(lambda x: "; ".join(x) if x else None).astype(object)
    )

    kept = (
        kept.drop(columns=["_fail", "_warn", "_status"])
        .sort_values("Title")
        .drop_duplicates(subset=["Title"], keep="last")
        .reset_index(drop=True)
    )
    quarantine = quarantine.drop(columns=["_fail", "_warn", "_status"]).reset_index(drop=True)

    kept["Title"] = kept["Title"].dt.date
    if not quarantine.empty:
        quarantine["Title"] = quarantine["Title"].dt.date

    return kept, quarantine, pd.DataFrame(summary_rows)


def _validate_asx200(con: duckdb.DuckDBPyConnection) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run all ASX200 DQ checks. Returns (kept, quarantined, summary)."""
    df = con.execute("SELECT * FROM raw.asx200").fetchdf()
    df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None).dt.normalize()
    for col in ["Open", "High", "Low", "Close", "Volume", "Dividends", "Stock Splits"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["_fail"] = [[] for _ in range(len(df))]
    df["_warn"] = [[] for _ in range(len(df))]
    summary_rows = []
    run_ts = datetime.now()
    n = len(df)

    def record(check_name, status, checked, failed, warned, reason):
        dq_logger.log_validation(
            dataset="ASX200",
            check_name=check_name,
            status=status,
            records_checked=checked,
            records_failed=failed,
            records_warned=warned,
            reason=reason,
        )
        summary_rows.append(
            {
                "dataset": "ASX200",
                "check": check_name,
                "status": status,
                "checked": checked,
                "failed": failed,
                "warned": warned,
                "run_at": run_ts,
            }
        )

    # 1. Completeness -- one row per business day; gaps are reported (likely
    # ASX public holidays, which can't be distinguished from a real outage
    # without an external holiday calendar) rather than hard-failed.
    full_bdays = pd.bdate_range(df["Date"].min(), df["Date"].max())
    missing_days = sorted(set(full_bdays.date) - set(df["Date"].dt.date))
    if missing_days:
        preview = ", ".join(str(d) for d in missing_days[:5])
        more = f" (+{len(missing_days) - 5} more)" if len(missing_days) > 5 else ""
        record(
            "completeness", "warning", n, 0, len(missing_days),
            f"{len(missing_days)} business day(s) with no record (likely ASX public holidays): {preview}{more}",
        )
    else:
        record("completeness", "pass", n, 0, 0, "No missing business days.")

    # 2. Valid values -- Low must be <= Open/Close/High; High must be >=
    # Open/Close/Low; Close must be > 0; Volume must be >= 0.
    bad_low = (df["Low"] > df["Open"]) | (df["Low"] > df["Close"]) | (df["Low"] > df["High"])
    bad_high = (df["High"] < df["Open"]) | (df["High"] < df["Close"]) | (df["High"] < df["Low"])
    bad_close = df["Close"].isna() | (df["Close"] <= 0)
    bad_volume = df["Volume"] < 0
    bad_values = bad_low | bad_high | bad_close | bad_volume
    if bad_low.any():
        _flag(df, "_fail", bad_low, "Low price is greater than Open, Close, or High")
    if bad_high.any():
        _flag(df, "_fail", bad_high, "High price is less than Open, Close, or Low")
    if bad_close.any():
        _flag(df, "_fail", bad_close, "Close price is missing or <= 0")
    if bad_volume.any():
        _flag(df, "_fail", bad_volume, "Volume is negative")
    record(
        "valid_values", "fail" if bad_values.any() else "pass", n, int(bad_values.sum()), 0,
        f"{int(bad_values.sum())} row(s) failing OHLC/volume validity",
    )

    # 3. Internal consistency -- day-over-day % change from previous close,
    # flagged (not dropped) if magnitude exceeds 15%.
    pct_change = df["Close"].pct_change() * 100
    big_move = pct_change.abs() > 15
    if big_move.any():
        _flag(df, "_warn", big_move.fillna(False), "Daily % change from previous close exceeds 15%")
    record(
        "internal_consistency", "warning" if big_move.any() else "pass", n, 0, int(big_move.fillna(False).sum()),
        f"{int(big_move.fillna(False).sum())} row(s) with a >15% daily move",
    )

    # 4. No duplicates -- same trading date shouldn't appear twice with
    # conflicting values.
    dup_groups = df.groupby("Date")["Close"].nunique(dropna=False)
    conflicting_dates = dup_groups[dup_groups > 1].index
    conflicting_mask = df["Date"].isin(conflicting_dates)
    dup_counts = df["Date"].value_counts()
    harmless_dup_dates = dup_counts[dup_counts > 1].index.difference(conflicting_dates)
    harmless_mask = df["Date"].isin(harmless_dup_dates)
    if conflicting_mask.any():
        _flag(df, "_fail", conflicting_mask, "Duplicate trading date with conflicting values")
    if harmless_mask.any():
        _flag(df, "_warn", harmless_mask, "Duplicate trading date with identical values")
    record(
        "no_duplicates",
        "fail" if conflicting_mask.any() else ("warning" if harmless_mask.any() else "pass"),
        n, int(conflicting_mask.sum()), int(harmless_mask.sum()),
        f"{len(conflicting_dates)} conflicting date(s), {len(harmless_dup_dates)} harmless duplicate date(s)",
    )

    # 5. Freshness -- latest record shouldn't be more than 1 business day
    # behind today.
    latest = df["Date"].max()
    today = pd.Timestamp(datetime.now().date())
    bdays_behind = len(pd.bdate_range(latest + pd.Timedelta(days=1), today)) if today > latest else 0
    if bdays_behind > 1:
        record(
            "freshness", "warning", n, 0, 0,
            f"Latest record ({latest.date()}) is {bdays_behind} business day(s) behind today",
        )
    else:
        record("freshness", "pass", n, 0, 0, f"Latest record is {latest.date()}, up to date.")

    # 6. Index composition -- NOT AVAILABLE with the current data source.
    # yfinance's OHLCV feed for ^AXJO doesn't carry a constituent-count
    # field, so this check can't be evaluated -- logged explicitly (as
    # "not_applicable") rather than silently skipped or faked.
    record(
        "index_composition", "not_applicable", n, 0, 0,
        "No 'number of companies in index' field is ingested from the current source "
        "(yfinance OHLCV) -- would require adding an ASX index-constituent data source.",
    )

    # 7. Missing or zero close on a trading day.
    missing_or_zero_close = df["Close"].isna() | (df["Close"] == 0)
    if missing_or_zero_close.any():
        _flag(df, "_fail", missing_or_zero_close, "Close price is missing or zero on a trading day")
    record(
        "missing_or_zero_close", "fail" if missing_or_zero_close.any() else "pass",
        n, int(missing_or_zero_close.sum()), 0,
        f"{int(missing_or_zero_close.sum())} row(s) with missing/zero close",
    )

    df["_status"] = df.apply(lambda r: "fail" if r["_fail"] else ("warning" if r["_warn"] else "pass"), axis=1)
    quarantine = df[df["_status"] == "fail"].copy()
    # .astype(str) matters even (especially) when quarantine is empty: pandas
    # can't infer a string dtype from zero samples via plain .apply(), and
    # silently produces a numeric dtype instead -- which DuckDB would then
    # give the wrong column type (e.g. INTEGER for a text column).
    quarantine["quarantine_reason"] = quarantine["_fail"].apply(lambda x: "; ".join(x)).astype(str)
    kept = df[df["_status"] != "fail"].copy()
    # .astype(object) for the same empty-slice dtype-inference reason as
    # quarantine_reason above -- but object, not str, since None here must
    # stay a real NULL, not become the literal string "None".
    kept["dq_warning_reason"] = (
        kept["_warn"].apply(lambda x: "; ".join(x) if x else None).astype(object)
    )

    kept = (
        kept.drop(columns=["_fail", "_warn", "_status"])
        .sort_values("Date")
        .drop_duplicates(subset=["Date"], keep="last")
        .reset_index(drop=True)
    )
    quarantine = quarantine.drop(columns=["_fail", "_warn", "_status"]).reset_index(drop=True)

    kept["Date"] = kept["Date"].dt.date
    if not quarantine.empty:
        quarantine["Date"] = quarantine["Date"].dt.date

    return kept, quarantine, pd.DataFrame(summary_rows)


def _print_summary(summary_df: pd.DataFrame) -> None:
    if summary_df.empty:
        return
    print("\n=== Data Quality Validation Summary ===")
    cols = ["dataset", "check", "status", "checked", "failed", "warned", "run_at"]
    widths = {c: max(len(c), summary_df[c].astype(str).map(len).max()) for c in cols}
    header = "  ".join(c.ljust(widths[c]) for c in cols)
    print(header)
    print("-" * len(header))
    for _, row in summary_df.iterrows():
        print("  ".join(str(row[c]).ljust(widths[c]) for c in cols))
    print()


def build_silver_tables():
    """Type, validate, and quarantine raw.* tables into silver.* tables."""
    load_date = datetime.now()
    con = duckdb.connect(str(dq_logger.DB_PATH))
    try:
        con.execute("CREATE SCHEMA IF NOT EXISTS silver")

        rba_kept, rba_quarantine, rba_summary = _validate_rba(con)
        rba_kept["load_date"] = load_date
        con.register("silver_rba_view", rba_kept)
        con.execute(
            "CREATE OR REPLACE TABLE silver.rba_cash_rate_daily AS SELECT * FROM silver_rba_view"
        )
        con.unregister("silver_rba_view")
        if not rba_quarantine.empty:
            rba_quarantine["load_date"] = load_date
        con.register("silver_rba_quarantine_view", rba_quarantine)
        con.execute(
            "CREATE OR REPLACE TABLE silver.rba_cash_rate_daily_quarantine AS "
            "SELECT * FROM silver_rba_quarantine_view"
        )
        con.unregister("silver_rba_quarantine_view")
        dq_logger.log_run(
            source="Silver_RBA",
            row_count=len(rba_kept),
            status="warning" if len(rba_quarantine) else "success",
            message=f"{len(rba_kept)} row(s) kept, {len(rba_quarantine)} row(s) quarantined.",
        )

        asx_kept, asx_quarantine, asx_summary = _validate_asx200(con)
        asx_kept["load_date"] = load_date
        con.register("silver_asx_view", asx_kept)
        con.execute(
            "CREATE OR REPLACE TABLE silver.asx200_daily AS SELECT * FROM silver_asx_view"
        )
        con.unregister("silver_asx_view")
        if not asx_quarantine.empty:
            asx_quarantine["load_date"] = load_date
        con.register("silver_asx_quarantine_view", asx_quarantine)
        con.execute(
            "CREATE OR REPLACE TABLE silver.asx200_daily_quarantine AS "
            "SELECT * FROM silver_asx_quarantine_view"
        )
        con.unregister("silver_asx_quarantine_view")
        dq_logger.log_run(
            source="Silver_ASX200",
            row_count=len(asx_kept),
            status="warning" if len(asx_quarantine) else "success",
            message=f"{len(asx_kept)} row(s) kept, {len(asx_quarantine)} row(s) quarantined.",
        )
    except Exception as exc:
        dq_logger.log_run(source="Silver_Build", row_count=0, status="failure", message=str(exc))
        raise RuntimeError(f"Silver layer build failed: {exc}") from exc
    finally:
        con.close()

    _print_summary(pd.concat([rba_summary, asx_summary], ignore_index=True))


if __name__ == "__main__":
    build_silver_tables()
