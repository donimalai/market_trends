"""
Tests for src/transform/align.py — forward-fill correctness and no
off-by-one-day errors when joining RBA cash rate onto ASX200 trading days,
using synthetic silver-layer fixture data. Also tests the pure dim_date
calendar-attribute builder.
"""

import datetime

import duckdb
import pandas as pd
import pytest

from src.ingestion import dq_logger
from src.transform.align import _build_dim_date, align_daily


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_warehouse.duckdb"
    monkeypatch.setattr(dq_logger, "DB_PATH", db_path)
    return db_path


def _seed_silver_tables(db_path):
    con = duckdb.connect(str(db_path))
    con.execute("CREATE SCHEMA IF NOT EXISTS silver")

    # RBA rate: 4.00 through 01-03, changes to 4.25 effective 01-04. No row
    # at all for 01-08 -- that date must be forward-filled, not left null.
    rba = pd.DataFrame(
        {
            "Title": pd.to_datetime(
                ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]
            ).date,
            "Cash Rate Target": [4.00, 4.00, 4.00, 4.25, 4.25],
            "load_date": [datetime.datetime(2024, 1, 10)] * 5,
        }
    )
    con.register("rba_view", rba)
    con.execute("CREATE TABLE silver.rba_cash_rate_daily AS SELECT * FROM rba_view")

    # ASX trades 01-02 .. 01-05 plus 01-08 (skipping the 01-06/01-07 weekend).
    asx_dates = pd.to_datetime(
        ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08"]
    )
    asx = pd.DataFrame(
        {
            "Date": asx_dates,
            "Open": [100.0, 101.0, 102.0, 103.0, 104.0],
            "High": [101.0, 102.0, 103.0, 104.0, 105.0],
            "Low": [99.0, 100.0, 101.0, 102.0, 103.0],
            "Close": [100.5, 101.5, 102.5, 103.5, 104.5],
            "Volume": [1000, 1100, 1200, 1300, 1400],
            "load_date": [datetime.datetime(2024, 1, 10)] * 5,
        }
    )
    con.register("asx_view", asx)
    con.execute("CREATE TABLE silver.asx200_daily AS SELECT * FROM asx_view")
    con.close()


def test_forward_fill_and_no_off_by_one(temp_db):
    _seed_silver_tables(temp_db)
    result = align_daily().set_index("date")

    # Exact-match dates: cash rate on its own effective date.
    assert result.loc[datetime.date(2024, 1, 2), "cash_rate"] == pytest.approx(4.00)
    assert result.loc[datetime.date(2024, 1, 3), "cash_rate"] == pytest.approx(4.00)
    # The rate change takes effect exactly on 01-04, not delayed to 01-05
    # and not pulled forward to 01-03 -- the classic off-by-one-day bug.
    assert result.loc[datetime.date(2024, 1, 4), "cash_rate"] == pytest.approx(4.25)
    assert result.loc[datetime.date(2024, 1, 5), "cash_rate"] == pytest.approx(4.25)
    # 01-08 has no RBA row at all -- must forward-fill the last known rate
    # (4.25 from 01-05), not be null and not incorrectly revert to 4.00.
    assert result.loc[datetime.date(2024, 1, 8), "cash_rate"] == pytest.approx(4.25)


def test_only_asx_trading_days_kept(temp_db):
    _seed_silver_tables(temp_db)
    result = align_daily()

    # 5 ASX trading days in the fixture; RBA's extra day (01-01, no ASX
    # session) must not leak into the aligned table as an extra row.
    assert len(result) == 5
    assert datetime.date(2024, 1, 1) not in set(result["date"])


class TestBuildDimDate:
    def test_calendar_attributes(self):
        dates = pd.Series(pd.to_datetime(["2024-01-31", "2024-02-01", "2024-03-31"]))
        dim = _build_dim_date(dates).set_index("date")

        jan31 = dim.loc[datetime.date(2024, 1, 31)]
        assert jan31["year"] == 2024
        assert jan31["quarter"] == 1
        assert jan31["month"] == 1
        assert jan31["month_name"] == "January"
        assert jan31["day_name"] == "Wednesday"
        assert bool(jan31["is_month_end"]) is True

        feb1 = dim.loc[datetime.date(2024, 2, 1)]
        assert bool(feb1["is_month_end"]) is False

        mar31 = dim.loc[datetime.date(2024, 3, 31)]
        assert bool(mar31["is_quarter_end"]) is True
