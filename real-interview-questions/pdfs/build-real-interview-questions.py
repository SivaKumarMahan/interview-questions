#!/usr/bin/env python3
"""
Build a single designed PDF from the markdown files in real-interview-questions/.

Usage:
    python3 real-interview-questions/pdfs/build-real-interview-questions.py

Requires: python3-markdown, pygments, google-chrome (headless print-to-pdf).
"""

import html
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

import markdown

OUT_DIR = Path(__file__).resolve().parent
SRC_DIR = OUT_DIR.parent
OUT_PDF = OUT_DIR / "real-interview-questions.pdf"

# (filename, display name, subtitle, accent key)
DOCS = [
    ("ATC.md", "ATC", "Kubernetes, Terraform, containers, load balancers and Jenkins", "indigo"),
    ("DelloiteLLP.md", "Deloitte LLP", "Terraform recovery, scripting automation, Git and DevOps MCQs", "green"),
    ("InnovarTech.md", "Innovar Tech", "Three-tier app architecture, Dockerfiles and the end-to-end flow", "amber"),
]

ACCENTS = {
    "indigo": ("#4f46e5", "#eef2ff", "#c7d2fe"),
    "green": ("#15803d", "#ecfdf5", "#bbf7d0"),
    "amber": ("#c2410c", "#fff7ed", "#fed7aa"),
}

DIAGRAM_HINT = re.compile(
    r"[│├└─┌┐┘↓→⇒]|^\s*\|\s*$|\+--|-->|\s->\s|^\s{2,}\||^\s*[-=_]{4,}\s*$", re.M
)

FENCE = re.compile(r"^```([A-Za-z0-9_+-]*)[ \t]*\n(.*?)^```[ \t]*$", re.M | re.S)


def tag_diagrams(md_text: str) -> str:
    """Turn language-less ASCII-art fences into styled diagram blocks."""

    def repl(m):
        lang, body = m.group(1), m.group(2)
        if lang:
            return m.group(0)
        if not DIAGRAM_HINT.search(body):
            return m.group(0)
        return (
            '\n<div class="diagram"><pre>'
            + html.escape(body.rstrip("\n"))
            + "</pre></div>\n"
        )

    return FENCE.sub(repl, md_text)


def slugify(text: str, prefix: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return f"{prefix}-{s}"[:80]


def split_title(text: str):
    """'3. VM vs Container' -> ('3', 'VM vs Container')."""
    m = re.match(r"^(?:Q)?(\d+)[.)]\s+(.*)$", text)
    if m:
        return m.group(1), m.group(2)
    return None, text


def prepare(md_text: str, prefix: str):
    """Strip the leading H1, demote stray H1s, add anchors, collect the outline."""
    lines = md_text.splitlines()
    out, outline = [], []
    seen_first_h1 = False
    in_fence = False
    used = set()

    def unique(base):
        hid, n = base, 2
        while hid in used:
            hid, n = f"{base}-{n}", n + 1
        used.add(hid)
        return hid

    for line in lines:
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        if in_fence:
            out.append(line)
            continue

        h1 = re.match(r"^#\s+(.*)$", line)
        h2 = re.match(r"^##\s+(.*)$", line)
        h3 = re.match(r"^###\s+(.*)$", line)

        if h1:
            if not seen_first_h1:
                seen_first_h1 = True
                continue  # the file title becomes the section header
            title = h1.group(1).strip()
            pid = unique(slugify(title, prefix))
            outline.append({"kind": "part", "title": title, "id": pid})
            out.append(f'\n<div class="partbreak" id="{pid}"><span>{html.escape(title)}</span></div>\n')
            continue

        if h2:
            raw = h2.group(1).strip()
            num, title = split_title(raw)
            hid = unique(slugify(raw, prefix))
            if num:
                outline.append({"kind": "q", "badge": num, "title": title, "id": hid})
                out.append(f"## {title} {{#{hid} .qhead data-badge={num}}}")
            else:
                outline.append({"kind": "topic", "title": title, "id": hid})
                out.append(f"## {title} {{#{hid} .subhead}}")
            continue

        if h3:
            raw = h3.group(1).strip()
            hid = unique(slugify(raw, prefix))
            outline.append({"kind": "h3", "title": raw, "id": hid})
            out.append(f"### {raw} {{#{hid}}}")
            continue

        out.append(line)

    return "\n".join(out), outline


def convert(md_text: str) -> str:
    return markdown.markdown(
        md_text,
        extensions=["fenced_code", "tables", "attr_list", "sane_lists", "codehilite"],
        extension_configs={
            "codehilite": {"guess_lang": False, "linenums": False}
        },
    )


def postprocess(body: str) -> str:
    # number badges on question headings
    def badge(m):
        attrs, text = m.group(1), m.group(2)
        b = re.search(r'data-badge="?([\w]+)"?', attrs)
        attrs = re.sub(r'\s*data-badge="?[\w]+"?', "", attrs)
        if not b:
            return f"<h2{attrs}><span class=\"qtext\">{text}</span></h2>"
        return (
            f'<h2{attrs}><span class="qnum">{b.group(1)}</span>'
            f'<span class="qtext">{text}</span></h2>'
        )

    body = re.sub(r'<h2([^>]*)>(.*?)</h2>', badge, body, flags=re.S)

    # quoted paragraphs become interview-answer callouts, but never inside a
    # blockquote (which is already rendered as a callout)
    def callout(m):
        inner = m.group(1).strip()
        if inner.startswith("&quot;") or inner.startswith("“") or inner.startswith('"'):
            return f'<div class="callout"><p>{inner}</p></div>'
        return m.group(0)

    parts = re.split(r"(<blockquote>.*?</blockquote>)", body, flags=re.S)
    body = "".join(
        p if p.startswith("<blockquote>") else re.sub(r"<p>(.*?)</p>", callout, p, flags=re.S)
        for p in parts
    )

    # blockquotes are callouts too
    body = body.replace("<blockquote>", '<blockquote class="callout">')
    return body


CSS = """
:root{
  --ink:#0f172a; --body:#334155; --muted:#64748b; --line:#e2e8f0; --soft:#f8fafc;
  --accent:#4f46e5; --accent-soft:#eef2ff; --accent-line:#c7d2fe;
  --code-bg:#0f172a; --code-fg:#e2e8f0;
}
*{box-sizing:border-box;}
html{-webkit-print-color-adjust:exact; print-color-adjust:exact;}
body{
  margin:0; color:var(--body);
  font:11pt/1.62 "Helvetica Neue",Helvetica,Arial,"Segoe UI",sans-serif;
  letter-spacing:.005em;
}
@page{ size:A4; margin:15mm 14mm 16mm; }
@page:first{ margin:0; }

code,kbd,pre{font-family:"SF Mono",SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;}

/* ---------- cover ---------- */
.cover{
  height:297mm; padding:26mm 22mm 20mm; page-break-after:always;
  display:flex; flex-direction:column;
  background:
    radial-gradient(900px 420px at 88% -8%, #1e293b 0%, rgba(30,41,59,0) 62%),
    linear-gradient(158deg,#0b1220 0%,#111c33 46%,#0d1a2b 100%);
  color:#e7ecf5; position:relative; overflow:hidden;
}
.cover::after{
  content:""; position:absolute; left:0; right:0; bottom:0; height:9mm;
  background:linear-gradient(90deg,#4f46e5 0 33.33%,#15803d 33.33% 66.66%,#c2410c 66.66% 100%);
}
.cover .eyebrow{
  font-size:8.5pt; letter-spacing:.20em; text-transform:uppercase;
  color:#8ea3c9; font-weight:700;
}
.cover h1{
  margin:8mm 0 0; font-size:39pt; line-height:1.04; letter-spacing:-.022em;
  color:#fff; font-weight:800; max-width:150mm;
}
.cover .rule{width:34mm; height:4px; background:#4f46e5; margin:7mm 0 8mm; border-radius:3px;}
.cover .lede{font-size:11.5pt; line-height:1.65; color:#b9c6de; max-width:135mm;}
.stats{display:flex; gap:5mm; margin-top:14mm;}
.stats div{flex:1; border-top:2px solid rgba(255,255,255,.16); padding-top:3.5mm;}
.stats .v{font-size:24pt; font-weight:800; color:#fff; line-height:1; letter-spacing:-.02em;}
.stats .l{margin-top:2mm; font-size:8pt; letter-spacing:.14em; text-transform:uppercase; color:#8ea3c9; font-weight:700;}
.legend{margin-top:auto; margin-bottom:13mm; border:1px solid rgba(255,255,255,.13); border-radius:10px; padding:7mm 7mm 6mm; background:rgba(255,255,255,.04);}
.legend h3{margin:0 0 5mm; padding:0; border:0; font-size:8.5pt; letter-spacing:.18em; text-transform:uppercase; color:#8ea3c9; font-weight:700;}
.legend .row{display:flex; align-items:baseline; gap:4mm; padding:2.6mm 0; border-top:1px solid rgba(255,255,255,.08);}
.legend .row:first-of-type{border-top:0;}
.legend .dot{width:9px;height:9px;border-radius:50%;flex:0 0 9px;}
.legend .nm{font-weight:700;color:#fff;font-size:11pt;min-width:34mm;}
.legend .ds{color:#9fb0cd;font-size:9.5pt;line-height:1.45;flex:1;}
.legend .ct{color:#e7ecf5;font-size:8.5pt;font-weight:700;white-space:nowrap;
  background:rgba(255,255,255,.10); border-radius:20px; padding:1.2mm 3mm;}
.cover .foot{position:absolute; left:22mm; right:22mm; bottom:16mm; display:flex;
  justify-content:space-between; font-size:8.5pt; color:#7f92b5; letter-spacing:.06em;}

/* ---------- contents ---------- */
.toc{page-break-after:always;}
.toc h2.plain{font-size:22pt;color:var(--ink);margin:0 0 2mm;letter-spacing:-.015em;}
.toc .sub{color:var(--muted); font-size:10pt; margin:0 0 9mm;}
.tocgroup{margin:0 0 8mm; break-inside:avoid;}
.tocgroup .gh{display:flex;align-items:center;gap:3mm;margin:0 0 3.5mm;}
.tocgroup .gh .bar{width:4px;height:16px;border-radius:2px;}
.tocgroup .gh .nm{font-weight:800;color:var(--ink);font-size:12.5pt;letter-spacing:-.01em;}
.tocgroup .gh .ds{color:var(--muted);font-size:9pt;}
.toclist{display:grid;grid-template-columns:1fr 1fr;gap:0 8mm;}
.toclist a{display:flex;gap:2.5mm;align-items:baseline;text-decoration:none;color:var(--body);
  font-size:9.3pt;padding:1.5mm 0;border-bottom:1px dotted var(--line);line-height:1.35;}
.toclist a .n{font-weight:700;font-size:8pt;min-width:6mm;text-align:right;}
.toclist a.part{grid-column:1 / -1;font-weight:700;color:var(--ink);border-bottom:0;padding-top:3mm;}
.toclist a .n.topic{font-size:12pt;line-height:.6;}
.sublist{grid-column:1 / -1; margin:1.5mm 0 0 8mm; padding:2.5mm 4mm; border-radius:6px;
  background:var(--soft); border:1px solid var(--line); font-size:8.8pt; line-height:1.7;}
.sublist a.sub{display:inline; color:var(--muted); border:0; padding:0;}
.sublist .sep{color:#94a3b8;}

/* ---------- section opener ---------- */
.sectionhead{page-break-before:always; margin:0 0 9mm; padding:0 0 6mm; border-bottom:2px solid var(--line);}
.sectionhead .eyebrow{font-size:8pt;letter-spacing:.2em;text-transform:uppercase;font-weight:800;}
.sectionhead h1{margin:2.5mm 0 0;font-size:27pt;line-height:1.08;color:var(--ink);letter-spacing:-.022em;font-weight:800;}
.sectionhead .bar{width:24mm;height:4px;border-radius:3px;margin:4mm 0 5mm;}
.sectionhead p{margin:0;color:var(--muted);font-size:10.5pt;max-width:150mm;}
.sectionhead .chips{margin-top:5mm;display:flex;gap:2.5mm;flex-wrap:wrap;}
.sectionhead .chip{font-size:8pt;font-weight:700;letter-spacing:.05em;text-transform:uppercase;
  padding:1.4mm 3.2mm;border-radius:20px;}

/* ---------- headings ---------- */
h2.qhead{
  display:flex; gap:4mm; align-items:flex-start; margin:11mm 0 4mm;
  font-size:15pt; line-height:1.28; color:var(--ink); font-weight:800; letter-spacing:-.014em;
  break-after:avoid; break-inside:avoid;
  padding-top:4mm; border-top:1px solid var(--line);
}
h2.qhead:first-of-type{margin-top:0;border-top:0;padding-top:0;}
.qnum{
  flex:0 0 8.5mm; height:8.5mm; border-radius:50%; background:var(--accent); color:#fff;
  font-size:9.5pt; font-weight:800; display:flex; align-items:center; justify-content:center;
  margin-top:.6mm;
}
.qtext{flex:1;}
h2.subhead{
  margin:10mm 0 4mm; padding:0 0 2.5mm; border-bottom:2px solid var(--accent-line);
  font-size:13pt; color:var(--ink); font-weight:800; letter-spacing:-.012em;
  break-after:avoid; break-inside:avoid;
}
section h3{
  margin:7mm 0 2.5mm; font-size:11.5pt; color:var(--ink); font-weight:750; letter-spacing:-.008em;
  break-after:avoid; padding-left:3.5mm; border-left:3px solid var(--accent-line);
}
h4{margin:5mm 0 2mm;font-size:10.5pt;color:var(--ink);font-weight:700;break-after:avoid;}
section hr{display:none;}
.partbreak{
  margin:12mm 0 7mm; padding:4.5mm 6mm; border-radius:8px;
  background:var(--accent-soft); border-left:5px solid var(--accent); break-inside:avoid; break-after:avoid;
}
.partbreak span{font-size:12.5pt;font-weight:800;color:var(--ink);letter-spacing:-.01em;}

/* ---------- text ---------- */
p{margin:0 0 3.4mm;}
strong{color:var(--ink);font-weight:700;}
ul,ol{margin:0 0 4mm; padding-left:6mm;}
li{margin:0 0 1.6mm; padding-left:1mm;}
li::marker{color:var(--accent);font-weight:700;}
hr{border:0;border-top:1px solid var(--line);margin:8mm 0;}
a{color:var(--accent);text-decoration:none;}

p code, li code, td code, h3 code, h2 code{
  background:var(--soft); border:1px solid var(--line); border-radius:4px;
  padding:.3mm 1.4mm; font-size:9pt; color:#b91c1c;
}

/* ---------- callouts ---------- */
.callout{
  margin:0 0 4mm; padding:4mm 5mm 4mm 6mm; border-radius:0 8px 8px 0;
  background:var(--accent-soft); border-left:4px solid var(--accent);
  break-inside:avoid;
}
.callout p{margin:0 0 2.5mm; color:#1e293b; font-size:10.3pt; line-height:1.6;}
.callout p:last-child{margin:0;}
blockquote{margin:0 0 4mm;}

/* ---------- code ---------- */
.codehilite, pre{
  background:var(--code-bg); color:var(--code-fg); border-radius:8px;
  margin:0 0 4.5mm; overflow:hidden;
}
.codehilite pre, .diagram pre{margin:0;}
.codehilite pre, pre{padding:4mm 5mm; font-size:8.6pt; line-height:1.55; white-space:pre-wrap; word-break:break-word;}
.codehilite{border:1px solid #1e293b;}
.diagram{
  background:#f1f5f9; border:1px solid #dbe3ec; border-left:4px solid var(--accent);
  border-radius:8px; margin:0 0 4.5mm; break-inside:avoid;
}
.diagram pre{
  background:transparent; color:#334155; padding:4.5mm 5mm; font-size:8.6pt; line-height:1.5;
  white-space:pre; overflow-x:hidden;
}

/* pygments - dark palette */
.codehilite .c,.codehilite .c1,.codehilite .cm,.codehilite .cs{color:#7c8ba1;font-style:italic;}
.codehilite .k,.codehilite .kd,.codehilite .kn,.codehilite .kt,.codehilite .kr,.codehilite .kc{color:#c4b5fd;font-weight:600;}
.codehilite .s,.codehilite .s1,.codehilite .s2,.codehilite .sb,.codehilite .se,.codehilite .sd{color:#86efac;}
.codehilite .nb,.codehilite .bp{color:#7dd3fc;}
.codehilite .nf,.codehilite .fm{color:#93c5fd;}
.codehilite .nt{color:#f0abfc;}
.codehilite .na{color:#fcd34d;}
.codehilite .nv,.codehilite .vi,.codehilite .vg{color:#fda4af;}
.codehilite .m,.codehilite .mi,.codehilite .mf{color:#fdba74;}
.codehilite .o,.codehilite .ow{color:#e2e8f0;}
.codehilite .p{color:#cbd5e1;}
.codehilite .err{color:#fca5a5;}

/* ---------- tables ---------- */
table{width:100%;border-collapse:collapse;margin:0 0 5mm;font-size:9.4pt;break-inside:avoid;}
th{background:var(--ink);color:#fff;text-align:left;font-weight:700;padding:2.6mm 3.2mm;
  font-size:8.6pt;letter-spacing:.03em;text-transform:uppercase;}
td{padding:2.4mm 3.2mm;border-bottom:1px solid var(--line);vertical-align:top;}
tbody tr:nth-child(even){background:var(--soft);}
td:first-child{font-weight:600;color:var(--ink);}

/* ---------- misc print ---------- */
h2,h3,h4{page-break-after:avoid;}
img{max-width:100%;}
"""


def build_html() -> str:
    sections, tocs, meta = [], [], []

    for idx, (fname, name, subtitle, accent) in enumerate(DOCS, start=1):
        raw = (SRC_DIR / fname).read_text(encoding="utf-8")
        raw = tag_diagrams(raw)
        prefix = f"s{idx}"
        prepped, outline = prepare(raw, prefix)
        body = postprocess(convert(prepped))

        acc, soft, line = ACCENTS[accent]
        qcount = sum(1 for o in outline if o["kind"] == "q")
        topics = sum(1 for o in outline if o["kind"] == "topic")
        parts = sum(1 for o in outline if o["kind"] == "h3")
        codecount = body.count("<div class=\"codehilite\">")
        diagcount = body.count('<div class="diagram">')

        def chip(label):
            return f'<span class="chip" style="background:{soft};color:{acc}">{label}</span>'

        chips = (
            chip(f"{qcount} question" + ("" if qcount == 1 else "s"))
            + chip(f"{parts} sections")
            + chip(f"{codecount} code samples")
            + chip(f"{diagcount} diagrams")
        )

        sections.append(
            f'<section style="--accent:{acc};--accent-soft:{soft};--accent-line:{line}">'
            f'<div class="sectionhead">'
            f'<div class="eyebrow" style="color:{acc}">Company {idx:02d} · Interview questions</div>'
            f"<h1>{html.escape(name)}</h1>"
            f'<div class="bar" style="background:{acc}"></div>'
            f"<p>{html.escape(subtitle)}</p>"
            f'<div class="chips">{chips}</div>'
            f"</div>{body}</section>"
        )

        meta.append({
            "name": name, "sub": subtitle, "acc": acc,
            "q": qcount + topics, "code": codecount, "diag": diagcount,
        })

        # when a company has only a question or two, list its sub-sections too
        show_h3 = qcount + topics <= 2

        items, pending = [], []

        def flush():
            if pending:
                items.append(
                    '<div class="sublist">'
                    + '<span class="sep"> · </span>'.join(pending)
                    + "</div>"
                )
                pending.clear()

        for o in outline:
            if o["kind"] != "h3":
                flush()
            if o["kind"] == "part":
                items.append(f'<a class="part" href="#{o["id"]}">{html.escape(o["title"])}</a>')
            elif o["kind"] == "q":
                items.append(
                    f'<a href="#{o["id"]}"><span class="n" style="color:{acc}">{o["badge"]}</span>'
                    f'<span>{html.escape(o["title"])}</span></a>'
                )
            elif o["kind"] == "topic":
                items.append(
                    f'<a href="#{o["id"]}"><span class="n topic" style="color:{acc}">·</span>'
                    f'<span>{html.escape(o["title"])}</span></a>'
                )
            elif show_h3:
                pending.append(
                    f'<a class="sub" href="#{o["id"]}">{html.escape(o["title"])}</a>'
                )
        flush()

        label = f"{qcount} question" + ("" if qcount == 1 else "s")
        if topics:
            label += f" · {topics} topics"
        tocs.append(
            f'<div class="tocgroup">'
            f'<div class="gh"><span class="bar" style="background:{acc}"></span>'
            f'<span class="nm">{html.escape(name)}</span>'
            f'<span class="ds">· {label}</span></div>'
            f'<div class="toclist">{"".join(items)}</div></div>'
        )

    total = sum(m["q"] for m in meta)
    total_code = sum(m["code"] for m in meta)
    total_diag = sum(m["diag"] for m in meta)

    legend_rows = ""
    for m in meta:
        legend_rows += (
            f'<div class="row"><span class="dot" style="background:{m["acc"]}"></span>'
            f'<span class="nm">{html.escape(m["name"])}</span>'
            f'<span class="ds">{html.escape(m["sub"])}</span>'
            f'<span class="ct">{m["q"]} Q</span></div>'
        )

    today = date.today().strftime("%d %B %Y")

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Real Interview Questions</title>
<style>{CSS}</style></head><body>

<div class="cover">
  <div class="eyebrow">DevOps Interview Preparation · Compiled Notes</div>
  <h1>Real Interview<br>Questions</h1>
  <div class="rule"></div>
  <div class="lede">Questions asked in real interviews, with worked answers, commands,
  diagrams and ready-to-speak responses. Compiled from three companies and organised
  so each answer can be read, practised and delivered on its own.</div>
  <div class="stats">
    <div><div class="v">{total}</div><div class="l">Questions</div></div>
    <div><div class="v">{total_code}</div><div class="l">Code samples</div></div>
    <div><div class="v">{total_diag}</div><div class="l">Diagrams</div></div>
  </div>
  <div class="legend">
    <h3>What's inside</h3>
    {legend_rows}
  </div>
  <div class="foot"><span>{total} QUESTIONS · 3 COMPANIES</span><span>{today.upper()}</span></div>
</div>

<div class="toc">
  <h2 class="plain">Contents</h2>
  <p class="sub">Every question in this document, grouped by company.</p>
  {"".join(tocs)}
</div>

{"".join(sections)}

</body></html>"""


def main():
    OUT_DIR.mkdir(exist_ok=True)
    doc = build_html()

    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "doc.html"
        src.write_text(doc, encoding="utf-8")
        cmd = [
            "google-chrome",
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--no-pdf-header-footer",
            "--run-all-compositor-stages-before-draw",
            "--virtual-time-budget=20000",
            f"--print-to-pdf={OUT_PDF}",
            src.as_uri(),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            sys.stderr.write(res.stderr)
            sys.exit(res.returncode)

    size = OUT_PDF.stat().st_size / 1024
    print(f"Wrote {OUT_PDF} ({size:.0f} KB)")


if __name__ == "__main__":
    main()
