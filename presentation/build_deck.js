const pptxgen = require("pptxgenjs");
const path = require("path");

const A = (f) => path.join(__dirname, "assets", f);

// Palette: "Midnight Executive" -- navy dominant, ice blue supporting, white accent.
// Semantic RAG colors (matching the actual dashboard) are used only on the DQ slide.
const NAVY = "1E2761";
const NAVY_DARK = "141B4D";
const ICE = "CADCFC";
const ICE_TINT = "EEF3FD";
const WHITE = "FFFFFF";
const INK = "1B1F3B";
const MUTED = "5B6280";
const GREEN = "1E7E34";
const AMBER = "B26A00";
const RED = "C62828";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.3 x 7.5 in
const PAGE_W = 13.33;
const PAGE_H = 7.5;

const FONT = "Calibri";
const FONT_HEAD = "Cambria";

function iconCircle(slide, iconFile, x, y, size, circleColor, iconScale) {
  slide.addShape("ellipse", { x, y, w: size, h: size, fill: { color: circleColor }, line: { type: "none" } });
  const pad = size * (1 - (iconScale || 0.55)) / 2;
  slide.addImage({ path: A(iconFile), x: x + pad, y: y + pad, w: size - 2 * pad, h: size - 2 * pad });
}

function footer(slide, pageNum, dark) {
  slide.addText("Market Intelligence Platform  |  Case study — Data & Analytics Engineering Lead", {
    x: 0.5, y: PAGE_H - 0.42, w: 9.5, h: 0.3, fontFace: FONT, fontSize: 9,
    color: dark ? "8892C7" : MUTED, align: "left",
  });
  slide.addText(String(pageNum), {
    x: PAGE_W - 1.0, y: PAGE_H - 0.42, w: 0.5, h: 0.3, fontFace: FONT, fontSize: 9,
    color: dark ? "8892C7" : MUTED, align: "right",
  });
}

function sectionHeader(slide, iconFile, title, subtitle) {
  iconCircle(slide, iconFile, 0.6, 0.5, 0.62, NAVY, 0.55);
  slide.addText(title, {
    x: 1.4, y: 0.42, w: 11.3, h: 0.55, fontFace: FONT_HEAD, fontSize: 28, bold: true, color: INK, valign: "middle",
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: 1.4, y: 0.98, w: 11.3, h: 0.35, fontFace: FONT, fontSize: 13, italic: true, color: MUTED, valign: "middle",
    });
  }
}

// ---------------------------------------------------------------- Slide 1: Title
{
  const s = pres.addSlide();
  s.background = { color: NAVY_DARK };
  iconCircle(s, "database.png", PAGE_W / 2 - 0.5, 1.1, 1.0, NAVY, 0.55);
  s.addText("Market Intelligence Platform", {
    x: 1.0, y: 2.35, w: PAGE_W - 2.0, h: 1.1, fontFace: FONT_HEAD, fontSize: 40, bold: true,
    color: WHITE, align: "center", valign: "middle",
  });
  s.addText("ASX 200 market trend + RBA cash rate, for financially literate, non-technical bank management",
    { x: 1.3, y: 3.5, w: PAGE_W - 2.6, h: 0.6, fontFace: FONT, fontSize: 16, color: ICE, align: "center" });
  s.addText("Case study — Senior Data Analytics / BI Specialist (Data & Analytics Engineering Lead), Associate Director\nMacquarie Market Services — Post-Trade Transformation",
    { x: 1.3, y: 4.35, w: PAGE_W - 2.6, h: 0.7, fontFace: FONT, fontSize: 12.5, color: "9AA6D6", align: "center", lineSpacingMultiple: 1.3 });
  s.addText("github.com/donimalai/market_trends", {
    x: 1.3, y: 6.55, w: PAGE_W - 2.6, h: 0.4, fontFace: FONT, fontSize: 12, color: "7C87BD", align: "center",
  });
}

// ---------------------------------------------------------------- Slide 2: Framing
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  sectionHeader(s, "target.png", "One question, answered without reading a pipeline", "Framing");

  s.addText(
    [
      { text: "This role has two mandates: instrument how the business measures itself, and shape how analytics gets embedded into every product. ", options: { color: MUTED, italic: true } },
      { text: "This case study is a compressed version of the first — the same thinking extends to the second.", options: { color: NAVY, italic: true, bold: true } },
    ],
    { x: 0.6, y: 1.4, w: 12.13, h: 0.4, fontFace: FONT, fontSize: 12.5, align: "center", valign: "middle" }
  );

  s.addShape("roundRect", { x: 0.6, y: 1.9, w: 12.13, h: 1.25, rectRadius: 0.12, fill: { color: ICE_TINT }, line: { type: "none" } });
  s.addText(
    [{ text: "“How has ASX 200 market activity trended over the past 90 days, and is there anything we should be watching?”", options: { italic: true, fontSize: 17, color: NAVY, bold: true } }],
    { x: 0.95, y: 1.9, w: 11.43, h: 1.25, fontFace: FONT_HEAD, align: "center", valign: "middle", lineSpacingMultiple: 1.2 }
  );

  const rows = [
    ["Why it matters", "Rate moves and market swings don't always show up together right away — one view of both lets management catch a shift while it's still a line on a chart, not a headline."],
    ["Audience", "Financially literate, non-technical bank management — one clear takeaway per chart, no jargon."],
    ["Source pairing", "RBA cash rate + ASX 200 — the case study's own suggested pairing, and naturally fits a Sydney / Market Services context."],
    ["Design philosophy", "Data as infrastructure, not a one-off report — instrumented, observable, built for self-service from day one, the same standard I'd hold a product to."],
  ];
  let y = 3.35;
  rows.forEach(([h, b]) => {
    s.addShape("ellipse", { x: 0.7, y: y + 0.08, w: 0.14, h: 0.14, fill: { color: NAVY }, line: { type: "none" } });
    s.addText(h, { x: 1.0, y, w: 3.1, h: 0.6, fontFace: FONT, fontSize: 14, bold: true, color: NAVY, valign: "top" });
    s.addText(b, { x: 4.2, y, w: 8.5, h: 0.6, fontFace: FONT, fontSize: 13, color: INK, valign: "top", lineSpacingMultiple: 1.15 });
    y += 0.93;
  });
  footer(s, 2, false);
}

// ---------------------------------------------------------------- Slide 3: Architecture
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  sectionHeader(s, "compass.png", "Raw → Silver → Mart → Dashboard", "Pipeline walkthrough");

  const stages = [
    ["data/raw/", "Immutable Parquet\n(gitignored)"],
    ["raw.*", "Straight DuckDB load\n+ load_date lineage"],
    ["silver.*", "Typed · deduped\n13 DQ checks · quarantine"],
    ["curated.*", "Star schema mart\n(dim_date + facts)"],
    ["Dashboard", "3-page Streamlit app\nreads metrics_daily only"],
  ];
  const boxW = 2.15, gap = 0.28, startX = 0.65, boxY = 2.35, boxH = 1.55;
  stages.forEach((st, i) => {
    const x = startX + i * (boxW + gap);
    const isLast = i === stages.length - 1;
    s.addShape("roundRect", {
      x, y: boxY, w: boxW, h: boxH, rectRadius: 0.1,
      fill: { color: isLast ? NAVY : ICE_TINT }, line: { color: ICE, width: 1 },
    });
    s.addText(st[0], { x, y: boxY + 0.12, w: boxW, h: 0.4, fontFace: FONT_HEAD, fontSize: 15, bold: true, align: "center", color: isLast ? WHITE : NAVY });
    s.addText(st[1], { x: x + 0.08, y: boxY + 0.55, w: boxW - 0.16, h: 0.9, fontFace: FONT, fontSize: 10.5, align: "center", color: isLast ? ICE : MUTED, valign: "top", lineSpacingMultiple: 1.15 });
    if (!isLast) {
      s.addText("→", { x: x + boxW, y: boxY, w: gap, h: boxH, fontFace: FONT, fontSize: 20, bold: true, color: NAVY, align: "center", valign: "middle" });
    }
  });

  const pillars = [
    ["Layer separation", "Raw is never pre-cleaned — every source column survives untouched, so a requirement change never means re-pulling data. Each layer re-runs and tests independently."],
    ["Error handling", "Nothing fails silently — every stage logs its outcome. Rows that fail a critical check are quarantined, with the exact reason, not dropped."],
    ["Handoff approach", "Adding a source follows one fixed pattern; DQ logging lives in two tables, not tribal knowledge; any schema change needs a written design doc before code."],
  ];
  const pW = 3.9, pGap = 0.22, pX = 0.6, pY = 4.35, pH = 2.15;
  pillars.forEach((p, i) => {
    const x = pX + i * (pW + pGap);
    s.addShape("roundRect", { x, y: pY, w: pW, h: pH, rectRadius: 0.12, fill: { color: ICE_TINT }, line: { type: "none" } });
    s.addText(p[0], { x: x + 0.25, y: pY + 0.18, w: pW - 0.5, h: 0.4, fontFace: FONT, fontSize: 13.5, bold: true, color: NAVY });
    s.addText(p[1], { x: x + 0.25, y: pY + 0.62, w: pW - 0.5, h: 1.4, fontFace: FONT, fontSize: 11, color: INK, valign: "top", lineSpacingMultiple: 1.25 });
  });
  footer(s, 3, false);
}

// ---------------------------------------------------------------- Slide 4: Data decisions
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  sectionHeader(s, "chart.png", "Four measures, each on purpose", "Data decisions");

  const tableRows = [
    [
      { text: "Measure", options: { bold: true, color: WHITE, fill: { color: NAVY } } },
      { text: "Window", options: { bold: true, color: WHITE, fill: { color: NAVY } } },
      { text: "Why this window", options: { bold: true, color: WHITE, fill: { color: NAVY } } },
    ],
    [{ text: "Rolling avg volume" }, { text: "20 trading days" }, { text: "Not specified in the brief — chosen as a ~monthly convention: smooths noise, stays responsive." }],
    [{ text: "Rate of change" }, { text: "1 day" }, { text: "Simplest “up or down” signal — deliberately the shortest window." }],
    [{ text: "14-day volatility (ann.)" }, { text: "14 trading days" }, { text: "The one window the brief specifies explicitly." }],
    [{ text: "RAG signal" }, { text: "14d vol vs. its own 90d avg" }, { text: "Self-relative, not fixed — flags regime shifts without an external baseline." }],
  ];
  s.addTable(tableRows, {
    x: 0.6, y: 1.65, w: 12.13, h: 2.5, fontFace: FONT, fontSize: 11.5, color: INK, border: { type: "solid", color: ICE, pt: 0.75 },
    autoPage: false, colW: [3.0, 2.6, 6.53], valign: "middle", rowH: 0.5,
  });

  const dBoxes = [
    ["RAG threshold", "🟢 ≤ 1.5×   🟡 1.5–2.0×   🔴 > 2.0×\nof its own 90-day trailing average volatility.\nThe system makes the call — not the reader.", true],
    ["What we excluded", "CPI/inflation was evaluated as a second macro overlay and deliberately left out — the brief wants one macro series, and CPI's quarterly cadence doesn't suit a 90-day view.", false],
    ["Assumptions", "9 documented where the brief was silent — e.g. the 20-day volume window, Cash Rate Target vs. Interbank rate. Full list in the Appendix, kept visible, not buried.", false],
  ];
  const dW = 3.87, dGap = 0.26, dX = 0.6, dY = 4.4, dH = 2.1;
  dBoxes.forEach((b, i) => {
    const x = dX + i * (dW + dGap);
    s.addShape("roundRect", { x, y: dY, w: dW, h: dH, rectRadius: 0.12, fill: { color: b[2] ? NAVY : ICE_TINT }, line: { type: "none" } });
    s.addText(b[0], { x: x + 0.22, y: dY + 0.16, w: dW - 0.44, h: 0.4, fontFace: FONT, fontSize: 13, bold: true, color: b[2] ? ICE : NAVY });
    s.addText(b[1], { x: x + 0.22, y: dY + 0.58, w: dW - 0.44, h: 1.42, fontFace: FONT, fontSize: 11.5, color: b[2] ? WHITE : INK, lineSpacingMultiple: 1.3, valign: "top" });
  });
  footer(s, 4, false);
}

// ---------------------------------------------------------------- Slide 5: Data quality approach
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  sectionHeader(s, "shield.png", "No silent failures, by design", "Data quality approach");

  const stats = [
    ["8", "pipeline stages\nlogged every run"],
    ["13", "DQ checks per run\n(both datasets combined)"],
    ["2", "real bugs caught\n& fixed while building this"],
  ];
  stats.forEach(([n, l], i) => {
    const x = 0.6 + i * 4.15;
    s.addShape("roundRect", { x, y: 1.6, w: 3.85, h: 1.55, rectRadius: 0.12, fill: { color: NAVY }, line: { type: "none" } });
    s.addText(n, { x, y: 1.65, w: 3.85, h: 0.75, fontFace: FONT_HEAD, fontSize: 40, bold: true, color: WHITE, align: "center", valign: "middle" });
    s.addText(l, { x, y: 2.4, w: 3.85, h: 0.65, fontFace: FONT, fontSize: 11.5, color: ICE, align: "center", valign: "top", lineSpacingMultiple: 1.2 });
  });

  s.addText("How a row moves through validation", { x: 0.6, y: 3.55, w: 11, h: 0.35, fontFace: FONT, fontSize: 14, bold: true, color: NAVY });
  const flow = [
    ["Pass", GREEN, "Nothing flagged"],
    ["Warning", AMBER, "Flagged, kept — e.g. a missing business day (likely a holiday)"],
    ["Fail", RED, "Quarantined, not dropped — held with the exact reason"],
  ];
  let fx = 0.6;
  flow.forEach(([label, color, desc], i) => {
    s.addShape("roundRect", { x: fx, y: 4.05, w: 3.9, h: 1.1, rectRadius: 0.1, fill: { color: ICE_TINT }, line: { color, width: 1.5 } });
    s.addShape("ellipse", { x: fx + 0.2, y: 4.22, w: 0.22, h: 0.22, fill: { color }, line: { type: "none" } });
    s.addText(label, { x: fx + 0.55, y: 4.16, w: 3.2, h: 0.35, fontFace: FONT, fontSize: 13, bold: true, color: INK });
    s.addText(desc, { x: fx + 0.2, y: 4.55, w: 3.55, h: 0.55, fontFace: FONT, fontSize: 10.5, color: MUTED, lineSpacingMultiple: 1.2 });
    fx += 4.15;
  });

  s.addText(
    "Both bugs below were caught by checking real output — not by code review alone. Full detail: docs/ai_agent_process_log.md, Entry 9.",
    { x: 0.6, y: 5.35, w: 12.13, h: 0.35, fontFace: FONT, fontSize: 11, italic: true, color: MUTED }
  );
  s.addShape("roundRect", { x: 0.6, y: 5.75, w: 12.13, h: 1.2, rectRadius: 0.1, fill: { color: "FBEAEA" }, line: { type: "none" } });
  s.addText(
    [
      { text: "“Missing” miscounted as “out of range”:  ", options: { bold: true, color: INK, fontSize: 11.5 } },
      { text: "a null value (today's not-yet-published rate) was flagged as implausible. Fixed by splitting the check in two.", options: { color: INK, fontSize: 11.5 } },
    ],
    { x: 0.85, y: 5.85, w: 11.6, h: 0.45, fontFace: FONT, valign: "top" }
  );
  s.addText(
    [
      { text: "Empty quarantine table got the wrong column type:  ", options: { bold: true, color: INK, fontSize: 11.5 } },
      { text: "pandas' dtype inference silently gave a text column an INTEGER type when 0 rows were quarantined — the common case. Caught via DESCRIBE, not the row count.", options: { color: INK, fontSize: 11.5 } },
    ],
    { x: 0.85, y: 6.3, w: 11.6, h: 0.55, fontFace: FONT, valign: "top" }
  );
  footer(s, 5, false);
}

// ---------------------------------------------------------------- Slide 6: Dashboard demo 1
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  sectionHeader(s, "chart.png", "Answers the question directly — live demo now", "Dashboard walkthrough · Market overview");

  const cards = [
    ["KPI row + bottom-line", "Latest close, 90-day change, range as a ±% band, and current volatility — plus one auto-generated sentence synthesizing all of it. Rule-based, not ML."],
    ["Market activity", "ASX 200 close price and volume, with a 20-day rolling average — outlier-capped y-axis so the trend isn't flattened by spikes."],
    ["Macro overlay", "ASX 200 on a single axis; the RBA cash rate shown as shaded background bands, not a second line on a second axis — simpler to read at a glance."],
    ["Volatility signal", "The RAG badge for today, plus a day-by-day history strip with an inline legend — “how long has it been this color” at a glance."],
  ];
  cards.forEach((c, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 0.6 + col * 6.15, y = 1.65 + row * 2.35;
    s.addShape("roundRect", { x, y, w: 5.85, h: 2.1, rectRadius: 0.12, fill: { color: ICE_TINT }, line: { type: "none" } });
    s.addText(c[0], { x: x + 0.25, y: y + 0.18, w: 5.35, h: 0.4, fontFace: FONT, fontSize: 14, bold: true, color: NAVY });
    s.addText(c[1], { x: x + 0.25, y: y + 0.62, w: 5.35, h: 1.35, fontFace: FONT, fontSize: 11.5, color: INK, lineSpacingMultiple: 1.25, valign: "top" });
  });
  footer(s, 6, false);
  s.addNotes(
    "Logistics: confirm timing with a full run-through including the live demo before presenting -- 12 " +
    "content slides plus two live demo sections is tight for 20 minutes. Have a screenshot fallback ready " +
    "(see README/docs) in case the live dashboard doesn't come up cleanly."
  );
}

// ---------------------------------------------------------------- Slide 7: Dashboard demo 2
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  sectionHeader(s, "shield.png", "The DQ tables are the DQ dashboard", "Dashboard walkthrough · Data quality & Appendix");

  s.addShape("roundRect", { x: 0.6, y: 1.65, w: 12.13, h: 2.55, rectRadius: 0.12, fill: { color: ICE_TINT }, line: { type: "none" } });
  s.addText("Data statistics & quality", { x: 0.9, y: 1.85, w: 11.5, h: 0.4, fontFace: FONT, fontSize: 15, bold: true, color: NAVY });
  s.addText(
    "•  Colour-coded status badges (🟢/🟡/🔴/⚪) mapped directly from the pipeline's own logged status — nothing re-classified for display.\n" +
    "•  DQ trend chart across recent runs — evidence this is continuously monitored, not a one-off check.\n" +
    "•  A worked quarantine example: one deliberately invalid row run through the real validation logic — proves the mechanism works by executing it, not just describing it. Labeled honestly as a synthetic test case; the real pipeline has quarantined 0 rows to date.",
    { x: 0.9, y: 2.3, w: 11.5, h: 1.8, fontFace: FONT, fontSize: 12, color: INK, lineSpacingMultiple: 1.3, valign: "top" }
  );

  s.addShape("roundRect", { x: 0.6, y: 4.4, w: 12.13, h: 1.85, rectRadius: 0.12, fill: { color: NAVY }, line: { type: "none" } });
  s.addText("Appendix", { x: 0.9, y: 4.58, w: 11.5, h: 0.4, fontFace: FONT, fontSize: 15, bold: true, color: ICE });
  s.addText(
    "One plain-language explainer, written for both audiences — the exact formulas behind every KPI, why the macro overlay dropped its dual axis, and precise definitions for every DQ status — all traceable to real table/function names, and kept in sync with docs/metric_definitions.md rather than re-explained twice.",
    { x: 0.9, y: 5.0, w: 11.5, h: 1.15, fontFace: FONT, fontSize: 12, color: WHITE, lineSpacingMultiple: 1.3, valign: "top" }
  );
  footer(s, 7, false);
  s.addNotes(
    "Logistics: same timing note as slide 6 -- rehearse this section live, keep a screenshot fallback handy."
  );
}

// ---------------------------------------------------------------- Slide 8: AI agent reflection
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  sectionHeader(s, "cpu.png", "Caught, not assumed — and trusted where it earned it", "AI agent reflection");

  const colW = 5.9, colGap = 0.33, colX0 = 0.6, colY = 1.65, colH = 4.95;
  const cols = [
    {
      label: "Corrected", x: colX0, bg: "FBEAEA", accent: RED,
      items: [
        ["The three-layer model was my call", "The agent's first working version was a simple two-layer raw → curated pipeline. I directed the split into raw, silver, and curated once the DQ spec needed an explicit layer to quarantine failed rows without touching raw."],
        ["“Raw” wasn't actually raw", "The extractors were narrowing and renaming columns before writing to the raw layer — technically raw in name, not in fact. Caught on review, not agent self-catch; corrected to persist every source column untouched."],
        ["“It ran” ≠ “it worked”", "The volatility signal computed with zero errors but was 0% populated. Caught by checking the actual row count, not just that nothing crashed — fixed with a properly sized lookback window."],
      ],
    },
    {
      label: "Accepted", x: colX0 + colW + colGap, bg: ICE_TINT, accent: GREEN,
      items: [
        ["The metric-definitions draft", "Accepted as the starting point — including three open judgment calls the agent flagged rather than silently defaulting on (warm-up nulls, baseline averaging, annualisation convention). I decided each one myself."],
        ["The mart design doc", "A star-schema proposal, written before any code. Walked through two embedded judgment calls with the agent and approved it — not accepted blind, but the design itself needed no rework."],
        ["How it handled hitting a wall", "When a sandbox limit blocked it mid-task, it stopped, said exactly what failed, and asked rather than guessing or quietly leaving a broken state — trusted as the default response, no correction needed."],
      ],
    },
  ];
  cols.forEach((col) => {
    s.addShape("roundRect", { x: col.x, y: colY, w: colW, h: colH, rectRadius: 0.12, fill: { color: col.bg }, line: { type: "none" } });
    s.addShape("ellipse", { x: col.x + 0.28, y: colY + 0.26, w: 0.2, h: 0.2, fill: { color: col.accent }, line: { type: "none" } });
    s.addText(col.label, { x: col.x + 0.6, y: colY + 0.18, w: colW - 0.9, h: 0.4, fontFace: FONT, fontSize: 15, bold: true, color: INK });
    let iy = colY + 0.75;
    col.items.forEach(([h, b]) => {
      s.addText(h, { x: col.x + 0.3, y: iy, w: colW - 0.6, h: 0.35, fontFace: FONT, fontSize: 12.5, bold: true, color: INK });
      s.addText(b, { x: col.x + 0.3, y: iy + 0.35, w: colW - 0.6, h: 0.95, fontFace: FONT, fontSize: 10.8, color: MUTED, lineSpacingMultiple: 1.22, valign: "top" });
      iy += 1.38;
    });
  });
  s.addText("Full turn-by-turn record: docs/ai_agent_process_log.md — 12 entries.", {
    x: 0.6, y: 6.75, w: 12, h: 0.3, fontFace: FONT, fontSize: 10.5, italic: true, color: MUTED,
  });
  footer(s, 8, false);
}

// ---------------------------------------------------------------- Slide 9: Team & standards
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  sectionHeader(s, "users.png", "What I owned vs. what the agent owned", "Team & standards");

  const tableRows = [
    [
      { text: "Owned by lead", options: { bold: true, color: WHITE, fill: { color: NAVY } } },
      { text: "Owned by agent (supervised)", options: { bold: true, color: WHITE, fill: { color: NAVY } } },
    ],
    [{ text: "Source & metric selection, threshold rationale" }, { text: "Boilerplate scaffolding, extractor implementation" }],
    [{ text: "Rubric/requirement compliance checking" }, { text: "Test-writing against a locked spec" }],
    [{ text: "Metric definitions, written before any code" }, { text: "Implementation once spec is approved" }],
    [{ text: "Data modelling standards — schema shape, what “raw” means literally" }, { text: "Draft schema proposals with tradeoffs surfaced, not silently decided" }],
    [{ text: "Deciding acceptance criteria for “done”" }, { text: "Running against real data, reporting actual counts — not just “no exception”" }],
  ];
  s.addTable(tableRows, {
    x: 0.6, y: 1.55, w: 12.13, h: 3.1, fontFace: FONT, fontSize: 11.5, color: INK, border: { type: "solid", color: ICE, pt: 0.75 },
    autoPage: false, colW: [6.06, 6.07], valign: "middle", rowH: 0.52,
  });

  s.addShape("roundRect", { x: 0.6, y: 4.85, w: 5.9, h: 2.15, rectRadius: 0.12, fill: { color: NAVY }, line: { type: "none" } });
  s.addText("Review was iterative, not one-pass", { x: 0.85, y: 5.0, w: 5.4, h: 0.5, fontFace: FONT, fontSize: 13, bold: true, color: ICE });
  s.addText(
    "The RAG rule went through three passes: a first draft, a boundary and near-zero-denominator fix once a real failure mode surfaced, then a lookback-window fix once it ran against real data and returned zero populated rows. Each pass came from checking actual output, not re-reading code.",
    { x: 0.85, y: 5.5, w: 5.4, h: 1.4, fontFace: FONT, fontSize: 11, color: WHITE, lineSpacingMultiple: 1.25, valign: "top" }
  );

  s.addShape("roundRect", { x: 6.7, y: 4.85, w: 6.03, h: 2.15, rectRadius: 0.12, fill: { color: ICE_TINT }, line: { type: "none" } });
  s.addText("How this becomes a handoff model", { x: 6.95, y: 5.0, w: 5.5, h: 0.5, fontFace: FONT, fontSize: 13, bold: true, color: NAVY });
  s.addText(
    "Every schema-level decision — metric definitions, then the mart design — went through a written proposal, signed off before code: the artifact I'd hand a new hire or agent to onboard onto this codebase. When a second agent joined mid-build, I split file ownership explicitly, not left it to chance.",
    { x: 6.95, y: 5.5, w: 5.5, h: 1.4, fontFace: FONT, fontSize: 11, color: INK, lineSpacingMultiple: 1.25, valign: "top" }
  );
  footer(s, 9, false);
}

// ---------------------------------------------------------------- Slide 10: If I had more time
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  sectionHeader(s, "arrow.png", "What's next", "If I had more time");

  const items = [
    ["Priority 1", "curated.fact_daily_long", "The flexible reporting layer, designed but not built. Wins the top spot because it unblocks every *future* dashboard request without more pipeline work — the highest-leverage thing left."],
    ["Priority 2", "Full RBA meeting calendar", "Currently marks rate-change dates only. Wins second because markets can react to a hold's guidance too, not just a move — a real gap in the “anything to watch” story, cheap to close."],
  ];
  items.forEach((it, i) => {
    const x = 0.6 + i * 6.15, y = 1.7;
    s.addShape("roundRect", { x, y, w: 5.85, h: 3.0, rectRadius: 0.12, fill: { color: NAVY }, line: { type: "none" } });
    s.addText(it[0], { x: x + 0.25, y: y + 0.2, w: 5.35, h: 0.3, fontFace: FONT, fontSize: 11, bold: true, color: "8FA6E0" });
    s.addText(it[1], { x: x + 0.25, y: y + 0.5, w: 5.35, h: 0.5, fontFace: FONT_HEAD, fontSize: 17, bold: true, color: ICE });
    s.addText(it[2], { x: x + 0.25, y: y + 1.1, w: 5.35, h: 1.75, fontFace: FONT, fontSize: 11.5, color: WHITE, lineSpacingMultiple: 1.35, valign: "top" });
  });

  s.addShape("roundRect", { x: 0.6, y: 4.95, w: 12.13, h: 1.15, rectRadius: 0.12, fill: { color: ICE_TINT }, line: { type: "none" } });
  s.addText(
    "Consciously left off the top two: real scheduling and hosted deployment. Both matter eventually, but this is a local case-study submission, not a production rollout yet — solving them now would be effort spent ahead of actual need.",
    { x: 0.9, y: 5.1, w: 11.55, h: 0.85, fontFace: FONT, fontSize: 12, italic: true, color: INK, lineSpacingMultiple: 1.3, valign: "middle" }
  );
  footer(s, 10, false);
}

// ---------------------------------------------------------------- Slide 11: Real stakeholder influence
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  sectionHeader(s, "flag.png", "Where I've had to move people, not just data", "Real stakeholder influence — beyond this case study");

  const colW = 5.9, colGap = 0.33, colX0 = 0.6, colY = 1.6, colH = 5.0;
  const cols = [
    {
      title: "Bigtincan — legacy reporting migration", x: colX0,
      parts: [
        ["Situation", "Head of Data mandated migrating legacy reporting to a modern BI platform on Databricks — 300+ customers globally, deadline forced by an expiring software licence."],
        ["What I pushed for", "Not a like-for-like migration. I proposed defining higher-level reporting requirements and a reusable data model instead — so customers could build new reports themselves, not wait on us to rebuild every existing one."],
        ["Outcome", "Convinced the product team to trade migration speed for genuine self-serve capability."],
      ],
    },
    {
      title: "Allianz — actuarial reserving automation", x: colX0 + colW + colGap,
      parts: [
        ["Situation", "Currently driving automation of the actuarial reserving process across three product lines — general insurance, CTP, workers comp — each with different rules."],
        ["What I pushed for", "Rather than three bespoke solutions, defined a strategy for reusable components that work across all three, and worked the plan through with business stakeholders before any build started."],
        ["Outcome", "One architecture, three product lines, self-serve capability designed in from the start."],
      ],
    },
  ];
  cols.forEach((col) => {
    s.addShape("roundRect", { x: col.x, y: colY, w: colW, h: colH, rectRadius: 0.12, fill: { color: ICE_TINT }, line: { type: "none" } });
    s.addText(col.title, { x: col.x + 0.28, y: colY + 0.2, w: colW - 0.56, h: 0.55, fontFace: FONT, fontSize: 14, bold: true, color: NAVY, valign: "top" });
    let iy = colY + 0.85;
    col.parts.forEach(([label, text]) => {
      s.addText(label.toUpperCase(), { x: col.x + 0.28, y: iy, w: colW - 0.56, h: 0.28, fontFace: FONT, fontSize: 9.5, bold: true, color: "6B7BB0", charSpacing: 1 });
      s.addText(text, { x: col.x + 0.28, y: iy + 0.28, w: colW - 0.56, h: 1.05, fontFace: FONT, fontSize: 11, color: INK, lineSpacingMultiple: 1.22, valign: "top" });
      iy += 1.38;
    });
  });
  footer(s, 11, false);
}

// ---------------------------------------------------------------- Slide 12: Closing
{
  const s = pres.addSlide();
  s.background = { color: NAVY_DARK };
  iconCircle(s, "compass.png", PAGE_W / 2 - 0.45, 0.6, 0.9, NAVY, 0.55);
  s.addText("Same standard, at scale", { x: 1.0, y: 1.75, w: PAGE_W - 2.0, h: 0.6, fontFace: FONT_HEAD, fontSize: 28, bold: true, color: WHITE, align: "center", valign: "middle" });

  const scaleLines = [
    "Real-time metrics leaders actually use — not manual reporting.",
    "Analytics built into every product from day one — not bolted on after.",
    "Data that drives decisions — not decorates them.",
  ];
  let sy = 2.55;
  scaleLines.forEach((line) => {
    s.addText(line, { x: 1.5, y: sy, w: PAGE_W - 3.0, h: 0.4, fontFace: FONT, fontSize: 14, italic: true, color: ICE, align: "center", valign: "middle" });
    sy += 0.42;
  });

  s.addText("Thank you — questions, and a live look at the dashboard", { x: 1.0, y: 4.15, w: PAGE_W - 2.0, h: 0.45, fontFace: FONT, fontSize: 14, bold: true, color: WHITE, align: "center" });

  const links = [
    ["Repository", "github.com/donimalai/market_trends"],
    ["Run locally", "python run_pipeline.py  &&  streamlit run src/dashboard/app.py"],
  ];
  let ly = 4.9;
  links.forEach(([l, v]) => {
    s.addText(l, { x: 1.3, y: ly, w: 2.2, h: 0.4, fontFace: FONT, fontSize: 12, bold: true, color: "9AA6D6", align: "right" });
    s.addText(v, { x: 3.7, y: ly, w: 8.3, h: 0.4, fontFace: FONT, fontSize: 13, color: WHITE, align: "left" });
    ly += 0.55;
  });
  footer(s, 12, true);
}

pres.writeFile({ fileName: path.join(__dirname, "Market_Intelligence_Platform.pptx") }).then((fileName) => {
  console.log("Wrote", fileName);
});
