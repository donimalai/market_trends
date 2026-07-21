# Market Intelligence Platform

Local data pipeline + dashboard: 90-day ASX 200 market trend, watched
alongside the RBA cash rate, for financially literate but non-technical
management. Built as a case study for a Data & Analytics Engineering Lead
role — data as infrastructure, not a one-off report.

**Repo:** private by design (no LICENSE file — this is a case study
submission, not an open-source release; the case study doesn't require a
public repo).

## Overview
_TODO: business question this answers, and why these two sources / this
scope were chosen._

## Setup
_TODO: venv creation, `pip install -r requirements.txt`._

## Run Instructions
_TODO: `python run_pipeline.py` then `streamlit run src/dashboard/app.py`._

## Architecture
_TODO: raw -> DQ log -> transform/align -> metrics -> dashboard, and why
that layering (separating storage from transformation)._

## Design Decisions
_TODO: source choice rationale, metric definitions (link to
docs/metric_definitions.md), RAG threshold rationale, timezone handling
approach._

## Data Quality Notes
_TODO: the one real DQ issue encountered during the actual build, and how
it was fixed. Must reflect what actually happened, not a hypothetical._

## AI Agent Log
_TODO: which files were AI-generated vs. human-reviewed/modified, and one
specific example of an incorrect or incomplete AI output that was caught
and corrected. See ai_agent_process_log.md for the running build log this
gets distilled from._

## Handoff Notes
_TODO: what a junior engineer needs to maintain/extend this — coding
standards, where to add a new source, how DQ logging works, guardrails for
AI-assisted changes. (Written to double as presentation content for the
"pipeline walkthrough / handoff approach" section.)_
