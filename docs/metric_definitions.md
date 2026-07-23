# Metric Definitions — Market Intelligence Platform

Finalized by the engineering lead (human) before any transform code was written or prompted to an AI agent, per the case study's requirement to define metric requirements in plain language ahead of agent-assisted implementation. This is the authoritative spec for `src/transform/metrics.py` — implement exactly what's written here; do not redefine or reinterpret.

---

## 1. Rolling Average Volume (20-day)

**Plain language:** The average number of ASX 200 shares/contracts traded per day, smoothed over the trailing 20 trading days (roughly one calendar month).

**Why it matters:** Daily volume is noisy — a single event can spike it. Smoothing over 20 days shows whether market participation is genuinely trending up or down, which is a proxy for market interest/liquidity.

**Formula:** `rolling_avg_volume_20d[t] = mean(volume[t-19 : t])`

**Edge cases:** First 19 rows of any series won't have a full 20-day window — left as null, not computed on a shorter window (a partial-window average would be misleading rather than genuinely comparable).

---

## 2. Day-over-Day Rate of Change (%)

**Plain language:** How much the ASX 200 closing price moved, in percentage terms, from the previous trading day to today.

**Why it matters:** This is the simplest "is the market up or down" signal, expressed in a way non-technical management immediately understands.

**Formula:** `rate_of_change_pct[t] = (close[t] - close[t-1]) / close[t-1] * 100`

**Edge cases:** First row has no prior day — null, not zero (a zero would misleadingly imply "no change").

---

## 3. 14-Day Realised Volatility (Annualised)

**Plain language:** A measure of how much the ASX 200's daily price swings have been, recently — turned into a single number that can be compared to "normal." Higher means the market has been more turbulent over the past two weeks.

**Why it matters:** Price direction alone doesn't tell you about risk. Two markets can end up at the same price but one got there smoothly and the other via wild swings — volatility captures that difference, which is what risk-aware management actually watches.

**Formula:**
1. Compute daily log returns: `log_return[t] = ln(close[t] / close[t-1])`
2. Take the standard deviation of the trailing 14 log returns.
3. Annualise by multiplying by `sqrt(252)` (252 = approximate trading days/year — this converts a 14-day sample stat into a comparable "annualised" figure, the market-standard convention).

**Formula (combined):** `volatility_14d_annualised[t] = stdev(log_return[t-13 : t]) * sqrt(252)`

**Edge cases:** Needs at least 14 trading days of log returns before it's valid — first ~14 rows will be null.

---

## 4. RAG Signal (derived from volatility)

**Plain language:** A simple traffic-light flag on current market turbulence, so a non-technical reader doesn't have to interpret a raw volatility number.

**Threshold logic (finalized):**
- **Green:** current 14-day volatility ≤ 1.5× its own trailing 90-day average
- **Amber:** current 14-day volatility > 1.5× **and** ≤ 2.0× its trailing 90-day average
- **Red:** current 14-day volatility > 2.0× its trailing 90-day average

The amber band is inclusive on its upper bound (2.0× itself is amber) and red is strictly "greater than" — every possible ratio value maps to exactly one band, with no gap or overlap at either boundary.

**Why a self-relative threshold rather than a fixed number (e.g. "volatility > 20% = red"):** A fixed absolute threshold would need to be re-tuned for every index and every market regime, and what counts as "high" volatility drifts over time (a level that was alarming in a calm decade is unremarkable in a turbulent one). Comparing today's volatility to the market's own recent trailing average instead flags *regime shifts* — the thing management actually wants an early warning for — without needing an externally sourced "normal" baseline. The tradeoff, worth stating openly: this signal is inherently backward-looking (it can't flag danger the first time volatility spikes above its own new normal) and will be less sensitive shortly after a sustained volatile period, since the 90-day average itself will have risen. That's an explicit, documented limitation, not an oversight.

**Warm-up rule (its own, longer null period):** The RAG signal depends on two things stacking: the 14-day volatility figure itself (needing ~14 trading days), *and* a 90-day trailing average computed over already-valid volatility values (needing a further ~90 days on top of that). In practice, RAG signal cannot be produced until roughly **104 trading days** of history exist (14 + 90). This is a distinct, longer warm-up period from the "first 14–20 rows are null" warm-up already noted for the other three metrics above — document and null it separately in `metrics.py` and the dashboard, rather than folding it into the shorter warm-up windows.

**Divide-by-near-zero guard:** If the 90-day trailing average volatility is unusually low (an unusually calm stretch), the ratio `current / trailing_average` can spike sharply on a small, ordinary absolute move — producing a false Red that doesn't reflect real risk. Guard against this with a minimum-volatility floor: if the 90-day trailing mean volatility falls below **3% annualised**, report the RAG signal as **"insufficient signal"** (a distinct fourth state, not folded into Green) rather than computing — and potentially misreporting — the ratio. 3% is set well below any volatility level the ASX200 has historically sustained, so this floor should only ever trigger on genuinely degenerate or edge-case data, not during a normal calm market; treat as a sanity guard, not an expected everyday state. Confirm this number specifically if it looks off before it's hardcoded.

---

## Finalized decisions (previously open questions)

1. **90-day trailing mean:** simple average, not smoothed/weighted.
2. **Warm-up nulls:** left as actual nulls in the data (not backfilled or estimated) for all four metrics; a dashboard chart should simply start rendering from the first non-null point rather than showing a fabricated early value.
3. **Annualisation convention:** 252 trading days/year, as stated in Section 3 — standard market convention, confirmed.
