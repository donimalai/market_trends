# Metric Definitions — Market Intelligence Platform

Drafted by the engineering lead (human) before any transform code was written or prompted to an AI agent, per the case study's requirement to define metric requirements in plain language ahead of agent-assisted implementation. Review, edit, and approve before this is handed to Claude Code as the spec for `metrics.py`.

Once finalized, the approved version should replace the placeholder in `docs/metric_definitions.md` (that file, not this draft, is what `src/transform/metrics.py` must be implemented against).

---

## 1. Rolling Average Volume (20-day)

**Plain language:** The average number of ASX 200 shares/contracts traded per day, smoothed over the trailing 20 trading days (roughly one calendar month).

**Why it matters:** Daily volume is noisy — a single event can spike it. Smoothing over 20 days shows whether market participation is genuinely trending up or down, which is a proxy for market interest/liquidity.

**Formula:** `rolling_avg_volume_20d[t] = mean(volume[t-19 : t])`

**Edge cases to define:** First 19 rows of any series won't have a full 20-day window — decide whether to leave as null or compute on a shorter window (recommendation: null, with a comment explaining why, rather than a misleading partial average).

---

## 2. Day-over-Day Rate of Change (%)

**Plain language:** How much the ASX 200 closing price moved, in percentage terms, from the previous trading day to today.

**Why it matters:** This is the simplest "is the market up or down" signal, expressed in a way non-technical management immediately understands.

**Formula:** `rate_of_change_pct[t] = (close[t] - close[t-1]) / close[t-1] * 100`

**Edge cases to define:** First row has no prior day — null, not zero (a zero would misleadingly imply "no change").

---

## 3. 14-Day Realised Volatility (Annualised)

**Plain language:** A measure of how much the ASX 200's daily price swings have been, recently — turned into a single number that can be compared to "normal." Higher means the market has been more turbulent over the past two weeks.

**Why it matters:** Price direction alone doesn't tell you about risk. Two markets can end up at the same price but one got there smoothly and the other via wild swings — volatility captures that difference, which is what risk-aware management actually watches.

**Formula:**
1. Compute daily log returns: `log_return[t] = ln(close[t] / close[t-1])`
2. Take the standard deviation of the trailing 14 log returns.
3. Annualise by multiplying by `sqrt(252)` (252 = approximate trading days/year — this converts a 14-day sample stat into a comparable "annualised" figure, the market-standard convention).

**Formula (combined):** `volatility_14d_annualised[t] = stdev(log_return[t-13 : t]) * sqrt(252)`

**Edge cases to define:** Needs at least 14 trading days of log returns before it's valid — first ~14 rows will be null.

---

## 4. RAG Signal (derived from volatility)

**Plain language:** A simple traffic-light flag on current market turbulence, so a non-technical reader doesn't have to interpret a raw volatility number.

**Threshold logic:**
- **Green:** current 14-day volatility ≤ 1.5× its own trailing 90-day average
- **Amber:** current 14-day volatility is between 1.5× and 2× its trailing 90-day average
- **Red:** current 14-day volatility > 2× its trailing 90-day average

**Why a self-relative threshold rather than a fixed number (e.g. "volatility > 20% = red"):** A fixed absolute threshold would need to be re-tuned for every index and every market regime, and what counts as "high" volatility drifts over time (a level that was alarming in a calm decade is unremarkable in a turbulent one). Comparing today's volatility to the market's own recent trailing average instead flags *regime shifts* — the thing management actually wants an early warning for — without needing an externally sourced "normal" baseline. The tradeoff, worth stating openly: this signal is inherently backward-looking (it can't flag danger the first time volatility spikes above its own new normal) and will be less sensitive shortly after a sustained volatile period, since the 90-day average itself will have risen. That's an explicit, documented limitation, not an oversight.

---

## Open questions for your review

1. Should the 90-day trailing mean for the RAG threshold be a simple average or itself smoothed/weighted? (Draft assumes simple mean.)
2. Do you want nulls in the warm-up period (first 14–20 rows) surfaced anywhere in the dashboard, or silently dropped from the chart?
3. Any preference on annualisation convention — 252 trading days is standard, but confirm before it's hardcoded.
