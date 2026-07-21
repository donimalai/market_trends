"""
metrics.py

Computes the platform's three metrics plus the RAG signal, on top of
curated.aligned_daily.

IMPORTANT: the plain-language metric definitions live in
docs/metric_definitions.md and are authored BEFORE this implementation,
independent of any AI agent used to write this file. This module must
implement exactly what's specified there — it does not redefine or
reinterpret the metrics itself. See that file for full definitions,
formulas, edge cases, and the RAG threshold rationale.

Responsibilities (to be implemented):
- rolling_avg_volume_20d — 20-day rolling average of ASX200 volume.
- rate_of_change_pct — day-over-day % change in ASX200 close price.
- volatility_14d_annualised — 14-day rolling stdev of log returns of close
  price, annualised (x sqrt(252)).
- rag_signal — Green/Amber/Red per the threshold logic in
  docs/metric_definitions.md.
- Write result to DuckDB table curated.metrics_daily.

NOT YET IMPLEMENTED — scaffold only.
"""

def compute_metrics():
    """Compute all metrics + RAG signal from curated.aligned_daily, write curated.metrics_daily."""
    raise NotImplementedError


if __name__ == "__main__":
    compute_metrics()
