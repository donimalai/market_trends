# Draft email — for the business user (non-technical)

*(Copy into email client, adjust recipient/tone as needed. Written for the dashboard's actual audience — financially literate, non-technical management — not a technical reviewer. A more technical/peer-facing version of this exists at `docs/requirements_clarifications_email_draft.md` if needed.)*

---

**Subject:** Market Intelligence Dashboard — a few decisions I've made that I'd like your sign-off on

Hi [name],

The dashboard (ASX 200 trend + RBA cash rate + a volatility signal) is built and working. Before I finalize it, I want to flag a handful of decisions I made along the way where the brief left room for judgment — so you're not seeing any of this for the first time when you open the dashboard.

## What the dashboard shows, and a couple of things to know

1. **The volatility signal (Green/Amber/Red) is relative, not absolute.** It compares today's market turbulence to the market's *own* recent average over the last ~90 days, rather than a fixed number like "20% volatility = red." I chose this because a fixed threshold would need constant re-tuning and doesn't age well — what counts as "high" volatility today looked normal a decade ago. The tradeoff: it's backward-looking, so it won't catch the very first day something unusual starts happening, and it becomes less sensitive for a while right after a genuinely volatile stretch. Happy to walk through this logic live if useful.

2. **There's a fourth state beyond Green/Amber/Red: "Insufficient signal."** During an unusually calm stretch, the math behind the ratio can become unreliable and produce a misleadingly alarming reading. Rather than risk a false alarm, the dashboard will show this instead. It should be rare in practice.

3. **The signal needs about 5 months of trading history before it can be shown at all.** Until then, the badge will say "not yet available" rather than guessing. This only affects a brand-new deployment — once it's been running a while, this won't come up again.

4. **Gaps around public holidays are expected, not a data problem.** Both the ASX and the RBA don't publish on public holidays, so you'll occasionally see the data skip a day. That's normal and doesn't indicate the pipeline failed.

5. **Data currently refreshes when the pipeline is run manually, not automatically.** It's built so it *can* be scheduled (e.g. a daily 7am run before market open), but nothing is scheduled yet in this version. The dashboard always shows the timestamp of the last refresh, so it's clear how current the numbers are.

6. **Market pricing comes from Yahoo Finance**, a free public data source — not a paid/licensed direct exchange feed. Fine for internal monitoring and trend-watching; wouldn't be my recommendation as the source of record for anything that needs an audited/licensed data feed.

7. **This is running locally right now, not hosted anywhere shared.** If you or others need to view it without me running it live, that's a separate piece of work (hosting it somewhere accessible) I haven't done yet.

## Questions I still need your input on

- **Is the cash rate the only macro indicator you want, or do you also want inflation (CPI) or another indicator alongside it?** I looked into adding CPI earlier and stepped back from it to keep scope tight for this build — want to confirm that's the right call rather than assuming.
- **Do the specific volatility thresholds (1.5x and 2x the recent average) match how your team actually thinks about "elevated" vs "concerning"?** These were my starting judgment call, not something your team validated — worth a second opinion, especially from anyone closer to risk/markets.
- **How current does this data need to be in practice — daily each morning, or something more frequent?** This determines whether "designed to be schedulable" is good enough for now or whether I should actually wire up a real schedule.
- **Does this need to be viewable by others, or is a local demo sufficient for now?** Determines whether hosting is worth prioritizing.
- **If a day's market data looks wrong (fails a quality check), should that ever be visible on the dashboard**, or is it fine for that to be handled invisibly behind the scenes (logged, but not shown)?

Let me know your thoughts on any of the above — happy to jump on a call if easier than email.

Thanks,
[your name]
