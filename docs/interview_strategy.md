# Interview Strategy — Market Intelligence Platform Case Study

Companion to `docs/context_summary_for_review.md`. That file is the *what happened*; this file is the *what to expect and how to answer*. Built from the case study brief's own rubric categories, the JD's stated priorities, and the panel feedback already given (technically strong candidates, weak on stakeholder/leadership evidence).

---

## 1. What to expect

- **Format:** ~20-minute presentation (hard limit, no slack in the current script), then open Q&A. Assume the panel includes at least one non-technical business stakeholder (the case study explicitly designs the dashboard for "financially literate, non-technical" readers, and the JD stresses influencing skills) — so don't assume every question comes from a technical reviewer.
- **What's already been flagged to you directly:** prior candidates were technically solid but weak on stakeholder management, influencing, and demonstrating real technical leadership vs. "manager who delegates and forgets." Expect the panel to actively probe for this — questions may deliberately try to catch you defaulting back into pure technical description.
- **The rubric is explicit and itemized** (Framing, Pipeline, Data curation, Dashboard, AI agent reflection, Team & standards, More time, plus three separate "Leadership Lens" sub-asks and two "AI Agent Lens" sub-asks). Assume the panel is literally checking boxes against this list — don't let any one item go unaddressed even briefly.
- **Bonus question is optional and unassessed** — low risk either way, but see §4 for a reserve answer in case it comes up in Q&A.

---

## 2. Question bank by rubric category

Each entry: likely question → where your answer already lives → the core point to land.

### Framing

- *"Why this pairing, why this scope?"* → Slide 2 / `speaker_script.md`. Land: the dual-mandate framing (this build demonstrates the "internal instrumentation" half of the role; same thinking extends to product analytics) — don't just justify the technical choice, connect it to the role.
- *"What would you have done differently with more time/data sources?"* → Slide 10. Land: two ranked, concrete items, not a wish list — and the explicit reasoning for what you deliberately left off (real scheduling, hosted deployment) and why that's a correct call for a local case-study submission, not a cop-out.

### Pipeline walkthrough

- *"Walk me through what happens when a source fails."* → Slide 3, README. Land: nothing fails silently — every stage logs an outcome; a failed row is quarantined with a reason, never dropped; a bad *run* logs `failure` and raises rather than returning partial data silently.
- *"Why raw → silver → curated, not just two layers?"* → Slide 8 / Entry 8, 9. Land: this is your own directed decision, not a default pattern — it exists specifically because the DQ spec needed somewhere to quarantine failed rows without touching the raw layer. **Be ready to say this was originally a simpler 2-layer design and you changed it** — that's a stronger story than "I designed it this way from the start."
- **[AI Agent Lens, Pipeline]** *"Give me a specific example of the agent producing wrong or incomplete code, and how you caught it."* → Slide 8, Entry 9/12/7. Have **one crisp example memorized cold** — the strongest is the RAG signal computing with zero errors but populating 0/103 rows, caught by checking the actual row count, not that nothing crashed. Say the mechanism of detection explicitly (ran it against real data, checked real output) — that's the actual answer to "how did you identify the problem," not just "I found a bug."
- **[Leadership Lens, Pipeline]** *"How would you hand this off to a junior engineer specifically — not just 'a team member'?"* → README Handoff Notes, Slide 9. **This is a known gap — prep it directly** (see §5, item 1). Don't just repeat the design-doc-gate answer verbatim; explicitly address what changes for someone genuinely early-career (more pairing on the first instance of a pattern, a written coding-standards doc rather than assuming context, explicit "ask before assuming" norm — same ground rule you set for the agent in Entry 1).

### Data curation

- *"What did you exclude, and why?"* → Slide 4. Land: CPI was evaluated as a second macro series and deliberately dropped (brief wants one series; CPI's quarterly cadence doesn't suit a 90-day view) — naming a real rejected option is stronger than just listing what you kept.
- *"Walk me through the timezone/date handling."* → `align.py`, `docs/requirement_specification.md` §2.2. Land: the specific, verified fact that yfinance's `^AXJO` index is already tz-aware `Australia/Sydney` (not an assumption) — and that this fact is commented explicitly rather than silently relied on, since it isn't true for yfinance tickers in general.
- **[AI Agent Lens, Curation]** *"You said you wrote metric definitions before the agent touched code — walk me through that."* → Entry 3, `docs/metric_definitions.md`. Land: the agent drafted definitions as an explicit first pass ("you write a draft, I decide"), and specifically **flagged open judgment calls rather than silently defaulting** (warm-up null handling, baseline averaging method, annualisation convention) — you decided each one. This is a good example of "what did you accept" that isn't just "the code compiled."
- **[Leadership Lens, Curation]** *"How would you set and enforce data modelling standards on a team?"* → Slide 9 "Architect" mode, Entry 7/8/10. Land: standards enforced structurally (a design-doc-before-code gate for any schema-level decision), not by policy document nobody reads — and give the concrete example (raw-fidelity fix) of a standard being *enforced*, not just stated.

### Dashboard

- *"Why this RAG threshold, why self-relative rather than a fixed number?"* → `docs/metric_definitions.md` §4, Appendix page. Land: state the honest tradeoff unprompted (backward-looking, less sensitive right after a volatile stretch) — volunteering the limitation is more credible than waiting to be asked.
- *"Your correlation sentence says the two series barely correlate — was this the wrong pairing?"* → See §5, item 4. **Prep this one specifically** — don't let "no correlation found" sound like a negative result you're avoiding.
- **[AI Agent Lens, Dashboard]** *"How did you iterate on the dashboard for a non-technical audience?"* → the macro-overlay chart history (two-line/two-axis → shaded bands → back to two-line/two-axis with a step line) is a real, honest iteration story — each version had a specific, stated reason, not just taste. Use it.
- **[Leadership Lens, Dashboard]** *"How would you help a team of analysts present something that tells a story, not just shows data?"* → tie to the KPI row + auto-generated bottom-line sentence pattern (numbers alone don't answer the question; one rule-based sentence synthesizes them into the actual takeaway) — frame this as the *standard* you'd coach analysts toward, not just a feature of this dashboard.

### AI agent reflection (both halves — case study explicitly requires both)

- Have your **Corrected** (3) and **Accepted** (3) examples from Slide 8 memorized at the level of "what happened, how I caught it, what changed" — not just the labels. The panel may ask you to go deeper on any one of the six.
- Likely follow-up: *"What's your rule for what you trust the agent with vs. not?"* → Slide 9. Land: judgment calls and anything a non-technical reader would take at face value stay with you; scaffolding, first drafts once a spec is locked, and running-and-reporting against real data go to the agent.

### Team and standards — expect this to be probed hardest

This is the section the panel has explicitly said prior candidates weakened on. Slide 9's four-mode framing (Architect, Hands-on engineer, Quality gate, Coach & scale-enabler) is your answer — know all four cold, each with its own concrete evidence, not just the labels.

- *"That's a lot of 'I' — where's the actual team in this?"* → Be ready for this pushback directly. Land: the file-ownership split when a second agent session joined mid-build *is* a real team-coordination example, just with an agent standing in for a person — name that explicitly rather than hoping they don't notice the team was small.
- **[Leadership Lens]** *"Discuss a prioritisation trade-off."* → Slide 9's depth-vs-breadth trade-off is prepared. **The brief says "trade-offs," plural — have a second one ready that involves people/resourcing, not just your own time** (see §5, item 3).
- *"What standard would you personally never delegate away?"* → Land on the "Architect" and "Quality gate" modes specifically — schema/metric definitions, and final review of anything stakeholder-facing.

### If you had more time

- Slide 10 is ready — two ranked items with "why this over the alternative," plus an explicit, reasoned deprioritisation of two more (scheduling, hosted deployment). If pushed on "why not just do all four," the answer is effort-ahead-of-need for a local submission — say that plainly rather than getting defensive.

---

## 3. Real stakeholder-influence stories (Slide 11)

Know the **Situation → What I pushed for → Outcome** shape of both cold, since these are your strongest, most senior-specific evidence:
- **Bigtincan:** legacy-reporting migration, 300+ customers, licence-renewal deadline; pushed for a reusable data model over a 1:1 migration; convinced the product team to trade migration speed for genuine self-serve capability.
- **Allianz:** actuarial reserving automation across three product lines; pushed for one reusable architecture over three bespoke builds; worked the plan through business stakeholders before any build started.

Likely follow-ups: *"What was the actual pushback, and how did you overcome it?"* and *"What would you have done if they'd said no?"* — have real specifics ready for both stories, not just the outcome. If you don't have crisp specifics for the pushback/objection-handling moment, that's worth strengthening before the interview — it's the part a senior panel is most likely to probe.

---

## 4. Bonus question — reserve answer (optional, unassessed, but keep one ready for Q&A)

*"How would you partner with a data product owner from concept to delivery?"* — this is a different question from the Slide 11 stories (those are about convincing others of *your* direction; this is about partnering with someone who *owns* prioritisation). A reserve answer should cover: shaping requirements together rather than receiving them as a spec (the same "ask before building" instinct from Entry 1), building to a standard that can be maintained (the design-doc gate, again — it's a genuinely reusable answer across multiple rubric items, which is fine, real standards *should* generalize), and influencing with data specifically (the RAG signal's self-relative design and the auto-generated bottom-line sentence exist so a non-technical reader reaches the right conclusion without translation — "the dashboard argues its own case" is a good line here).

---

## 5. Prep these four specifically before the interview

Carried over from `context_summary_for_review.md` §7 — these are the places your current material is thinnest:

1. **"Junior engineer," not just "team member."** Prepare one sentence that explicitly names what's different about onboarding someone early-career vs. a generic new hire.
2. **A second prioritisation trade-off involving people/resourcing**, not just your own time allocation on this build.
3. **The "no correlation found" answer** for the macro overlay — have language ready that distinguishes "no correlation in this window" from "wrong pairing."
4. **Objection-handling specifics** for the Bigtincan and Allianz stories — the actual moment of pushback, not just the resolution.

---

## 6. Cheat sheet — numbers to have cold

- 2 sources (RBA cash rate, ASX 200), 4 metrics computed (3 required + RAG derived from the 3rd), 3 dashboard pages, 3 DuckDB layers (raw/silver/curated).
- 13 DQ checks (6 RBA + 7 ASX200), 2 real bugs found and fixed (both now have regression tests), 0 rows quarantined in production to date (handled honestly, not hidden — see summary §6).
- RAG thresholds: Green ≤1.5×, Amber ≤2.0×, Red >2.0× of 90-day trailing average volatility; ~104 trading days warm-up; 3%-annualised floor for "insufficient signal."
- 20-day rolling volume window, 14-day volatility window, 252 trading-days/year annualisation convention — all stated as conventions, not brief requirements (except the 14-day window, which the brief specifies).
- Presentation: 12 slides, ~20:30 runtime, demo given a ~4:15 window.
