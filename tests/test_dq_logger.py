"""
Tests for src/ingestion/dq_logger.py — log_run and log_validation each
insert exactly one row into a DuckDB file, verified against a temporary
test database, never the real data/warehouse.duckdb.
"""

import duckdb
import pytest

from src.ingestion import dq_logger


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_warehouse.duckdb"
    monkeypatch.setattr(dq_logger, "DB_PATH", db_path)
    return db_path


def test_log_run_inserts_row(temp_db):
    dq_logger.log_run(source="TestSource", row_count=42, status="success", message="ok")

    con = duckdb.connect(str(temp_db))
    row = con.execute("SELECT source, row_count, status, message FROM dq_log").fetchone()
    con.close()

    assert row == ("TestSource", 42, "success", "ok")


def test_log_run_multiple_calls_append_not_overwrite(temp_db):
    dq_logger.log_run(source="A", row_count=1, status="success")
    dq_logger.log_run(source="B", row_count=2, status="failure", message="boom")

    con = duckdb.connect(str(temp_db))
    count = con.execute("SELECT COUNT(*) FROM dq_log").fetchone()[0]
    con.close()

    assert count == 2


def test_log_run_message_defaults_to_null(temp_db):
    dq_logger.log_run(source="NoMessage", row_count=0, status="failure")

    con = duckdb.connect(str(temp_db))
    message = con.execute("SELECT message FROM dq_log WHERE source = 'NoMessage'").fetchone()[0]
    con.close()

    assert message is None


def test_log_validation_inserts_row(temp_db):
    dq_logger.log_validation(
        dataset="TestDataset",
        check_name="test_check",
        status="warning",
        records_checked=10,
        records_failed=1,
        records_warned=2,
        reason="synthetic reason",
    )

    con = duckdb.connect(str(temp_db))
    row = con.execute(
        "SELECT dataset, check_name, status, records_checked, records_failed, "
        "records_warned, reason FROM dq_validation_log"
    ).fetchone()
    con.close()

    assert row == ("TestDataset", "test_check", "warning", 10, 1, 2, "synthetic reason")


def test_dq_log_and_dq_validation_log_are_independent_tables(temp_db):
    dq_logger.log_run(source="A", row_count=1, status="success")
    dq_logger.log_validation(
        dataset="A", check_name="c", status="pass", records_checked=1
    )

    con = duckdb.connect(str(temp_db))
    dq_log_count = con.execute("SELECT COUNT(*) FROM dq_log").fetchone()[0]
    validation_count = con.execute("SELECT COUNT(*) FROM dq_validation_log").fetchone()[0]
    con.close()

    assert dq_log_count == 1
    assert validation_count == 1
