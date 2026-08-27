# Market Intelligence Platform — Context & Process Summary (for external review)

**Purpose of this document:** a self-contained brief for a reviewer with no prior context on this project. It covers the role being interviewed for, the case study brief the candidate was assessed against, the solution built, the process followed (including AI-agent collaboration), and the presentation prepared for a 20-minute panel readout. A list of open questions/tensions worth a second opinion is at the end — that's the most useful section to focus feedback on.

---

## 1. The role

**Position:** Associate Director, Senior Data Analytics / BI Specialist ("Data & Analytics Engineering Lead"), Corporate Operations Group — Market Services, Macquarie Group, Sydney.

**Core framing from the JD:** Market Services is replacing manual, fragmented post-trade operations with a digital-first, event-driven platform. The role has an explicit **dual mandate**:
- **Internal:** define how the business measures itself — automated, real-time OKRs/operational metrics replacing narrative-led reporting.
- **Product:** shape how analytics gets embedded into every product the team builds — "built in, not bolted on."

Recurring JD language worth noting because it shows up in the case study rubric too:
- "Data as infrastructure. Not dashboards. Not reports."
- "Challenge every report: if a human is reading a number and making a decision, ask whether the system should be making that decision instead."
- "Lead a team that blends data engineers, analysts, and AI agents... set the standard for how data teams work in a human-agent hybrid model."
- Must-have: "technical enough to build, articulate and influence others" — explicitly not a request for someone who only directs others.
- What Success Looks Like: self-service analytics adopted, no manual reporting, "data driving decisions, not decorating them."

**Stated panel feedback going into this round:** candidates so far have shown solid technical execution but have fallen short on stakeholder management, influencing skills, and demonstrating genuine technical leadership (as opposed to "manager who delegates and forgets"). This feedback is the single biggest driver of recent changes to the presentation (see §5).

---

## 2. The case study brief (verbatim requirements)

Source: `Data-Analytics-Engineering-Lead-Case-Study.docx`. Fictional context: candidate joins "Really Big Bank" as lead of a small team of analysts/engineers, building a first proof-of-concept to help management understand market trends. Scope is deliberately constrained: **2 data sources, 2–3 metrics, 1 dashboard.** Four assessed parts, one optional/unassessed bonus part.

**Part 1 — Data Pipeline**
- Pick exactly 2 sources: one macro series + one market index series, from FRED / RBA / Yahoo Finance / Alpha Vantage.
- Ingest on a scheduled or repeatable basis; separate storage from transformation; handle at least one failure scenario; log DQ outcomes (no silent drops); must run locally with a README.
- *AI Agent Lens:* if used, presentation must include an example of the agent producing incorrect/incomplete output and how the problem was identified.
- *Leadership Lens:* presentation must explain how this would be handed off **to a junior engineer** — standards, documentation, guardrails, and how that extends to AI-generated code.

**Part 2 — Data Curation**
- 2–3 calculated metrics; join/align sources on a common time axis with date/timezone handling made explicit; document one real DQ issue and its fix.
- *AI Agent Lens:* metric requirements must be defined in plain language *before* the agent writes transformation logic — that definition must be in the submission.
- *Leadership Lens:* be ready to discuss how you'd set and enforce data modelling standards.

**Part 3 — Management Dashboard**
- Audience: financially literate, non-technical. Must answer: *"How has market activity trended over the past 90 days, and is there anything we should be watching?"*
- Must include: (a) index volume/price over 90 days with a rolling average overlay, (b) a macro overlay showing correlation or divergence, (c) one Red/Amber/Green signal with a justified threshold.
- *AI Agent Lens:* note how the prompt/output was iterated to suit the audience.
- *Leadership Lens:* discuss how you'd help a team of analysts present information that conveys a story.

**Part 4 — Presentation** (≤20 minutes, must include):
Framing → Pipeline walkthrough (layers, error handling, **handoff approach**) → Data decisions (transforms/exclusions/assumptions) → Dashboard demo → AI agent reflection (**both** overridden/corrected *and* accepted, explained) → Team and standards (**how you'd contribute to building and leading the team**) → If you had more time (1–2 concrete next steps).
Also: be prepared to discuss **team leadership and prioritisation trade-offs**.

**Part 5 — Bonus (optional, not assessed):** one slide max on how the candidate, as engineering lead, would partner with a data product owner to take a new data product from concept to delivery, including how they'd influence decisions with data insights.

**Submission:** GitHub repo + dashboard link. README must include setup steps, key design decisions, a note on handing the work to a team member, and an AI agent log.

---

## 3. The solution built

**Stack:** local Python pipeline + Streamlit dashboard, single DuckDB file (`data/warehouse.duckdb`), no cloud dependency.

**Sources chosen:** RBA Cash Rate Target (macro) + ASX 200 OHLCV via Yahoo Finance (market index) — the pairing the case study itself points toward, and a natural fit given the fictional context is a Sydney-based bank.

**Layering:** `data/raw/` (immutable Parquet, untouched source columns) → `raw.*` DuckDB tables → `silver.*` (typed, deduplicated, validated, with a parallel `*_quarantine` table per source) → `curated.*` (a small star schema — `dim_date` + `fact_market_daily` / `fact_macro_daily` / `fact_metrics_daily` — plus `aligned_daily` / `metrics_daily` built as required by the literal brief, now as joins over the facts). The 3-layer split (raw/silver/curated) was **not** the agent's proposal — the first working version was a simpler 2-layer raw→curated design; the split was directed once the DQ spec needed an explicit layer to quarantine failed rows without touching raw.

**Metrics** (defined in plain language in `docs/metric_definitions.md` *before* implementation, per the case study's AI Agent Lens requirement):
1. 20-day rolling average volume (window not specified in brief; chosen as a ~monthly convention).
2. Day-over-day rate of change (%).
3. 14-day annualised volatility (`stdev(log_return, 14) × √252`) — the one window the brief specifies directly.
4. RAG signal, derived from volatility: Green ≤1.5× its own 90-day trailing average, Amber ≤2.0×, Red >2.0×, plus a distinct "insufficient signal" state when the 90-day baseline is unusually low (guards against a false Red from a near-zero denominator) and a "not yet available" state during the ~104-trading-day warm-up.

**Data quality:** 13 checks total (6 on RBA, 7 on ASX200 — completeness, valid range/values, internal consistency, freshness, no-duplicates, plus source-specific checks including an explicitly `not_applicable` index-composition check, since the current source has no constituent-count field). Failed rows are quarantined with a reason, not dropped; warned rows are kept and tagged. Every run logs to `dq_log` (per-stage) and `dq_validation_log` (per-check). **The real pipeline has quarantined 0 rows to date** — see §6 for how that's handled honestly rather than papered over.

**Two real bugs found and fixed while building the DQ suite** (both now have pytest regression tests, not just narrated history):
1. A missing RBA rate was silently miscounted as "out of range" (`pandas.Series.between()` treats `NaN` as `False` when negated) — split into two distinct checks.
2. An empty quarantine table got the wrong DuckDB column type (`INTEGER` instead of `VARCHAR`) due to pandas' dtype inference on an empty `.apply()` result — fixed with explicit `.astype()` calls forced even on the empty path.

**Dashboard** (3 Streamlit pages, reads only `curated.metrics_daily` per the brief's literal contract):
- **Market overview:** KPI row (latest close with its date, 90-day change, 90-day range as a ±% band, volatility signal) + an auto-generated rule-based bottom-line sentence; price/volume chart with 20-day rolling average, outlier-capped volume axis; macro overlay — ASX 200 and RBA cash rate each on their own axis (ASX in points, rate in %), the rate drawn as a step line since it's genuinely constant between RBA decisions; RAG badge plus a 90-day history strip.
- **Data statistics & quality:** live status badges per check, a DQ trend chart, and a synthetic worked example (a deliberately invalid row run through the real `_validate_asx200()` function) proving the quarantine mechanism works, honestly labeled as a synthetic test since the real pipeline has never actually quarantined a row.
- **Appendix:** plain-language explainer mirroring `docs/metric_definitions.md` — one source of truth, not two.

---

## 4. The AI-agent collaboration process

Full turn-by-turn record: `docs/ai_agent_process_log.md` (12 entries). Key shape of the process:

- **Ownership split:** the lead owns source/metric selection, threshold rationale, rubric compliance against the actual brief text (not a paraphrase of it), metric definitions written before any code, and data modelling standards. The agent owns scaffolding, implementation once a spec is approved, test-writing against a locked spec, and running things against real data to report actual numbers back.
- **Review was iterative, not one-pass.** The RAG rule alone went through three revisions: a first draft (Entry 3) → a boundary clarification and near-zero-denominator guard once a real failure mode was identified (Entry 11) → a lookback-window fix after the module was actually run against real data and returned 0/103 populated rows despite computing with zero errors (Entry 12). Every catch came from checking real output, not re-reading code.
- **Real environment friction, handled transparently, not hidden:** a GitHub PAT arrived in plaintext in chat (flagged, never persisted, rotation recommended); a synced/sandboxed filesystem couldn't support git's lock-file behavior, discovered via a loud error rather than silent corruption, and worked around by building on local disk and verifying via a full zip/unzip round-trip; a second agent session (VS Code's Claude Code extension) began working the same repo concurrently mid-build, handled by explicitly splitting file ownership rather than letting both write to `src/`.
- **"Raw means raw" was a real correction, not an agent self-catch:** the extractors were initially narrowing/renaming columns before writing to `data/raw/` — technically raw in name, not in fact. Caught on direct review and corrected to persist every source column untouched.
- **Design-doc-before-code gate applied consistently:** metric definitions, then the mart/star-schema design, both went through a written proposal reviewed before implementation — this is also positioned as the actual handoff artifact for a new team member or agent, not a separate onboarding document.

---

## 5. The presentation

12 slides (`presentation/build_deck.js` generates the `.pptx`; `presentation/speaker_script.md` is the full ~20:30 narration). Structure follows the case study's required sections. The most significant recent work was a **deliberate reframing driven by the panel's stated feedback** (technically strong candidates, weak on stakeholder/leadership evidence):

- **Slide 2 (Framing)** now opens with the JD's own dual-mandate language (internal instrumentation vs. product analytics embedding) before stating the case study's question — positions the whole build as a compressed demo of one half of the actual role, not a generic exercise.
- **Slide 8 (AI agent reflection)** was corrected so the raw/silver/curated layering is attributed accurately — it was the candidate's own directed decision, not an agent proposal that was simply accepted. (This came from an explicit user correction mid-session: "I decided to create raw, silver, curated.") Both Corrected and Accepted columns are now grounded in specific, defensible log entries rather than generic claims.
- **Slide 9 (Team & standards)** was rebuilt twice. First pass: a retrospective "what I owned vs. what the agent owned" table. Second, more significant pass: reframed entirely around the user's own clarification that the case study is testing *"how I, as lead, will be contributing... not just a manager who is delegating and forgetting"* — now structured as four modes (**Architect, Hands-on engineer, Quality gate, Coach & scale-enabler**), each grounded in real evidence from this specific build (the raw/silver/curated call, the raw-fidelity fix, the two real DQ bugs, the design-doc gate and mid-build file-ownership split).
- **Slide 11 (Real stakeholder influence)** replaced generic "leadership lens" bullet points with two real career stories supplied by the candidate: Bigtincan (convinced a product team to build a reusable self-serve data model instead of a 1:1 legacy-reporting migration, under a licence-renewal deadline) and Allianz (currently driving a reusable actuarial-automation architecture across three product lines, working the plan through with stakeholders before building).
- **Slide 12 (Closing)** reframed around the JD's own "What Success Looks Like" language rather than a generic thank-you.

Deck and script are kept in sync deliberately — every content change to a slide is mirrored in the narration, and total runtime is tracked from actual word counts (not guessed) to stay near the 20-minute limit.

---

## 6. How honesty-under-scrutiny is handled

Two places where the natural interview pressure is "make this sound more impressive than it is," handled by leaning into the honest answer instead:

- **"You've never actually had a DQ failure — so how would you know you can handle one?"** Answer built from three real, verifiable things: (1) warnings *do* fire routinely (missing business days = public holidays) — the DQ system is exercised every run, just at a softer severity tier; (2) two real bugs were caught and fixed *in the validation logic itself* during build, which is arguably a harder failure mode to catch than a bad data row, since nothing crashes; (3) the quarantine path itself is proven via a synthetic worked example that runs a deliberately invalid row through the actual production validation function, honestly labeled as synthetic rather than presented as a real event.
- **Slide 9's "trade-off I made"** names a real, specific choice (depth on data-quality validation over building the flexible `fact_daily_long` reporting layer) with an explicit reason (a wrong number shown to management costs more than a missing nice-to-have), rather than a vague, unfalsifiable answer.

---

## 7. Open questions / worth a second opinion

1. **"Junior engineer" vs. "team member."** The case study's Pipeline Leadership Lens asks specifically how the work would be handed off *to a junior engineer* — standards, documentation, guardrails, and how that extends to AI-generated code. The README's Handoff Notes section covers this content well, but the deck/script consistently say "new hire," "team member," or "a person or an agent" rather than "junior engineer" specifically. Is that a distinction worth making explicit, in case the panel probes "does your approach still work for someone genuinely early-career, not just a generic new hire"?
2. **The Bonus Question (Part 5) is unassessed and currently not in the deck at all** — it was previously a placeholder "leadership lens" slide that got replaced with the real Bigtincan/Allianz stories (Slide 11), which is a different question (real influence examples) than the bonus question's specific ask (partnering with a *data product owner* from concept to delivery). Is it worth a short verbal answer in reserve for Q&A even though it's not required, given the JD's own product-analytics mandate makes it relevant?
3. **Depth of the "prioritisation trade-offs" answer.** The case study explicitly says "be prepared to discuss team leadership and prioritisation trade-offs" (plural) — the deck currently has one named trade-off (depth vs. breadth on DQ). Worth having at least one more in reserve — ideally a trade-off involving *people* (e.g., a resourcing call across a team), not just this candidate's own solo time allocation, since the leadership framing is otherwise entirely about individual judgment calls.
4. **The RAG signal's correlation sentence currently reports "little relationship" (≈0.14) between ASX 200 and the RBA cash rate in the visible window.** This is honest and real, but worth confirming the candidate is comfortable with a panel question like "so your headline macro overlay found nothing interesting — was this the right pairing?" A prepared answer should distinguish "no correlation in this particular 90-day window" from "the pairing itself was wrong" (rate changes are lagging/anticipatory, not necessarily contemporaneously correlated with price).
5. **Two virtual environments existed in the repo (`.venv` and a stray broken `venv`)** during this session — now resolved, but worth double-checking nothing else in the repo (stray branches, uncommitted local-only state) would surprise the candidate live during the demo. A pre-interview `git status` and a clean `streamlit run` dry run is cheap insurance.
6. **Everything demonstrated is local-only** (no hosted deployment). The case study explicitly allows this ("must be able to run locally"), and Slide 10 deliberately deprioritises hosting as out of scope for a local submission — but worth being ready for "what would make this production-grade" beyond the two named next steps (the flexible `fact_daily_long` layer, the full RBA meeting calendar).
