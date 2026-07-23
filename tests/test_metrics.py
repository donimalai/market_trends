"""
Tests for src/transform/metrics.py — rolling average volume, rate of
change, and volatility calculations against a small synthetic DataFrame
with known expected outputs, per docs/metric_definitions.md. Also unit
tests the RAG threshold/warm-up/near-zero-guard rule directly (Entry 11 in
docs/ai_agent_process_log.md finalized the exact boundaries these check).
"""

import duckdb
import numpy as np
import pandas as pd
import pytest

from src.ingestion import dq_logger
from src.transform.metrics import _rag_signal, compute_metrics


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_warehouse.duckdb"
    monkeypatch.setattr(dq_logger, "DB_PATH", db_path)
    return db_path


def _make_synthetic_aligned(n=25):
    # Close price grows by exactly 10% every day -> constant day-over-day
    # rate of change and (since log returns are then also constant) exactly
    # zero volatility -- both easy to hand-verify.
    dates = pd.date_range("2024-01-01", periods=n, freq="D").date
    close = [100 * (1.1**i) for i in range(n)]
    volume = [100 * (i + 1) for i in range(n)]  # 100, 200, ..., 2500
    return pd.DataFrame(
        {
            "date": dates,
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": volume,
            "cash_rate": [4.35] * n,
        }
    )


@pytest.fixture
def metrics_output(temp_db):
    df = _make_synthetic_aligned()
    con = duckdb.connect(str(temp_db))
    con.execute("CREATE SCHEMA IF NOT EXISTS curated")
    con.register("synthetic_view", df)
    con.execute("CREATE TABLE curated.aligned_daily AS SELECT * FROM synthetic_view")
    con.close()

    compute_metrics()

    con = duckdb.connect(str(temp_db))
    out = con.execute("SELECT * FROM curated.metrics_daily ORDER BY date").fetchdf()
    con.close()
    return out


def test_rolling_avg_volume_20d(metrics_output):
    # First 19 rows: not enough history for a full 20-day window (Section 1
    # edge case -- null, not a misleading partial-window average).
    assert metrics_output["rolling_avg_volume_20d"].iloc[:19].isna().all()
    # Row 20 (index 19): mean(volume[0:20]) = mean(100, 200, ..., 2000) = 1050.
    assert metrics_output["rolling_avg_volume_20d"].iloc[19] == pytest.approx(1050.0)


def test_rate_of_change_pct(metrics_output):
    # First row: no prior day -- null, not zero (Section 2 edge case).
    assert pd.isna(metrics_output["rate_of_change_pct"].iloc[0])
    # Every subsequent day is exactly +10% over the previous close by construction.
    assert (
        metrics_output["rate_of_change_pct"].iloc[1:].apply(lambda v: v == pytest.approx(10.0)).all()
    )


def test_volatility_14d_annualised(metrics_output):
    # First 14 rows: not enough log returns for a full 14-day window (Section 3 edge case).
    assert metrics_output["volatility_14d_annualised"].iloc[:14].isna().all()
    # Constant %-growth series -> constant log returns -> zero volatility.
    assert (
        metrics_output["volatility_14d_annualised"]
        .iloc[14:]
        .apply(lambda v: v == pytest.approx(0.0, abs=1e-9))
        .all()
    )


def test_rag_signal_null_with_short_history(metrics_output):
    # 25 rows is far short of the ~104 needed for the first RAG value
    # (Section 4's warm-up rule) -- every row should be null, not an error.
    assert metrics_output["rag_signal"].isna().all()


class TestRagSignalThresholds:
    """Direct unit tests for the finalized RAG boundary/warm-up/near-zero rule."""

    def test_warmup_returns_none_when_trailing_mean_missing(self):
        assert _rag_signal(ratio=1.0, trailing_mean=np.nan) is None

    def test_insufficient_signal_below_volatility_floor(self):
        # trailing_mean below the 3% floor -> "insufficient signal" regardless of ratio.
        assert _rag_signal(ratio=5.0, trailing_mean=0.02) == "insufficient signal"

    def test_green_at_and_below_1_5x(self):
        assert _rag_signal(ratio=1.5, trailing_mean=0.10) == "Green"
        assert _rag_signal(ratio=1.0, trailing_mean=0.10) == "Green"

    def test_amber_above_1_5x_up_to_and_including_2_0x(self):
        assert _rag_signal(ratio=1.51, trailing_mean=0.10) == "Amber"
        assert _rag_signal(ratio=2.0, trailing_mean=0.10) == "Amber"  # inclusive upper bound

    def test_red_strictly_above_2_0x(self):
        assert _rag_signal(ratio=2.01, trailing_mean=0.10) == "Red"
