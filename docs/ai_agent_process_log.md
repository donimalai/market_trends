# AI Agent Process Log — Market Intelligence Platform

**Purpose:** running record kept throughout the build, to be distilled into the presentation's "AI agent reflection" (what was overridden/corrected vs accepted) and "Team and standards" (work breakdown, delegation model) sections. Not a polished document — a raw log we compress into slide bullets at the end.

**How this gets used later:** each entry below should be defensible in a live Q&A — specific enough that "how did you catch that" has a real answer, not a generic one.

---

## Entry 1 — Intake: reading the 3 source docs

**Directed:** asked the agent to read the case study brief, the JD, and the draft 11-prompt Claude Code build spec, and ask questions before taking action (deliberately withheld "go build it" as the first instruction).

**What happened:** the agent's sandbox hit a real resource limit (disk space) and could not open the two `.docx` files. Rather than guessing at their contents from the filenames or the markdown paraphrase, it stopped, told me exactly what it couldn't do, and asked me to supply PDFs instead.

**Why this is worth keeping:** it's a small but concrete example of the failure-handling philosophy the case study itself asks for ("no silent failures," "log the outcome, don't guess") showing up in how I supervise the agent, not just in the pipeline code. Good answer to "how do you know the agent isn't quietly making things up when it hits a wall."

**Leadership/WBS note:** I set the ground rule up front — review and ask questions before acting — rather than letting the agent move straight to code. That's the same gate I'd want a junior engineer to pass through before writing transformation logic against a spec they haven't had checked.

---

## Entry 2 — Cross-checking the draft build spec against the actual case study PDF

**Directed:** once PDFs were available, asked the agent to compare the existing 11-prompt draft spec line-by-line against the real assessment brief (not just the earlier markdown paraphrase), and flag gaps before I ran anything.

**What the agent got right initially:** source selection (RBA + ASX200), the raw/DQ-log/curated/dashboard layering, and the 3 metrics all mapped cleanly to the rubric with no changes needed.

**What was incomplete, and how I caught it:**
1. **Metric-definition ordering.** The case study's AI Agent Lens requirement is specific: *"before using the agent to write the transformation logic, define your metric requirements in plain language. Include this definition in your submission."* The original Prompt 6 had the agent write the plain-language docstring **and** the implementation in the same pass. That would technically produce a document that looks like a human-first spec, without actually being one — it doesn't demonstrate the thing being assessed. Caught by reading the rubric sentence literally rather than trusting the paraphrase. **Correction:** split into Step A (I write `docs/metric_definitions.md` myself, agent not involved) and Step B (agent implements strictly against that file, explicitly told not to redefine the metrics).
2. **Silent scope gaps.** The draft spec covered code only — it never mentioned the Presentation deck, the optional bonus slide, or the actual submission format ("GitHub repo, plus dashboard link"), all of which are graded or explicitly required. A code-only spec would have let "finish the 11 prompts" quietly stand in for "finished the case study." **Correction:** added an explicit "Out of scope" section so those don't fall through unnoticed, plus a Prompt 0 for actual repo/git setup.
3. **Partial requirement coverage.** The brief asks for ingestion "on a scheduled or repeatable basis" — the draft only delivered "repeatable" (a manually-run script). **Correction:** rather than over-building real scheduling infrastructure for a local case study, added a documented cron/Task Scheduler example so the requirement is visibly addressed, not ignored or over-engineered.

**Leadership/WBS note:** this is the shape of review I'd expect from myself before handing any AI-drafted spec to a team member to execute — check it against the actual source requirement, not the last summary of it. Worth stating plainly in the presentation: the paraphrase (my own markdown notes) had already drifted slightly from the source brief before the agent ever touched it — a reminder that spec drift happens to humans too, and the review step has to catch both.

---

## Entry 3 — Drafting the metric definitions (human-first spec)

**Directed:** asked the agent to draft the plain-language metric definitions as a starting point for my review — explicitly not as a final artifact, and explicitly framed as "you write a draft, I decide."

**What came back:** definitions for all 3 metrics plus the RAG threshold rationale, including the *tradeoff* of a self-relative threshold (backward-looking, less sensitive right after a sustained volatile period) stated as an explicit limitation rather than glossed over.

**What I still need to decide (agent flagged these rather than silently defaulting):**
- Whether warm-up-period nulls (first 14–20 rows with no valid rolling window) should be surfaced in the dashboard or dropped.
- Whether the 90-day trailing mean for the RAG baseline should be a simple average or smoothed/weighted.
- Confirming the 252-trading-day annualisation convention before it's hardcoded.

**Leadership/WBS note:** these three are modelling judgment calls, not implementation details — the kind of decision I'd want a lead to own rather than delegate by default, even when using an agent that's perfectly capable of picking a reasonable default on its own. Good example for "how do you decide what to hand to the agent vs. keep for yourself."

---

## Entry 4 — Prompt 0 + Prompt 1: git init and repo scaffold

**Directed:** initialize git, connect to the real GitHub repo, scaffold Prompt 1's structure, commit.

**Security note first:** the GitHub URL supplied included a personal access token in plaintext directly in chat. Flagged this immediately, decided not to write the token into any persisted file or git config, and recommended rotating it regardless of what happened next — a real credential shouldn't be treated as safe just because "it's just me and the agent." Small moment, but a fair example of supervising an agent on security hygiene, not just code correctness.

**What came back / infrastructure issue found:** attempted to `git init` and commit directly inside the synced output folder. It failed — that folder is write-once (files can't be deleted or overwritten once written, by design, to protect the user's synced copy), and git constantly needs to create/delete lock files and rewrite refs. First attempt left a half-committed, unremovable `.git` directory with stale lock files sitting in the output folder.

**How I caught it:** the git commit itself errored loudly (`unable to lock ref 'HEAD'`) rather than silently succeeding in a broken state — the error surfaced immediately, not after the fact.

**Correction:** rebuilt the repo on the sandbox's local (non-synced) disk instead, where git behaves normally, committed there, then verified the *result* — not just the command's exit code — by doing a full round-trip: zipped it, unzipped it to a separate directory, and re-ran `git log` / `git status` / `git remote -v` against the unzipped copy before considering it done. Delivered as a `.zip` rather than a live folder, since a zip is a single new file (allowed) rather than a folder full of files that need in-place rewrites (not allowed on that mount).

**Also caught earlier, same step:** GitHub itself isn't reachable from the sandbox at all (outbound network is allowlisted, and `github.com` isn't on it — confirmed via `git ls-remote` and `curl` both returning 403 from the proxy). Decided not to fight this — the actual `git push` has to happen from the user's own machine anyway, which is also the cleaner security outcome (the token is never used or stored by the agent at all).

**Leadership/WBS note:** this is a good live example of "AI agent hit an environment limitation — what did it do." It didn't retry the same failing command blindly, didn't fabricate a "success," and didn't quietly leave a half-broken repo without saying so — it changed approach and then proved the new approach worked before reporting done. Worth stating explicitly in the "what did you override/correct" section: the correction here was mine (redirect to local disk, verify via round-trip) even though the diagnosis (the mount doesn't support git) came from reading the actual error message rather than assuming.

---

## Entry 5 — Connecting the real project folder, and a second git/mount surprise

**Directed:** connect the actual `~/Github/mip` folder (the one you'd already unzipped and pushed to GitHub yourself) so I could work against it directly, and run the `init` skill to generate a `CLAUDE.md`.

**What happened:** on connecting, found your local `.git/config` had the GitHub PAT embedded in the remote URL in plaintext (from the original zip's remote, which you'd set up using the URL as originally pasted). Fixed by rewriting the remote to the token-free URL immediately. Then, testing whether git would behave normally on this *real* folder (as opposed to the earlier synced scratch folder), ran a throwaway commit-and-revert — and hit the same "can't delete/lock files" restriction as before, this time against your actual project folder. Left a stray local-only commit and a stuck `HEAD.lock`.

**How I caught it:** again, the error surfaced immediately and loudly rather than silently corrupting state; nothing had been pushed, so the blast radius was contained to an unpushed local commit.

**Correction:** gave you exact recovery commands to run from your own Terminal (since I can't delete files through this connection either), and changed approach going forward — no more `git` commands run through my shell against your real repo. File *content* edits go through `Read`/`Write`/`Edit` (verified these work cleanly on this mount); actual git operations (add/commit/push) are either done by you directly, or built-and-verified on sandbox-local disk first the way Entry 4 describes.

**Leadership/WBS note:** two separate environments produced the same class of failure. Worth calling out as a pattern, not a one-off: before trusting a tool/agent to run stateful operations (git, database writes, deploys) against a new environment, do a cheap dry run first rather than assuming success from the first environment carries over. I made that mistake once (Entry 4) and then repeated a *smaller* version of it here instead of pre-emptively checking — a fair thing to admit in the "what did the agent/process get wrong" section, since this second instance was more on me (the operator) than the model.

---

## Entry 6 — Parallel work: VS Code + Claude Code extension joins the same repo

**Context, not yet a correction:** partway through, you opened the same `~/Github/mip` repo in VS Code with the Claude Code extension, working the same repo concurrently with this session. It had already created a `feature/rba-extractor` branch and `.claude/settings.local.json` by the time this was noticed.

**Risk flagged:** two agents (this session + VS Code's Claude Code) editing/committing against the same working tree concurrently can clobber each other's uncommitted changes or diverge silently, especially given the git fragility already documented in Entries 4–5. Proposed splitting responsibility explicitly (e.g. VS Code owns the actual Prompt 2–11 implementation; this session stays on planning docs, review, and the process log) rather than letting both write to `src/` at once — decision still pending as of this entry.

**Leadership/WBS note:** this is a live, real version of the "coordinating multiple agents/team members against one codebase" problem the case study's leadership lens asks about — worth using as the concrete example rather than a hypothetical, once resolved.

---

## Entry 7 — "Raw means raw": enforcing literal source fidelity in data/raw/

**Directed:** after Prompts 2–4 were built and working end-to-end, told the agent the raw layer needed to hold the source data in its original format, with no changes.

**What the agent had actually built (the gap):** `rba_extractor.py` and `yahoo_extractor.py` were both doing column selection, renaming, and type parsing *before* writing to `data/raw/` — e.g. RBA's 18-column source table was already being narrowed to just `date`/`cash_rate`, and yfinance's `Open/High/Low/Close/Volume/Dividends/Stock Splits` were already renamed and two columns silently dropped. Technically "raw" in name, not in fact.

**How I caught it:** direct instruction, not agent self-catch — this is a case of the agent producing something that satisfied the letter of the Prompt 1 scaffold ("raw output to data/raw/ as Parquet") without the spirit of a raw/immutable layer.

**Correction:** the agent asked one clarifying question first (all-columns-typed vs. narrow-to-used-columns) rather than guessing which "no changes" meant, then rewrote both extractors to persist every source column, original names, original row order. Column selection/renaming got pushed downstream into the (at-the-time) `align.py`.

**Leadership/WBS note:** worth using as the concrete example for "how do you set and enforce data modelling standards" (a rubric leadership-lens question) — a raw/bronze layer that's already been narrowed and renamed isn't re-derivable if the narrowing turns out wrong later; enforcing literal fidelity at ingestion is cheap insurance against a requirement changing downstream (which is exactly what happened next, in Entry 8).

---

## Entry 8 — Splitting the transform layer into raw → silver → mart, with lineage

**Directed:** create the DuckDB tables from the raw Parquet files under an explicit `raw` schema, then a `silver` schema with typed/deduped/validated versions — as separate pipeline modules, not all folded into `align.py` — plus a `load_date` lineage column on every table.

**What came back:** three modules instead of one — `raw_loader.py` (straight Parquet → `raw.*` load, DuckDB `read_parquet()` directly, no pandas round-trip, `load_date` stamped via SQL), `silver_builder.py` (typing/dedup/validation), and `align.py` reset to a stub reserved for the eventual curated/mart join. `load_date` is stamped once per run and applied uniformly — silver's `load_date` deliberately overwrites (not appends to) raw's, since each layer should record when *that layer* was last built, not carry a stale ingestion timestamp forward.

**Leadership/WBS note:** this is the "bronze/silver/gold" medallion pattern by another name, arrived at incrementally through instruction rather than proposed upfront — worth being honest about in the presentation (the first working version was a simpler 2-layer raw→curated design; it only became 3 layers once the DQ requirement in Entry 9 needed somewhere explicit to quarantine failed rows without touching the raw layer).

---

## Entry 9 — Full data-quality validation suite: quarantine model, and two real bugs it caught

**Directed:** a detailed 6-check spec for the RBA dataset and a 7-check spec for ASX200 (completeness, valid range/values, internal consistency, freshness, no-duplicates, unusual-movement/index-composition), each check to produce pass/fail/warning + a human-readable reason, failed rows quarantined (not dropped), warned rows kept but flagged, and everything logged so a DQ dashboard could be built off it.

**What came back:** `dq_logger.py` gained a second table, `dq_validation_log` (one row per named check, structured counts — checked/failed/warned — rather than a free-text message), since the existing run-level `dq_log` table can't support per-check dashboarding. `silver_builder.py` was rewritten to run all 13 checks and split each source into a kept table (with `dq_warning_reason`) and a `*_quarantine` table (with `quarantine_reason`).

**Two real bugs caught while verifying, not assumed away:**
1. **False-positive range check.** The RBA `valid_range` check initially flagged today's row as "outside plausible range" — actually a `NULL` (today's rate not yet published by RBA), which `pandas.Series.between()` silently treats as `False` when negated, conflating "missing" with "implausible." Caught by inspecting the one flagged row rather than trusting the aggregate count. **Fix:** split into two separate checks (missing vs. out-of-range) so the reason reported is accurate.
2. **Wrong column type on an empty quarantine table.** With zero quarantined rows, pandas' dtype inference on an empty `.apply()` result silently produced `INTEGER` for `quarantine_reason` instead of `VARCHAR` — caught by inspecting `DESCRIBE` on the table, not by a crash (it would only have broken the moment a real quarantined row with a differently-typed value showed up). **Fix:** explicit `.astype(str)` / `.astype(object)` after the `.apply()`, forced even on the empty-row path.

**Leadership/WBS note:** both bugs are "silent until the edge case happens" — the empty-quarantine-table bug especially, since local testing with 0 quarantined rows is the *common* case and would never have surfaced it without deliberately checking the schema, not just the row count. Good concrete answer to "how do you review AI-generated validation code" — the review has to include checking degenerate/empty inputs, not just the happy path with real failures present.

---

## Entry 10 — Mart data model: reconciling the literal spec against "flexible for custom dashboards"

**Directed:** design the final curated/mart table(s) for the dashboard, but with a data model flexible enough for users to build custom dashboards later, not just the one specified in `docs/prompt_data_curation_and_dashboard.md`.

**The tension:** the case study's own prompt spec is literal — `align.py` must "write to DuckDB table curated.aligned_daily", `metrics.py` must write `curated.metrics_daily`, and `app.py` reads only `curated.metrics_daily`. A single wide table per step satisfies that exactly, but is rigid: every new chart means widening the table or writing a bespoke query.

**What came back:** a small star schema proposed as a design doc (`docs/mart_data_model.md`) *before* writing any code against it — `dim_date` + three fact tables (`fact_market_daily`, `fact_macro_daily`, `fact_metrics_daily`) as the actual source of truth, with `aligned_daily`/`metrics_daily` still physically built as required (now as joins of the facts, not the only artifact produced), plus a proposed `fact_daily_long` unpivoted table as the actual answer to "flexible" — a future custom chart filters by `metric_name`, no schema change needed. Flagged one open call rather than deciding it silently: whether `fact_daily_long` belongs inside `metrics.py` or as its own module.

**How this got reviewed:** walked through the proposal's table shapes and two embedded judgment calls (which RBA column counts as "the cash rate" now that silver validates `Cash Rate Target`; where AEST timezone handling now actually lives now that silver needs typed dates) before any implementation — approved, then `align.py` was rewritten against the agreed shape.

**Leadership/WBS note:** direct material for "how would you set and enforce data modelling standards" — the answer demonstrated here is "the literal graded requirement doesn't have to fight the good architecture; design the flexible layer *underneath* the fixed contract, so nothing downstream (here, `app.py`) has to change." Also a clean example of insisting on a reviewable design doc before code for a schema-level decision, the same gate applied earlier to metric definitions (Entry 3) and now extended to data modelling.

---

## Entry 11 — Finalizing the RAG signal: closing a boundary ambiguity and two failure modes

**Directed:** finalize the RAG threshold boundary logic (resolving whether exactly 2.0× volatility is amber or red) and fold in two additional supporting rules before `docs/metric_definitions.md` is treated as locked.

**What came back / was folded in:**
- **Boundary clarification:** amber is now explicitly `>1.5× and ≤2.0×`, red is `>2.0×` — every ratio value maps to exactly one band, no gap or overlap at the boundary that was previously just "between 1.5× and 2×."
- **A distinct, longer warm-up rule:** the RAG signal needs both a 14-day volatility figure *and* a 90-day trailing average of it, so it can't be produced until ~104 trading days of history exist — documented separately from the shorter 14–20 row warm-up already defined for the other three metrics, so it doesn't get silently conflated with them in `metrics.py`.
- **A divide-by-near-zero guard:** during an unusually calm stretch, a low 90-day trailing volatility average could make the ratio spike misleadingly on an ordinary small move. Added a 3%-annualised floor below which the signal reports `"insufficient signal"` (a distinct fourth state) instead of a potentially false Red.

**Leadership/WBS note:** this is the second full pass on the RAG definition (first draft in Entry 3, finalized here) — worth stating plainly that "plain-language spec, written before the agent implements" isn't a one-shot step; it went through real revision once a genuine failure mode (near-zero-denominator false positive) was identified, which is exactly the kind of thing a spec review is *for*.

---

## Entry 12 — Running the finalized RAG rule against real data exposed a second gap: the lookback window

**Directed:** implement `metrics.py` against the just-finalized `docs/metric_definitions.md` (Entry 11) and run it against the actual pipeline output, not just review the code.

**What came back / the gap found:** the other three metrics populated exactly as expected (`rolling_avg_volume_20d` 84/103 non-null, `rate_of_change_pct` 102/103, `volatility_14d_annualised` 89/103 — each correctly null for its own warm-up window). But **`rag_signal` was 0/103** — every single row null. The dataset only had 103 trading days of history (from `yahoo_extractor.py`'s 150-calendar-day lookback), one short of the ~104 trading days Entry 11's own warm-up rule requires for the *first* non-null RAG value.

**How I caught it:** not a code review catch — running the module against real data and checking the actual populated-row count, not just trusting that the formula was implemented correctly. The formula was correct; the upstream data volume was the problem, which only shows up empirically.

**Why this mattered immediately, not eventually:** the RAG badge (dashboard Section 3) is a *required* graded rubric item (DASH-4). Shipping this without noticing would have meant a blank badge on the actual demo data — a working pipeline that silently fails the one requirement most likely to get looked at first in a live demo.

**Correction:** widened `yahoo_extractor.py`'s lookback from 150 to **220 calendar days** (this is the second revision of that constant — it started at the spec's original 120, moved to 150 early on after 120 proved to only yield ~83 trading rows, and now to 220). Sized deliberately, not just "bigger": RAG needs ≥104 trading days total, and the dashboard's 90-day chart window additionally wants its own 20-day rolling-volume warm-up *before* that window starts for a gap-free overlay — so the real floor is ≥110 trading days, not 104. At the observed ~103-trading-days-per-150-calendar-days ratio, 220 calendar days was sized to comfortably clear ~150 trading rows. Also raised the module's own `MIN_EXPECTED_ROWS` DQ threshold from 90 to 110 to match, so that check still means something (previously it would never fire until the data was already badly short). Re-ran the full pipeline end to end: 150 trading rows, RAG populated on **47/150** rows, all Green (the current market is genuinely calm — verified against the actual volatility figures, not assumed).

**Leadership/WBS note:** two separate, independent findings landed on the same constant (Entry 9's earlier 120→150 fix, this 150→220 fix) — worth stating explicitly that a "reasonable-looking" lookback window needs to be sized against the *most demanding downstream consumer's* actual requirement (here, RAG's 104-day warm-up), not against an intuitive guess, and that this only gets caught by actually running the full chain against real data rather than trusting each module's unit-level correctness in isolation.

---

## Work breakdown pattern emerging so far (for "Team and standards" slide)

| Owned by lead (me) | Owned by agent (or junior eng., supervised) |
|---|---|
| Source & metric selection, threshold rationale | Boilerplate scaffolding, extractor implementation |
| Rubric/requirement compliance checking against source docs | Test-writing against a locked spec |
| Metric definitions (plain language, pre-code) | Implementation once spec is approved |
| Reviewing agent output for intent-completeness, not just literal completeness | First-pass drafts, gap-flagging, options for review |
| Coordinating which agent/session owns which files when working in parallel | — |
| Data modelling standards: schema shape, table naming, grain, what "raw" means literally | Draft schema proposals with tradeoffs surfaced, not silently decided |
| Deciding when a design needs a written doc + sign-off before code (metrics, then mart model) | Flagging open questions explicitly instead of picking a default unasked |
| Deciding acceptance criteria for "done" (e.g. RAG must actually populate on real data, not just compute without error) | Running each module against the real pipeline output and reporting actual counts, not just "no exceptions raised" |

---

## Template for future entries

```
### Entry N — <what was being built>
**Directed:** <what I asked the agent to do>
**What came back:** <what the agent produced>
**Error/gap found (if any):** <specifics>
**How I caught it:** <what triggered the review — rubric check, test failure, manual read, etc.>
**Correction:** <what changed>
**Leadership/WBS note (if any):** <delegation or standards angle>
```
