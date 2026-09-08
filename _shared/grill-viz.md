# grill-viz — shared HTML artifact visualization for the grill skills + grill-verify

Shared procedure + self-contained HTML skeleton used by `grill-yourself`, `grill-review`,
and `grill-verify` to render their output as a local HTML dashboard. This file is NOT an
invocable skill (it has no `SKILL.md`/frontmatter); each grill skill reads it by path.

**This runs only when the invoking skill was given the `--viz` flag.** No `--viz` → the
skill's normal chat output is the entire deliverable and none of this happens.

## Non-negotiables (inherited from each grill skill)
- **Chat output is the primary deliverable and is emitted FIRST, unchanged.** The
  artifact is a *supplementary* follow-up rendered after the normal chat message. It never
  replaces, delays, or alters that message.
- **The only file this procedure may write is a scratchpad HTML file.** Never the plan
  `.md`, never project code, never docs. This is the scratchpad carve-out each grill skill
  documents in its own Hard constraints; honor it strictly.
- If anything here fails, fall back (step 5) — never let visualization failure swallow or
  delay the chat report.

## How a skill loads this
Each grill skill's invocation header gives `Base directory for this skill: <dir>`. This
shared file lives as a sibling of every grill skill directory, so read it at:
`<that base directory>/../_shared/grill-viz.md`
(e.g. base `<repo>/.agents/skills/grill-review` →
`<repo>/.agents/skills/_shared/grill-viz.md`).

## Procedure (only when `--viz`)
1. **Emit the normal chat output first** (the plan, or the translated review/verify
   report). Do not skip or abbreviate it. Only after it is on the table, continue.
2. **Build the data object** for the run (see *Data contract*), mapping the skill's own
   output into it. Fields the skill doesn't produce stay omitted — the skeleton renders
   missing optionals gracefully.
3. **Write the HTML** to the OS temporary directory named `grill-<skill>-<slug>.html`
   (`<skill>` = `yourself`/`review`/`grill-verify`; `<slug>` = a short kebab slug of the plan
   title). Start from the *HTML skeleton* below, set the `<title>`, and inject the data
   object by replacing the exact token `/*__GRILL_DATA__*/{}` with your JSON object literal
   (swap the whole token, including the trailing `{}` empty-default — leaving it produces
   `= <json> {}` which is a syntax error).
4. **Present the file path** in the final response as a clickable local file link. When
   decisions change, rewrite the same file and report that path again. The chat report
   remains the primary deliverable.

## Data contract (JSON swapped in for the `/*__GRILL_DATA__*/{}` token)
```jsonc
{
  "title": "string",            // page <title> + header; e.g. the plan title
  "subtitle": "string?",        // optional one-line context (mode, scope, model)
  "disposition": "string?",     // review/verify banner text, e.g. "SHIP — Blocker 0, Advisory 1"
  "dispositionKind": "string?", // one of ship|revise|reject|clean|verified|pass|fix|fail (banner color)
  "buckets": [                  // grill-yourself: two buckets (Confident / Needs-you).
    {                           // grill-review: ONE bucket (the flat verdict table), e.g. name "비판".
      "name": "string",
      "rows": [
        {
          "n": "string|number", // decision # (or "—")
          "question": "string", // grill-yourself: the decision question.
                                //  grill-review: put the FULL "결정" text here; leave `answer` omitted.
          "answer": "string?",  // grill-yourself: the recommended answer. (review omits.)
          "axis": "string?",    // review/verify: the axis (모순/숨겨진 가정/…)
          "verdict": "string?", // confirmed | false | unverifiable  (review) / implemented|deviated|missing|unverifiable (verify)
          "severity": "string?",// blocker | advisory | confident | confirmed  → drives the badge color
          "rationale": "string?"// one-line rationale / criticism, may contain file:line
        }
      ]
    }
  ],
  "planBody": "string?",        // grill-yourself: the free-text "## Design spec" narrative (markdown-ish, rendered as pre-wrapped text)
  "revisions": [ { "n": "string", "from": "string", "to": "string", "note": "string?" } ],  // review 수정안 / verify 갭
  "realityTrace": [ "string" ], // review reality-check trace / verify dynamic-verification trace lines
  "reGrillList": { "autoFixable": [ "string" ], "needsYou": [ "string" ] }
}
```
Consumers:
- **grill-yourself** fills `title`, `buckets` (Confident + Needs-you), `planBody`. Leaves
  `disposition`/`verdict`/`axis`/`revisions`/`realityTrace`/`reGrillList` omitted.
- **grill-review** fills `title`, `subtitle`, `disposition(+Kind)`, a single `buckets`
  entry whose rows carry `axis`/`verdict`/`severity`/`rationale` (with `question` = full
  결정, `answer` omitted), plus `revisions`, `realityTrace`, `reGrillList`.
- **grill-verify** (later) reuses `severity` and `realityTrace` (as the dynamic-verification
  trace) for its three-layer verdict, adding only the optional fields it needs.

## HTML skeleton
Use a complete, standalone document with inline CSS and JavaScript, theme-aware and
responsive (no horizontal page scroll; wide blocks scroll inside their own container).
Replace the `<title>` text and swap the whole `/*__GRILL_DATA__*/{}` token for the JSON
literal; preserve the remaining skeleton unless the visualization needs a focused change.

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>grill visualization</title>
<style>
  :root{
    --bg:#f7f7f8; --card:#ffffff; --ink:#1a1a1c; --muted:#6b6b73; --line:#e3e3e8;
    --accent:#5b5bd6;
    --blocker:#c0362c; --blocker-bg:#fbeae8;
    --advisory:#9a6a00; --advisory-bg:#fcf3e0;
    --ok:#1f7a4d; --ok-bg:#e7f4ec;
    --neutral:#5a5a63; --neutral-bg:#eeeef1;
  }
  @media (prefers-color-scheme: dark){
    :root{
      --bg:#161618; --card:#1f1f22; --ink:#ececf0; --muted:#9a9aa2; --line:#2e2e33;
      --accent:#9d9df0;
      --blocker:#ff8a7e; --blocker-bg:#3a1f1c;
      --advisory:#e6b64c; --advisory-bg:#352a10;
      --ok:#68d19b; --ok-bg:#123626;
      --neutral:#b6b6be; --neutral-bg:#2a2a2f;
    }
  }
  :root[data-theme="light"]{
    --bg:#f7f7f8; --card:#ffffff; --ink:#1a1a1c; --muted:#6b6b73; --line:#e3e3e8; --accent:#5b5bd6;
    --blocker:#c0362c; --blocker-bg:#fbeae8; --advisory:#9a6a00; --advisory-bg:#fcf3e0;
    --ok:#1f7a4d; --ok-bg:#e7f4ec; --neutral:#5a5a63; --neutral-bg:#eeeef1;
  }
  :root[data-theme="dark"]{
    --bg:#161618; --card:#1f1f22; --ink:#ececf0; --muted:#9a9aa2; --line:#2e2e33; --accent:#9d9df0;
    --blocker:#ff8a7e; --blocker-bg:#3a1f1c; --advisory:#e6b64c; --advisory-bg:#352a10;
    --ok:#68d19b; --ok-bg:#123626; --neutral:#b6b6be; --neutral-bg:#2a2a2f;
  }
  *{box-sizing:border-box}
  .wrap{max-width:960px;margin:0 auto;padding:24px 18px 64px;color:var(--ink);
    background:var(--bg);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
  .top{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;flex-wrap:wrap}
  h1{font-size:22px;margin:0 0 4px;letter-spacing:-.01em}
  .subtitle{color:var(--muted);font-size:13px;margin:0 0 6px}
  .theme-btn{border:1px solid var(--line);background:var(--card);color:var(--ink);
    border-radius:8px;padding:6px 10px;font-size:12px;cursor:pointer}
  .banner{margin:14px 0 20px;padding:12px 14px;border-radius:10px;font-weight:600;
    border:1px solid var(--line);background:var(--neutral-bg);color:var(--ink)}
  .banner.ship,.banner.pass,.banner.verified,.banner.clean{background:var(--ok-bg);border-color:var(--ok);color:var(--ok)}
  .banner.revise,.banner.fix{background:var(--advisory-bg);border-color:var(--advisory);color:var(--advisory)}
  .banner.reject,.banner.fail{background:var(--blocker-bg);border-color:var(--blocker);color:var(--blocker)}
  .bucket{margin:22px 0 8px}
  .bucket h2{font-size:14px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);margin:0 0 10px}
  .grid{display:grid;grid-template-columns:1fr;gap:10px}
  .card{border:1px solid var(--line);background:var(--card);border-radius:10px;padding:12px 14px}
  .card .head{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
  .num{font-variant-numeric:tabular-nums;color:var(--muted);font-size:12px;min-width:20px}
  .q{font-weight:600}
  .a{margin-top:4px}
  .a .lbl,.meta .lbl{color:var(--muted);font-size:12px;margin-right:4px}
  .badges{display:flex;gap:6px;flex-wrap:wrap;margin-left:auto}
  .badge{font-size:11px;font-weight:700;padding:2px 8px;border-radius:999px;
    background:var(--neutral-bg);color:var(--neutral);white-space:nowrap}
  .badge.blocker{background:var(--blocker-bg);color:var(--blocker)}
  .badge.advisory{background:var(--advisory-bg);color:var(--advisory)}
  .badge.confident,.badge.confirmed,.badge.implemented{background:var(--ok-bg);color:var(--ok)}
  .badge.false,.badge.deviated,.badge.missing{background:var(--blocker-bg);color:var(--blocker)}
  .badge.unverifiable{background:var(--advisory-bg);color:var(--advisory)}
  details{margin-top:8px;border-top:1px dashed var(--line);padding-top:8px}
  summary{cursor:pointer;color:var(--accent);font-size:13px}
  details .body{margin-top:6px;color:var(--ink);font-size:13.5px}
  code,.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px}
  .section{margin:26px 0}
  .section h2{font-size:15px;margin:0 0 8px}
  .pre{white-space:pre-wrap;word-break:break-word;background:var(--card);border:1px solid var(--line);
    border-radius:10px;padding:12px 14px;font-size:13.5px}
  ul.plain{margin:0;padding-left:18px}
  ul.plain li{margin:3px 0}
  .rev{border:1px solid var(--line);border-radius:8px;padding:8px 10px;margin:6px 0;background:var(--card)}
  .rev .from{color:var(--blocker)} .rev .to{color:var(--ok);font-weight:600}
  .cols{display:grid;grid-template-columns:1fr 1fr;gap:14px}
  @media (max-width:640px){.cols{grid-template-columns:1fr}}
  .empty{color:var(--muted);font-style:italic;font-size:13px}
</style>
</head>
<body>

<div class="wrap" id="app"></div>

<script>
const DATA = /*__GRILL_DATA__*/{};

const el=(t,c,txt)=>{const e=document.createElement(t);if(c)e.className=c;if(txt!=null)e.textContent=txt;return e;};
const sev=s=>(s||"").toLowerCase();

function badge(text, cls){ const b=el("span","badge "+cls, text); return b; }

function renderCard(row){
  const card=el("div","card");
  const head=el("div","head");
  if(row.n!=null && row.n!=="") head.appendChild(el("span","num",String(row.n)));
  head.appendChild(el("span","q", row.question||""));
  const badges=el("div","badges");
  if(row.verdict) badges.appendChild(badge(row.verdict, sev(row.verdict)));
  if(row.severity) badges.appendChild(badge(row.severity, sev(row.severity)));
  if(row.axis) badges.appendChild(badge(row.axis, "neutral"));
  if(badges.childNodes.length) head.appendChild(badges);
  card.appendChild(head);
  if(row.answer){ const a=el("div","a"); a.appendChild(el("span","lbl","→")); a.appendChild(document.createTextNode(row.answer)); card.appendChild(a); }
  if(row.rationale){
    const d=el("details"); d.appendChild(el("summary","","근거 / rationale"));
    const body=el("div","body"); body.textContent=row.rationale; d.appendChild(body); card.appendChild(d);
  }
  return card;
}

function renderBucket(bk){
  const wrap=el("div","bucket");
  if(bk.name) wrap.appendChild(el("h2","",bk.name));
  const grid=el("div","grid");
  (bk.rows||[]).forEach(r=>grid.appendChild(renderCard(r)));
  if(!(bk.rows||[]).length) grid.appendChild(el("div","empty","(none)"));
  wrap.appendChild(grid);
  return wrap;
}

function section(title, node){
  const s=el("div","section"); s.appendChild(el("h2","",title)); s.appendChild(node); return s;
}

function render(){
  const app=document.getElementById("app"); app.innerHTML="";
  document.title = DATA.title || "grill visualization";

  const top=el("div","top");
  const left=el("div");
  left.appendChild(el("h1","",DATA.title||"grill visualization"));
  if(DATA.subtitle) left.appendChild(el("p","subtitle",DATA.subtitle));
  top.appendChild(left);
  const btn=el("button","theme-btn","◐ theme");
  btn.onclick=()=>{ const r=document.documentElement;
    const cur=r.getAttribute("data-theme")|| (matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light");
    r.setAttribute("data-theme", cur==="dark"?"light":"dark"); };
  top.appendChild(btn);
  app.appendChild(top);

  if(DATA.disposition){
    const b=el("div","banner "+(DATA.dispositionKind||"").toLowerCase(), DATA.disposition);
    app.appendChild(b);
  }

  (DATA.buckets||[]).forEach(bk=>app.appendChild(renderBucket(bk)));

  if(DATA.planBody){
    app.appendChild(section("Plan", (()=>{const p=el("div","pre");p.textContent=DATA.planBody;return p;})()));
  }

  if((DATA.revisions||[]).length){
    const box=el("div");
    DATA.revisions.forEach(r=>{
      const rv=el("div","rev");
      const head=el("div"); if(r.n!=null) head.appendChild(el("span","num",String(r.n)+" "));
      head.appendChild(el("span","from",(r.from||"")+" ")); head.appendChild(el("span","","→ "));
      head.appendChild(el("span","to",r.to||"")); rv.appendChild(head);
      if(r.note){ const nt=el("div","",r.note); nt.style.color="var(--muted)"; nt.style.fontSize="13px"; nt.style.marginTop="3px"; rv.appendChild(nt); }
      box.appendChild(rv);
    });
    app.appendChild(section("수정안 / Revisions", box));
  }

  if(DATA.reGrillList && ((DATA.reGrillList.autoFixable||[]).length || (DATA.reGrillList.needsYou||[]).length)){
    const cols=el("div","cols");
    const mk=(title,arr)=>{ const c=el("div"); c.appendChild(el("h2","",title)); const ul=el("ul","plain");
      (arr||[]).forEach(x=>ul.appendChild(el("li","",x))); if(!(arr||[]).length) ul.appendChild(el("li","empty","(none)")); c.appendChild(ul); return c; };
    cols.appendChild(mk("Auto-fixable", DATA.reGrillList.autoFixable));
    cols.appendChild(mk("Needs you", DATA.reGrillList.needsYou));
    app.appendChild(section("Re-grill list", cols));
  }

  if((DATA.realityTrace||[]).length){
    const ul=el("ul","plain"); DATA.realityTrace.forEach(x=>ul.appendChild(el("li","",x)));
    app.appendChild(section("Reality / verification trace", ul));
  }
}
render();
</script>
</body>
</html>
```
