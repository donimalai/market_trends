"""
Tests for src/transform/silver_builder.py — the 6 RBA + 7 ASX200 data-quality
checks, using synthetic raw-layer fixtures. Includes regression tests for
the two real bugs caught while building this module (see Entry 9 in
docs/ai_agent_process_log.md): a missing-value silently miscounted as
"out of range", and an empty quarantine table getting the wrong DuckDB
column type for its reason column.
"""

import duckdb
import numpy as np
import pandas as pd
import pytest

from src.ingestion import dq_logger
from src.transform.silver_builder import _validate_asx200, _validate_rba


@pytest.fixture
def con(tmp_path, monkeypatch):
    db_path = tmp_path / "test_warehouse.duckdb"
    monkeypatch.setattr(dq_logger, "DB_PATH", db_path)
    connection = duckdb.connect(str(db_path))
    connection.execute("CREATE SCHEMA IF NOT EXISTS raw")
    yield connection
    connection.close()


def _seed_rba(con, rows: pd.DataFrame) -> None:
    con.register("rba_seed", rows)
    con.execute("CREATE OR REPLACE TABLE raw.rba_cash_rate AS SELECT * FROM rba_seed")
    con.unregister("rba_seed")


def _seed_asx(con, rows: pd.DataFrame) -> None:
    con.register("asx_seed", rows)
    con.execute("CREATE OR REPLACE TABLE raw.asx200 AS SELECT * FROM asx_seed")
    con.unregister("asx_seed")


def _clean_rba_rows(dates, rates, changes=None) -> pd.DataFrame:
    if changes is None:
        changes = [None] * len(dates)
    return pd.DataFrame(
        {
            "Title": dates,
            "Cash Rate Target": rates,
            "Change in the Cash Rate Target": changes,
            "load_date": [pd.Timestamp("2024-01-10")] * len(dates),
        }
    )


def _clean_asx_rows(dates, close, **overrides) -> pd.DataFrame:
    n = len(dates)
    df = pd.DataFrame(
        {
            "Date": dates,
            "Open": overrides.get("open", close),
            "High": overrides.get("high", [c + 1 for c in close]),
            "Low": overrides.get("low", [c - 1 for c in close]),
            "Close": close,
            "Volume": overrides.get("volume", [1000] * n),
            "Dividends": overrides.get("dividends", [0.0] * n),
            "Stock Splits": overrides.get("stock_splits", [0.0] * n),
            "load_date": [pd.Timestamp("2024-01-10")] * n,
        }
    )
    return df


class TestRbaChecks:
    def test_completeness_flags_missing_business_day(self, con):
        # 01-02, 01-03 present; 01-04 (a Thursday) skipped -- one business-day gap.
        rows = _clean_rba_rows(
            ["01-Jan-2024", "02-Jan-2024", "03-Jan-2024", "05-Jan-2024"],
            [4.00, 4.00, 4.00, 4.00],
        )
        _seed_rba(con, rows)
        kept, quarantine, summary = _validate_rba(con)

        row = summary.set_index("check").loc["completeness"]
        assert row["status"] == "warning"
        assert row["warned"] == 1

    def test_valid_range_distinguishes_missing_from_out_of_range(self, con):
        # Regression test for the bug in Entry 9: a missing value must be
        # reported as "missing", not silently counted as "out of range".
        rows = _clean_rba_rows(
            ["01-Jan-2024", "02-Jan-2024", "03-Jan-2024"],
            [4.00, np.nan, 20.0],  # row 2: missing; row 3: genuinely out of [0,15]
        )
        _seed_rba(con, rows)
        kept, quarantine, summary = _validate_rba(con)

        row = summary.set_index("check").loc["valid_range"]
        assert row["status"] == "fail"  # the genuine out-of-range row makes this fail overall
        assert row["failed"] == 1  # only the 20.0 row, not the missing one
        assert row["warned"] == 1  # the missing row is a separate, distinct count
        # The out-of-range row is quarantined; the missing-value row is kept (flagged, not dropped).
        assert len(quarantine) == 1
        assert quarantine.iloc[0]["Cash Rate Target"] == 20.0
        assert any(pd.isna(kept["Cash Rate Target"]))

    def test_internal_consistency_quarantines_mismatched_change(self, con):
        # 4.00 -> 4.25 is a genuine +0.25 move, but recorded as +0.50 -- inconsistent.
        rows = _clean_rba_rows(
            ["01-Jan-2024", "02-Jan-2024"],
            [4.00, 4.25],
            changes=[None, 0.50],
        )
        _seed_rba(con, rows)
        kept, quarantine, summary = _validate_rba(con)

        row = summary.set_index("check").loc["internal_consistency"]
        assert row["status"] == "fail"
        assert row["failed"] == 1
        assert len(quarantine) == 1

    def test_no_duplicates_quarantines_conflicting_and_warns_identical(self, con):
        rows = _clean_rba_rows(
            ["01-Jan-2024", "01-Jan-2024", "02-Jan-2024", "02-Jan-2024"],
            [4.00, 4.25, 4.50, 4.50],  # 01-Jan: conflicting; 02-Jan: identical duplicate
        )
        _seed_rba(con, rows)
        kept, quarantine, summary = _validate_rba(con)

        row = summary.set_index("check").loc["no_duplicates"]
        assert row["failed"] == 2  # both 01-Jan rows quarantined
        assert row["warned"] == 2  # both 02-Jan rows flagged
        assert len(quarantine) == 2
        # Identical duplicates get deduped down to one row in the kept table.
        assert (kept["Title"] == pd.Timestamp("2024-01-02").date()).sum() == 1

    def test_unusual_movement_flags_large_move_without_quarantining(self, con):
        rows = _clean_rba_rows(
            ["01-Jan-2024", "02-Jan-2024"], [4.00, 4.75], changes=[None, 0.75]
        )
        _seed_rba(con, rows)
        kept, quarantine, summary = _validate_rba(con)

        row = summary.set_index("check").loc["unusual_movement"]
        assert row["status"] == "warning"
        assert row["warned"] == 1
        assert quarantine.empty  # a large but internally-consistent move is kept, just flagged

    def test_clean_data_produces_no_quarantine_with_correct_reason_column_type(self, con):
        # Regression test for the second bug in Entry 9: with zero
        # quarantined rows, pandas' empty-slice dtype inference must not
        # silently give quarantine_reason a numeric DuckDB type.
        rows = _clean_rba_rows(
            ["01-Jan-2024", "02-Jan-2024", "03-Jan-2024"], [4.00, 4.00, 4.00]
        )
        _seed_rba(con, rows)
        kept, quarantine, summary = _validate_rba(con)

        assert quarantine.empty
        con.execute("CREATE SCHEMA IF NOT EXISTS silver")
        con.register("q_view", quarantine.assign(load_date=pd.Timestamp("2024-01-10")))
        con.execute("CREATE OR REPLACE TABLE silver.rba_quarantine_test AS SELECT * FROM q_view")
        col_type = con.execute(
            "SELECT column_type FROM (DESCRIBE silver.rba_quarantine_test) "
            "WHERE column_name = 'quarantine_reason'"
        ).fetchone()[0]
        assert col_type == "VARCHAR"


class TestAsx200Checks:
    def test_completeness_flags_missing_business_day(self, con):
        dates = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-05"])  # skips 01-04
        rows = _clean_asx_rows(dates, [100.0, 101.0, 102.0])
        _seed_asx(con, rows)
        kept, quarantine, summary = _validate_asx200(con)

        row = summary.set_index("check").loc["completeness"]
        assert row["status"] == "warning"
        assert row["warned"] == 1

    def test_valid_values_quarantines_ohlc_and_volume_violations(self, con):
        dates = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"])
        rows = _clean_asx_rows(
            dates,
            close=[100.0, 101.0, 102.0],
            low=[99.0, 105.0, 101.0],  # row 2: Low > High -- invalid
            volume=[1000, 1100, -5],  # row 3: negative volume -- invalid
        )
        _seed_asx(con, rows)
        kept, quarantine, summary = _validate_asx200(con)

        row = summary.set_index("check").loc["valid_values"]
        assert row["status"] == "fail"
        assert row["failed"] == 2
        assert len(quarantine) == 2

    def test_internal_consistency_flags_large_move_without_quarantining(self, con):
        dates = pd.to_datetime(["2024-01-02", "2024-01-03"])
        rows = _clean_asx_rows(dates, close=[100.0, 120.0])  # +20% day-over-day
        _seed_asx(con, rows)
        kept, quarantine, summary = _validate_asx200(con)

        row = summary.set_index("check").loc["internal_consistency"]
        assert row["status"] == "warning"
        assert row["warned"] == 1
        assert quarantine.empty

    def test_no_duplicates_quarantines_conflicting_and_warns_identical(self, con):
        dates = pd.to_datetime(["2024-01-02", "2024-01-02", "2024-01-03", "2024-01-03"])
        rows = _clean_asx_rows(dates, close=[100.0, 105.0, 110.0, 110.0])
        _seed_asx(con, rows)
        kept, quarantine, summary = _validate_asx200(con)

        row = summary.set_index("check").loc["no_duplicates"]
        assert row["failed"] == 2
        assert row["warned"] == 2
        assert len(quarantine) == 2

    def test_index_composition_is_always_not_applicable(self, con):
        dates = pd.to_datetime(["2024-01-02"])
        rows = _clean_asx_rows(dates, close=[100.0])
        _seed_asx(con, rows)
        _, _, summary = _validate_asx200(con)

        row = summary.set_index("check").loc["index_composition"]
        assert row["status"] == "not_applicable"

    def test_missing_or_zero_close_quarantines(self, con):
        dates = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"])
        rows = _clean_asx_rows(dates, close=[100.0, 0.0, np.nan])
        _seed_asx(con, rows)
        kept, quarantine, summary = _validate_asx200(con)

        row = summary.set_index("check").loc["missing_or_zero_close"]
        assert row["failed"] == 2
        assert len(kept) == 1

    def test_clean_data_produces_no_quarantine_with_correct_reason_column_type(self, con):
        dates = pd.to_datetime(["2024-01-02", "2024-01-03"])
        rows = _clean_asx_rows(dates, close=[100.0, 101.0])
        _seed_asx(con, rows)
        kept, quarantine, summary = _validate_asx200(con)

        assert quarantine.empty
        con.execute("CREATE SCHEMA IF NOT EXISTS silver")
        con.register("q_view", quarantine.assign(load_date=pd.Timestamp("2024-01-10")))
        con.execute("CREATE OR REPLACE TABLE silver.asx_quarantine_test AS SELECT * FROM q_view")
        col_type = con.execute(
            "SELECT column_type FROM (DESCRIBE silver.asx_quarantine_test) "
            "WHERE column_name = 'quarantine_reason'"
        ).fetchone()[0]
        assert col_type == "VARCHAR"
