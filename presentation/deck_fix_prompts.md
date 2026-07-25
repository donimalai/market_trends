# Presentation fix prompts — from panel review

Source: mock non-technical panel review against the case study's own presentation
brief. Each prompt below fixes one specific gap the panel called out against a
literal line in the brief — not a style pass.

---

## FIX 1 — Framing: state the business "why", not the source citation

**Gap:** slide 2 said RBA+ASX200 was chosen because "it's the case study's own
suggested pairing" — that's a citation, not a business reason.

**Prompt:** add one line stating the actual business payoff — management can spot
a market/rate divergence while it's still a line on a chart, not a headline —
directly under the existing framing content. Don't remove the audience/source
bullets, add to them.

---

## FIX 2 — Pipeline walkthrough: add error handling + handoff approach

**Gap:** the brief names these as required content for *this* section. Error
handling currently only appears on a disconnected later slide; handoff approach
appears nowhere in the deck at all, despite being fully written in the README.

**Prompt:** restructure slide 3's bottom area from one "why layers are separated"
paragraph into three compact side-by-side callouts: Layer separation (existing
content, trimmed), Error handling (nothing fails silently; quarantine not drop),
Handoff approach (same 4-step pattern to add a source; DQ logging in two tables,
not tribal knowledge; design doc required before any schema change).

---

## FIX 3 — Data decisions: show what was excluded, not just what was built

**Gap:** the brief asks "what did you transform or exclude" — the deck only
answers the "transform" half.

**Prompt:** add a callout: CPI was evaluated as a second macro overlay and
deliberately excluded (the brief wants one macro series; CPI's quarterly cadence
doesn't suit a 90-day view). Add a one-line pointer to the 9 documented
assumptions in the Appendix, so "assumptions" is acknowledged even if not fully
enumerated on the slide itself.

---

## FIX 4 — AI agent reflection: add what was accepted, not just corrected; cut jargon

**Gap:** the brief explicitly requires both halves — "what did you override or
correct? What did you accept? Explain both" — bolded in the brief. The deck
currently only shows 3 corrections, and one of them names a Python function
(`merge_asof`) to a non-technical audience.

**Prompt:** restructure into two labeled columns, Corrected / Accepted, 3 items
each. Accepted column: the raw/silver/mart layering proposal (accepted as
proposed), the RAG self-relative threshold formula (accepted the first-draft
logic, only the exact boundary numbers were refined), the star-schema mart
design (accepted with one structural tweak). Rewrite the merge_asof line in
plain language: "a step that lines up the two data sources by date failed
safely instead of silently misaligning them."

---

## FIX 5 — Team & standards: forward-looking leadership + an explicit trade-off

**Gap:** the brief asks how the presenter would lead a *team* and specifically
flags *prioritisation trade-offs* — the slide only shows a retrospective
delegation table from this build, with no forward-looking statement and no
named trade-off.

**Prompt:** add one line connecting the table to how a human team would be run
the same way (spec/standards owned by the lead, first draft delegated, review
checks intent not just output). Add one explicit, named trade-off: depth on
data-quality validation was prioritized over breadth (the flexible
`fact_daily_long` mart layer), because a wrong number shown to management costs
more than a missing nice-to-have.

---

## FIX 6 — If I had more time: cut to 2 items, ranked, with "why these win"

**Gap:** the brief asks for 1–2 concrete next steps; the deck listed 4 with no
ranking — which is itself a missed opportunity to demonstrate prioritisation.

**Prompt:** cut to 2 items (`fact_daily_long`, full RBA meeting calendar), each
with a one-line "why this over the alternatives" justification, plus a single
line acknowledging the other two ideas (real scheduling, hosted deployment)
were consciously deprioritized for a local case-study submission and why.

---

## FIX 7 — Bonus slide: substance over artifact-counting

**Gap:** "two written stakeholder-facing clarification emails" reads as citing
one's own homework rather than demonstrating the partnership behavior itself.

**Prompt:** replace the artifact count with the actual behavior: proactively
flagging when scope had grown beyond what was asked (the CPI addition) and
rolling it back once confirmed unnecessary, rather than quietly keeping it.

---

## Not a slide fix — logistics note

12 content slides + a live dashboard demo is tight for 20 minutes; time a full
run-through including the demo, and have a screenshot fallback ready in case the
live demo hiccups. Added as a speaker note on the demo slides, not a content
change.
