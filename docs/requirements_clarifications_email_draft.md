# Draft email — requirements clarifications & assumptions for confirmation

*(Copy into email client, adjust recipient/tone as needed. Sourced from the full turn-by-turn record in `docs/ai_agent_process_log.md` — this is the distilled, audience-facing version.)*

---

**Subject:** Market Intelligence Platform — requirements clarifications & assumptions, need your confirmation before I finalize

Hi [name],

Before I lock this in, I wanted to summarise the requirements questions I raised during the build, the assumptions I made where I couldn't get an answer immediately, and a couple of real issues the review process caught. Flagging all of it now rather than after submission — want your confirmation on the assumptions specifically.

## Questions I asked before building, not after

1. **RAG threshold boundary ambiguity.** The original brief said "amber between 1.5x and 2x" without saying which side owns exactly 2.0x. Rather than picking one silently, I resolved it explicitly before implementation: amber is now `>1.5x and ≤2.0x`, red is `>2.0x` — every value maps to exactly one band. Two more rules got folded in at the same time: a distinct ~104-trading-day warm-up period for the RAG signal (it needs both a 14-day figure *and* a 90-day trailing average of that figure, longer than the other metrics' warm-up), and a 3%-annualised volatility floor below which the signal reports "insufficient signal" instead of a potentially false Red during an unusually calm stretch.

2. **Raw layer scope.** When I was told "raw data must be saved in its original format, no changes," I asked whether that meant keeping every source column (typed but unmodified) or narrowing to just the columns this platform uses, before touching any code. Confirmed: keep every column, original names — cleaning/selection happens downstream instead.

3. **Data-quality validation column scope.** Same question, applied a second time when building the full DQ validation suite: confirmed the RBA checks should validate `Cash Rate Target` (which pairs with a "change from previous" column) rather than `Interbank Overnight Cash Rate` (used elsewhere), since that's the field that actually matches the requested checks.

4. **Flexible data model for custom dashboards.** Rather than just widening the two required dashboard tables, I proposed a small star schema (a date dimension + fact tables) as a written design doc first, and got sign-off on the shape before writing `align.py`/`metrics.py` against it. The two literally-required tables still exist unchanged; the flexible layer sits underneath them.

5. **ASX200 lookback window.** Flagged (with numbers, not just "let's use more data") that the spec's original 120-day lookback only yields ~83 real trading rows after weekends/holidays — below what the dashboard's own 90-day requirement needs — and got confirmation before widening it.

## Assumptions I made — need your confirmation

- **`cash_rate` = RBA's "Cash Rate Target"**, not "Interbank Overnight Cash Rate." These track closely but aren't identical; I went with Cash Rate Target since it's what's actually announced/reported as "the cash rate."
- **3% annualised volatility floor** for the RAG "insufficient signal" state — set well below any level ASX200 has historically sustained, so it's a sanity guard, not an everyday state. Confirm the number specifically.
- **220-calendar-day ASX200 lookback** (up from the spec's original 120) — sized so the RAG signal's ~104-trading-day warm-up clears with margin, plus the dashboard's 90-day window has a gap-free rolling-average overlay.
- **Business-day-based completeness checks** for both sources — I can't distinguish a real data gap from a public holiday without pulling in an external holiday calendar, so gaps are reported as a count, not hard failures.
- **"Index composition" check (RBA / ASX200-count validation) is marked not-applicable** — the current ASX200 source (Yahoo Finance OHLCV) doesn't carry a constituent-count field at all; enforcing it for real would need a new data source.

## Two real issues the review process caught (not hypothetical)

- A data-quality check I built to flag implausible cash rate values was initially miscounting *missing* values (today's not-yet-published rate) as *out of range* — caught by inspecting the one flagged row rather than trusting the summary count, and fixed by splitting it into two separate checks.
- After finalizing the RAG rule above, I ran it against real pipeline data before considering it done — and found the RAG signal was 0% populated, one trading day short of the warm-up minimum. That's what actually drove the lookback-window change, not a guess.

Let me know if any of the assumptions above need to go a different way — happy to adjust before I finalize.

Thanks,
[your name]
