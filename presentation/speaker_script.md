# Speaker script — Market Intelligence Platform

Target: 20 minutes total, including one live demo section — this script runs to about 20:30 with no slack, so know it well enough to compress on the fly rather than speed-read. Timings are cumulative. If you're running over at a checkpoint, trim Slide 3's pipeline description or Slide 5's bug-detail depth first — both are useful context but not graded evidence on their own. Never cut or rush Slide 8 (AI reflection), Slide 9 (your leadership operating model — architect, hands-on engineer, quality gate, coach — this is the direct answer to "how would you build and lead the team," not just delegate to it), Slide 11 (real stakeholder influence — your direct answer to the influencing gap the panel is testing for), or the demo.

Plain-language rule throughout: no function names, no library names, no code. If a senior manager would ask "what does that mean," say it the way you'd answer them, not the way you'd write it in a commit message.

---

## Slide 1 — Title (0:00–0:30)

> Good morning / afternoon, everyone. I'm going to walk you through a local data pipeline and dashboard I built that tracks ASX 200 market activity alongside the RBA cash rate — built for exactly the audience in this room: financially literate, but you shouldn't need to read a data pipeline to understand it.
>
> Twenty minutes, then happy to take questions and show you the dashboard live at any point you want to dig in.

*[Advance]*

---

## Slide 2 — Framing (0:30–2:15)

> Before I get into this specific build, one framing point. This role has two mandates — instrumenting how the business measures itself internally, and shaping how analytics gets embedded into every product you ship. What I'm walking you through today is a compressed version of the first one. The same thinking — instrumented, self-service, no analyst in the loop — is exactly what I'd extend to the second.
>
> With that said — let's start with the question this whole thing answers: *"How has ASX 200 market activity trended over the past 90 days, and is there anything we should be watching?"*
>
> Here's why that matters in practice: rate decisions and market swings don't always show up together right away. If you're only looking at price, or only looking at rate announcements, you can miss the moment they start to diverge — and that gap is exactly the kind of thing you want to catch while it's still one line on a chart, not something you're reading about after the fact.
>
> I built this for financially literate, non-technical management — one clear takeaway per chart, no jargon, nothing you need me in the room to interpret.
>
> RBA cash rate and ASX 200 was the pairing the case study itself pointed toward, and it fits naturally given this is a Sydney, market-services context.
>
> And the underlying philosophy — this is data as infrastructure, not a one-off report. Instrumented, observable, self-service from day one — the same standard I'd hold a product to.

*[Advance]*

---

## Slide 3 — Pipeline walkthrough (2:15–3:45)

> So how does the data actually get from source to that dashboard? Five stages, left to right.
>
> Raw files land first, untouched — literally every column the source gives us, nothing cleaned or filtered yet. That goes into a raw database layer, still untouched, just organized. Then a validation layer — this is where every row gets checked, typed properly, and cleaned. Then a business-ready layer, which is what the dashboard actually reads from. And the dashboard itself, three pages, which I'll show you shortly.
>
> Three things worth knowing about how this is built, not just what it does:
>
> **Layer separation** — raw data is never pre-cleaned. Every source column survives untouched, so if a requirement changes six months from now, I'm not re-pulling data, I'm just re-processing what's already there.
>
> **Error handling** — nothing fails silently. Every stage logs its outcome. And if a row fails a serious check, it gets set aside with the exact reason — it's never just dropped, and it's never let through to break something downstream.
>
> **Handoff approach** — adding a new data source follows one fixed pattern, every time. Data quality logging lives in two tables, not somebody's memory. And any structural change to the data model needs a written proposal reviewed before anyone writes code against it.

*[Advance]*

---

## Slide 4 — Data decisions (3:45–5:30)

> Four measures, and I want to be upfront about why each one is the size it is, because none of these were handed to me — I had to decide.
>
> A 20-day rolling average of trading volume — that's not in the brief, I chose it because it's roughly a month, long enough to smooth out noise, short enough to still react to something real happening.
>
> Day-over-day rate of change — the simplest up-or-down signal, deliberately the shortest window we have.
>
> 14-day volatility, annualised — that one *is* specified in the brief.
>
> And the traffic-light signal — green at or under one and a half times its own 90-day average volatility, amber up to two times, red above that. That one's deliberate in a specific way: the system makes the call, not the reader — nobody has to look at a volatility number and decide for themselves whether it's high. That's the same instinct behind "challenge every report" — if a human's reading a number to make a decision, ask whether the system should just make it.
>
> Two more things I want to be transparent about. What we *excluded*: I looked at adding inflation data as a second macro indicator, and deliberately left it out — the brief wants one macro series, and inflation only updates quarterly, which doesn't suit a 90-day view. And assumptions — there are nine places where the brief was silent and I had to make a call. All nine are documented, not buried, in the appendix page of the dashboard.

*[Advance]*

---

## Slide 5 — Data quality approach (5:30–7:00)

> No silent failures, by design. Eight separate stages log their outcome on every single run. Both data sources go through thirteen quality checks between them. And — I'll be honest about this — two real bugs got caught and fixed while I was building this, not hypothetical ones.
>
> Here's how a row actually moves through validation: if nothing's flagged, it passes straight through. If something's unusual but not necessarily wrong — say, a business day with no data, which is almost always just a public holiday — it gets flagged but kept. If something's seriously wrong, it gets set aside, quarantined, with the exact reason attached, never silently dropped.
>
> The two bugs, quickly: one validation check was mistaking a *missing* value for an *implausible* one — I caught that by looking at the actual flagged row, not just trusting the summary count. And separately, an empty results table was quietly getting the wrong data type behind the scenes — caught by checking the structure, not just the row count. Both are the kind of thing that looks fine until the day it isn't, and both are now fixed with tests behind them so they can't silently come back.

*[Advance — this is a good moment to say "let me show you," and switch to the live dashboard]*

---

## Slide 6 & 7 — Dashboard demo (7:00–11:15) — LIVE DEMO

*[Switch to the browser now. Speaker notes on these two slides have the fallback plan if the live demo doesn't come up — have a screenshot ready regardless.]*

> Let me actually show you this rather than describe it.
>
> *[Market overview page]* Top of the page — latest close, the 90-day change, the range expressed as a plus-or-minus percentage so it's actually meaningful at a glance, not just two numbers you have to do math on, and the current volatility signal. Underneath, one sentence that pulls all of that together automatically — that's rule-based, not AI-generated text, fully reproducible from the numbers themselves.
>
> *[Scroll to price/volume chart]* Price and volume, with that 20-day average overlaid — and notice the volume axis is deliberately capped so a couple of extreme spikes don't flatten out the actual trend.
>
> *[Scroll to macro overlay]* This one changed shape during review, worth mentioning: it used to be two lines on two separate scales — price and rate — which technically works but takes real effort to read. Now it's one line, ASX 200, with the cash rate shown as shaded bands in the background, labeled with the rate. Same information, much less translation required.
>
> *[Scroll to RAG signal]* And the signal itself — today's read, plus a strip underneath showing every day's color for the last 90 days, so you can see at a glance whether it's been calm the whole time or just turned that way yesterday. Those are very different stories.
>
> *[Switch to Data statistics & quality page]* Second page — this is the same data-quality story from a couple of slides ago, but live. Color-coded status on every check, a trend across recent runs so you can see this is continuously monitored, not a one-time check, and — I actually built this in specifically — a worked example proving the quarantine mechanism works, by deliberately breaking one row and running it through the real logic. I'm upfront on the page that it's a synthetic test, because the real data hasn't actually failed yet.
>
> *[Switch to Appendix page]* And a third page for anyone who wants the detail behind any of this, in plain language.

*[Return to slides]*

---

## Slide 8 — AI agent reflection (11:15–13:30)

> I used an AI agent throughout this build, and I want to be specific about where I stepped in and where I didn't — both halves matter.
>
> Corrected, three examples — and I want to be precise about ownership on the first one, because it's easy to over-credit the agent here. The three-layer raw, silver, curated model was *my* call, not the agent's design — its first version was a simpler two-layer pipeline, and I directed the split once the data-quality spec needed a layer to quarantine failed rows without touching raw. Second: the raw layer wasn't actually raw — the extractors were narrowing and renaming columns before writing to it. I caught that on review, not the agent catching it itself, and corrected it to persist every source column untouched. Third: the volatility signal ran with zero errors but was completely empty — caught by checking the real count, not that nothing crashed, fixed with a properly sized lookback window.
>
> Accepted, three examples, and this is the half that's easy to leave out but shouldn't be. The metric-definitions draft — accepted as the starting point, including three open judgment calls the agent flagged rather than silently defaulting on, which I then decided myself. The mart design doc — a star-schema proposal written before any code, walked through with two judgment calls before I approved it — not accepted blind, but the design itself needed no rework. And how it handled hitting a wall: when a sandbox limit blocked it mid-task, it stopped, said exactly what failed, and asked rather than guessing — the default response I trusted without needing to correct it.
>
> The honest version of this: the agent earned trust on structure and first drafts. I stayed the one deciding what's actually correct, and specifically anything a non-technical reader would take at face value.

*[Advance]*

---

## Slide 9 — Team & standards (13:30–16:00)

> I want to be direct about what "lead" means here, because it isn't "I'd manage and delegate." As lead, I'm accountable for the standard — clear design up front, hands-on involvement where the risk is highest, and guardrails that let analysts, engineers, and AI agents deliver safely at pace. That's four modes, not one.
>
> Architect: I define the data model, the layer boundaries, the metric definitions, and the acceptance criteria before code starts. The raw, silver, curated split and every metric definition in this build were mine — decided before anyone touched implementation, not proposed by whoever happened to be building it.
>
> Hands-on engineer: I build or co-build the highest-risk parts myself — source contracts, transformation logic, DQ controls, the dashboard's actual semantics. Here that meant directing the fix when the raw layer wasn't actually raw, and personally sizing the RAG lookback window, not just approving someone else's fix after the fact.
>
> Quality gate: I review output from analysts, engineers, and agents the same way — against correctness, real data, and a definition of done — before anything is accepted. That's the same bar that caught two real data-quality bugs and a signal that ran with zero errors but returned zero rows.
>
> Coach and scale-enabler: I build reusable patterns, design docs, and guardrails so a team delivers consistently without tribal knowledge. The design-doc-before-code gate isn't just a personal habit — it's the actual onboarding artifact, and it's exactly how I split file ownership the moment a second contributor started working the same repo mid-build.
>
> One trade-off I want to name directly, because you asked me to be ready to discuss these: I prioritized depth on data quality — the checks, the quarantine mechanism, a proven worked example — over breadth. A more flexible reporting layer stayed a design document instead of working code. I made that call because a wrong number shown to management costs a lot more than a missing nice-to-have feature. Different context, different call — but that's the reasoning, and I'd defend it.

*[Advance]*

---

## Slide 10 — If I had more time (16:00–17:00)

> Two things, ranked, not four — because a list without a ranking isn't actually a plan.
>
> Priority one: that flexible reporting layer I just mentioned. It's the highest-leverage thing left, because it unblocks *every* future dashboard request without more pipeline work — build it once, every future chart is a query, not a project.
>
> Priority two: the full RBA meeting calendar, not just the dates the rate actually changed. Markets can react to a *hold* and its guidance just as much as an actual move — that's a real gap in the "anything to watch" story, and it's cheap to close.
>
> Two things I'm deliberately leaving off that list: real scheduling, and a hosted deployment. Both matter eventually. Neither matters yet — this is a local submission, not a production rollout, and solving them now would be effort spent ahead of actual need.

*[Advance — if running short on time, skip to Slide 12 here]*

---

## Slide 11 — Real stakeholder influence (17:00–19:00)

> Everything so far has been this pipeline. I want to close with two examples of the same thinking applied to actual people, not just data — because that's a different skill, and I want to be direct about having used it.
>
> First, Bigtincan. As Head of Data, I had a mandate to migrate legacy reporting onto a modern BI platform on Databricks — over 300 customers globally depending on it, and a hard deadline, because we were about to renew a software licence we were trying to get off of. The easy path was a like-for-like migration — rebuild every existing report, one for one. I pushed back on that. I proposed instead defining the higher-level reporting requirements and building a reusable data model, so customers could build their own new reports rather than wait on us to rebuild the old ones. That meant convincing the product team to trade migration speed for something slower up front but genuinely self-serve. They agreed, and that's the direction it went.
>
> Second, and this one's current — Allianz. I'm driving automation of the actuarial reserving process, and the complexity is that it spans three product lines: general insurance, CTP, workers comp — each with different rules. The requirement I pushed for was one architecture, not three bespoke builds — reusable components that work across all three. Before any of that got built, I worked the plan through with business stakeholders directly, and designed the self-serve capability in from the start rather than retrofitting it later.
>
> Same pattern both times: don't take the literal ask at face value, make the case for the version that scales, and do that convincing *before* you start building, not after.

*[Advance]*

---

## Slide 12 — Closing (19:00–20:30)

> Zoom out for a second on what this scales to. Same standard, larger canvas: real-time metrics leaders actually use, not manual reporting. Analytics built into every product from day one, not bolted on after. Data that drives decisions, not decorates them.
>
> That's the walkthrough. Repository link and how to run it locally are both on screen.
>
> Happy to take questions, and if anyone wants to drive the dashboard themselves rather than watch me do it, I'm glad to hand it over.

---

## Delivery notes

- **Rehearse the demo separately from the slides.** Time it on its own — it's the part most likely to run long or hit a snag.
- **Have a screenshot backup** of both dashboard pages in case the live version doesn't come up cleanly — don't let a technical hiccup eat your Q&A time.
- **If asked "why didn't you use AI for X"** (the definitions doc, the thresholds) — that's your answer already on Slide 8/9: spec and judgment calls stayed with you by design, not by accident.
- **If pushed on the trade-off** in Slide 9 — have one more sentence ready: *"If the priority had been showing breadth of capability rather than trustworthy numbers, I'd have made the opposite call — that's a business decision, not a technical one."*
