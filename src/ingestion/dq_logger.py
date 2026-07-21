"""
dq_logger.py

Shared data-quality logging utility. Every extraction run — success,
warning, or failure — writes exactly one row here. No silent failures.

Responsibilities (to be implemented):
- Connect to data/warehouse.duckdb; create table `dq_log` if missing, with
  columns: run_id (uuid), run_timestamp, source, row_count, status
  (success/failure/warning), message.
- Expose log_run(source, row_count, status, message=None) -> inserts a row
  and prints a concise console log line.
- Zero dependency on the extractor modules — extractors import this module,
  never the reverse (avoids circular imports).

NOT YET IMPLEMENTED — scaffold only.
"""

def log_run(source: str, row_count: int, status: str, message: str = None):
    """Insert one DQ log row and print a console summary line."""
    raise NotImplementedError
