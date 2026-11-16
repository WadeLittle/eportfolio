#!/usr/bin/env python3
"""Builds the GLD ePortfolio site from the Word documents in the parent folder.

Edit your essays in Word, then run:  python3 build.py
Essay text is copied word-for-word; only layout is added here.
Artifacts are configured in artifacts.json.
"""
import html, json, re, subprocess, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

# Sentences removed from the published text (drafting notes, not essay content).
STRIP = [
    r"Could I do a survey of Columbia business owners[^?]*\?\s*Cost, unskilled etc\.?",
]

INSIGHTS = [
    {"n": 1, "doc": "Key Insight 1.docx", "slug": "insight-1",
     "title": "Abstraction and reusability are the keys to a consumer’s heart",
     "wtc": "CSCE 145 & 146: Algorithmic Design I & II", "btc": "Software engineering internship, Deutsche Bank",
     "wtc_short": "CSCE 145/146", "btc_short": "Deutsche Bank",
     "concept": "Object-oriented programming: abstraction & reusability"},
    {"n": 2, "doc": "Key Insight 2.docx", "slug": "insight-2",
     "title": "Everything is a process, and you’re always selling",
     "wtc": "MKTG 457: Introduction to Sales", "btc": "Director of Employer Outreach, CSIET",
     "wtc_short": "MKTG 457", "btc_short": "CSIET",
     "concept": "The C.A.S.H.U. sales process & roleplay"},
    {"n": 3, "doc": "Key Insight 3.docx", "slug": "insight-3",
     "title": "Practice creates competence, and competence creates confidence",
     "wtc": "CSCE 201: Introduction to Computer Security", "btc": "NSF REU, University of Alabama",
     "wtc_short": "CSCE 201", "btc_short": "NSF REU",
     "concept": "Cryptographic primitives & sealed-bid auctions"},
]

NAV = [("index.html", "About Me"), ("insight-1.html", "Key Insight 1"), ("insight-2.html", "Key Insight 2"),
       ("insight-3.html", "Key Insight 3"), ("leadership.html", "Leadership"), ("artifacts.html", "Artifacts")]


def esc(s):
    return html.escape(s, quote=False)


def run_html(r):
    out = []
    for el in r:
        if el.tag == W + "t":
            out.append(esc(el.text or ""))
        elif el.tag == W + "tab":
            out.append(" ")
        elif el.tag == W + "br":
            out.append("<br>")
    text = "".join(out)
    rpr = r.find(W + "rPr")
    if text.strip() and rpr is not None:
        b = rpr.find(W + "b")
        if b is not None and b.get(W + "val") not in ("0", "false"):
            text = f"<strong>{text}</strong>"
        i = rpr.find(W + "i")
        if i is not None and i.get(W + "val") not in ("0", "false"):
            text = f"<em>{text}</em>"
    return text


def para(p):
    s = "".join(run_html(r) for r in p.iter(W + "r"))
    s = s.replace("</strong><strong>", "").replace("</em><em>", "")
    for x in STRIP:
        s = re.sub(x, " ", s)
    s = re.sub(r"[ \u00a0]{2,}", " ", s).strip()
    ppr = p.find(W + "pPr")
    style = ""
    is_list = False
    if ppr is not None:
        ps = ppr.find(W + "pStyle")
        style = ps.get(W + "val") if ps is not None else ""
        is_list = ppr.find(W + "numPr") is not None or "List" in style
    return style, is_list, s


def doc_blocks(path):
    """Return list of (kind, html) blocks: title, h2, p, li, table."""
    import xml.etree.ElementTree as ET
    root = ET.fromstring(zipfile.ZipFile(path).read("word/document.xml"))
    body = root.find(W + "body")
    blocks = []
    for el in body:
        if el.tag == W + "p":
            style, is_list, s = para(el)
            if not s:
                continue
            if style == "Title":
                blocks.append(("title", s))
            elif style.startswith("Heading"):
                blocks.append(("h2", re.sub(r"</?strong>", "", s)))
            elif is_list:
                blocks.append(("li", s))
            else:
                blocks.append(("p", s))
        elif el.tag == W + "tbl":
            rows = []
            for tr in el.iter(W + "tr"):
                cells = []
                for tc in tr.iter(W + "tc"):
                    cells.append("<br>".join(t for _, _, t in (para(p) for p in tc.iter(W + "p")) if t))
                rows.append(cells)
            head, *rest = rows
            t = "<div class=\"table-wrap\"><table><thead><tr>" + "".join("<th>" + re.sub(r'</?strong>', '', c) + "</th>" for c in head) + "</tr></thead><tbody>"
            for r in rest:
                t += "<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>"
            blocks.append(("table", t + "</tbody></table></div>"))
    return blocks


def render_blocks(blocks):
    out, in_list = [], False
    for kind, s in blocks:
        if kind == "li" and not in_list:
            out.append("<ul>"); in_list = True
        if kind != "li" and in_list:
            out.append("</ul>"); in_list = False
        if kind == "li":
            out.append(f"<li>{s}</li>")
        elif kind == "h2":
            out.append('<h2 id="' + re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-') + f'">{s}</h2>')
        elif kind == "p":
            out.append(f"<p>{s}</p>")
        elif kind == "table":
            out.append(s)
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


def page(filename, title, body, desc="Graduation with Leadership Distinction ePortfolio of Wade Little, Research pathway, University of South Carolina."):
    cur = ' aria-current="page"'
    nav = "".join(
        f'<a href="{h}"{cur if h == filename else ""}>{esc(t)}</a>' for h, t in NAV)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · Wade Little ePortfolio</title>
<meta name="description" content="{esc(desc)}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 64 64%27%3E%3Ccircle cx=%2732%27 cy=%2732%27 r=%2732%27 fill=%27%2373000a%27/%3E%3Ctext x=%2732%27 y=%2741%27 font-family=%27Georgia%27 font-size=%2726%27 font-weight=%27700%27 fill=%27white%27 text-anchor=%27middle%27%3EWL%3C/text%3E%3C/svg%3E">
<link rel="stylesheet" href="style.css">
<script src="viewer.js" defer></script>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-header">
  <div class="bar">
    <a class="brand" href="index.html"><span class="mark">WL</span><span>Wade Little<small>GLD ePortfolio · Research</small></span></a>
    <button class="menu" aria-expanded="false" aria-controls="nav" onclick="const n=document.getElementById('nav');const o=n.classList.toggle('open');this.setAttribute('aria-expanded',o)">Menu</button>
    <nav id="nav">{nav}</nav>
  </div>
</header>
<main id="main">
{body}
</main>
<footer class="site-footer">
  <p>Wade Little · Computer Information Systems, University of South Carolina, Class of 2027</p>
  <p>Graduation with Leadership Distinction in Research</p>
</footer>
</body>
</html>
"""


def pdf_pages(a):
    """Render a PDF artifact to page images (cached) so it can be viewed in the page."""
    f = a.get("file") or ""
    if not f.lower().endswith(".pdf"):
        return []
    pdf = HERE / f
    out = HERE / "assets" / "artifacts" / "pages" / a["id"]
    stamp = out / ".source"
    sig = f"{pdf.stat().st_size}-{int(pdf.stat().st_mtime)}"
    if not (stamp.exists() and stamp.read_text() == sig):
        if out.exists():
            for old in out.glob("*.jpg"):
                old.unlink()
        out.mkdir(parents=True, exist_ok=True)
        subprocess.run(["pdftoppm", "-jpeg", "-jpegopt", "quality=80", "-scale-to", "1600", str(pdf), str(out / "p")], check=True)
        stamp.write_text(sig)
    return [str(p.relative_to(HERE)) for p in sorted(out.glob("p-*.jpg"))]


def gallery(a):
    pages = pdf_pages(a)
    if a.get("image") and (a.get("gallery_includes_image") or not pages):
        pages = [a["image"]] + pages
    return list(a.get("images") or []) + pages


def viewer(a, pages):
    data = esc(json.dumps(pages)).replace('"', "&quot;")
    label = esc(a.get("alt", a["title"]))
    n = len(pages)
    return f"""<div class="viewer" data-pages="{data}" data-title="{esc(a['title'])}">
  <button class="v-stage" type="button" aria-label="Open {label} full screen"><img src="{esc(pages[0])}" alt="{label}" loading="lazy"></button>
  <div class="v-bar"{' hidden' if n < 2 else ''}>
    <button class="v-prev" type="button" aria-label="Previous page">‹</button>
    <span class="v-count">1 / {n}</span>
    <button class="v-next" type="button" aria-label="Next page">›</button>
  </div>
  <button class="v-full" type="button" aria-label="Full screen">⤢ Full screen</button>
</div>"""


def artifact_card(a, compact=False):
    kind = "Within the classroom" if a["type"] == "WTC" else "Beyond the classroom"
    pages = gallery(a)
    link, file = a.get("link"), a.get("file")
    quote = a.get("quote")
    pending = not (link or file or pages or quote)
    links = []
    if link:
        links.append(f'<a class="art-link" href="{esc(link)}" target="_blank" rel="noopener">{esc(a.get("link_label", "Open link"))} ↗</a>')
    if file:
        links.append(f'<a class="art-link subtle" href="{esc(file)}" target="_blank" rel="noopener">Open PDF ↗</a>')
    if pending:
        links.append('<span class="art-link pending">Artifact file not added yet</span>')
    desc = a.get("description") or ""
    body = f'<p class="art-desc">{esc(desc)}</p>' if desc else ''
    look = f'<p class="art-look"><strong>Look at:</strong> {esc(a["look_at"])}</p>' if a.get("look_at") else ""
    meta = f'<p class="art-meta">{esc(a["meta"])}</p>' if a.get("meta") else ""
    if quote:
        paras = "".join(f"<p>{esc(q)}</p>" for q in quote)
        if compact:
            paras = f"<p>{esc(quote[0])}</p>"
        media = f'<blockquote class="art-quote">{paras}<footer>{esc(a.get("quote_by", ""))}</footer></blockquote>'
    elif pages:
        media = viewer(a, pages)
    else:
        media = '<div class="viewer empty"><span>Artifact coming soon</span></div>'
    cls = f"artifact {a['type'].lower()}{' is-pending' if pending else ''}{' compact' if compact else ' feature'}"
    return f"""<article class="{cls}" id="{esc(a['id'])}">
  {media}
  <div class="art-body">
    <p class="art-kind">{kind} · {esc(a['type'])}</p>
    <h3>{esc(a['title'])}</h3>
    {meta}
    {'' if compact else body + look}
    <div class="art-links">{''.join(links)}</div>
  </div>
</article>"""


def build():
    artifacts = json.loads((HERE / "artifacts.json").read_text())
    # Only publish artifacts that have something to show; empty slots stay in artifacts.json for later.
    artifacts = [a for a in artifacts if any(a.get(k) for k in ("link", "file", "image", "images", "quote"))]

    # About Me
    about = doc_blocks(SRC / "About Me.docx")
    paras = [b for b in about if b[0] != "li"]
    intro_end = next(i for i, b in enumerate(about) if re.sub(r"<[^>]+>", "", b[1]).startswith("My key insights"))
    intro_html = render_blocks(about[:intro_end])
    closing_html = render_blocks([b for b in about[intro_end + 1:] if b[0] != "li"])
    bullets = [re.sub(r"<[^>]+>", "", b[1]).strip() for b in about if b[0] == "li"]
    cards = ""
    for ki, text in zip(INSIGHTS, bullets):
        # The bullet opens with the insight statement; the card shows the rest of the bullet verbatim.
        lead = ki["title"].rstrip(".") + "."
        rest = text[len(lead):].strip() if text.startswith(lead) else text
        cards += f"""<a class="ki-card" href="{ki['slug']}.html">
  <span class="ki-num">{ki['n']:02d}</span>
  <h3>{esc(lead)}</h3>
  <p>{esc(rest)}</p>
  <ul class="ki-tags"><li class="wtc">{esc(ki['wtc_short'])}</li><li class="btc">{esc(ki['btc_short'])}</li></ul>
  <span class="ki-go">Read Key Insight {ki['n']} →</span>
</a>"""
    lb_title = next((s for k, s in doc_blocks(SRC / "Leadership-section.docx") if k == "title"), "Leadership").replace("Leadership: ", "")
    body = f"""<section class="hero">
  <div class="hero-text">
    <p class="eyebrow">Graduation with Leadership Distinction · Research Pathway</p>
    <h1>Technology should fit the business, not the other way around.</h1>
    <dl class="facts">
      <div><dt>Pathway</dt><dd>Research</dd></div>
      <div><dt>Major</dt><dd>Computer Information Systems</dd></div>
      <div><dt>Graduating</dt><dd>May 2027</dd></div>
      <div><dt>Hometown</dt><dd>Raleigh, NC</dd></div>
    </dl>
  </div>
  <figure class="headshot">
    <img src="assets/headshot.jpg" alt="Portrait of Wade Little" onerror="this.replaceWith(Object.assign(document.createElement('div'),{{className:'headshot-ph',textContent:'WL'}}))">
  </figure>
</section>
<section class="prose about">
<h2>About Me</h2>
{intro_html}
</section>
<section class="band">
  <div class="band-inner">
    <h2 class="section-title">My Key Insights</h2>
    <div class="ki-grid">{cards}</div>
  </div>
</section>
<section class="lead-teaser">
  <p class="eyebrow">Leadership</p>
  <h2>{esc(lb_title)}</h2>
  <div class="prose-in">{closing_html}</div>
  <p class="next"><a class="button" href="leadership.html">Read my Leadership plan →</a></p>
</section>"""
    (HERE / "index.html").write_text(page("index.html", "About Me", body))

    # Key insights
    for ki in INSIGHTS:
        blocks = doc_blocks(SRC / ki["doc"])
        mine = [a for a in artifacts if a["insight"] == ki["n"]]
        arts = "\n".join(artifact_card(a) for a in mine)
        listing = "".join(f'<li><a href="#{esc(a["id"])}">{esc(a["title"])}</a> <span class="tag {a["type"].lower()}">{a["type"]}</span></li>' for a in mine)
        prev_next = []
        if ki["n"] > 1:
            prev_next.append(f'<a href="insight-{ki["n"]-1}.html">← Key Insight {ki["n"]-1}</a>')
        else:
            prev_next.append('<a href="index.html">← About Me</a>')
        if ki["n"] < 3:
            prev_next.append(f'<a href="insight-{ki["n"]+1}.html">Key Insight {ki["n"]+1} →</a>')
        else:
            prev_next.append('<a href="leadership.html">Leadership →</a>')
        body = f"""<header class="page-head">
  <p class="eyebrow">Key Insight {ki['n']} of 3</p>
  <h1>{ki['title']}</h1>
  <dl class="meta">
    <div><dt>Within the classroom</dt><dd>{esc(ki['wtc'])}</dd></div>
    <div><dt>Beyond the classroom</dt><dd>{esc(ki['btc'])}</dd></div>
    <div><dt>Concept</dt><dd>{esc(ki['concept'])}</dd></div>
  </dl>
</header>
<article class="prose essay">
{render_blocks(blocks)}
</article>
<section class="wide artifacts-section" aria-labelledby="arts-{ki['n']}">
  <h2 class="section-title" id="arts-{ki['n']}">Artifacts for Key Insight {ki['n']}</h2>
  <div class="art-feature-list">{arts}</div>
  <nav class="art-index" aria-label="Artifact list"><h3>Artifact list</h3><ol>{listing}</ol></nav>
</section>
<nav class="pager">{''.join(prev_next)}</nav>"""
        (HERE / f"{ki['slug']}.html").write_text(page(f"{ki['slug']}.html", f"Key Insight {ki['n']}", body))

    # Leadership
    lb = doc_blocks(SRC / "Leadership-section.docx")
    title = next((s for k, s in lb if k == "title"), "Leadership")
    rest = [b for b in lb if b[0] != "title"]
    ref_i = next((i for i, b in enumerate(rest) if b[0] == "h2" and b[1].lower() == "references"), len(rest))
    main_html = render_blocks(rest[:ref_i])
    # Visual emphasis only (text unchanged): SMART goal callout and a step timeline.
    main_html = main_html.replace("<p><strong>SMART Goal:", '<p class="callout"><strong>SMART Goal:')
    main_html = re.sub(r"<p><strong>(Step \d+:)", r'<p class="step"><strong>\1', main_html)
    main_html = re.sub(r'(<p class="step">.*?</p>\n?)+', lambda m: f'<div class="timeline">{m.group(0)}</div>', main_html, flags=re.S)
    toc = "".join(f'<a href="#{i}">{t}</a>' for i, t in re.findall(r'<h2 id="([^"]+)">([^<]+)</h2>', main_html))
    link_re = r'<a href="\1" target="_blank" rel="noopener">\1</a>'
    refs = "".join("<li>" + re.sub(r"(https?://[^\s<]+)", link_re, s) + "</li>"
                   for k, s in rest[ref_i + 1:])
    body = f"""<header class="page-head">
  <p class="eyebrow">Leadership</p>
  <h1>{title.replace('Leadership: ', '')}</h1>
  <nav class="toc" aria-label="On this page">{toc}<a href="#references">References</a></nav>
</header>
<article class="prose essay leadership">
{main_html}
<h2 id="references">References</h2>
<ul class="refs">{refs}</ul>
</article>
<nav class="pager"><a href="insight-3.html">← Key Insight 3</a><a href="artifacts.html">All artifacts →</a></nav>"""
    (HERE / "leadership.html").write_text(page("leadership.html", "Leadership", body))

    # All artifacts
    groups = ""
    for ki in INSIGHTS:
        mine = [a for a in artifacts if a["insight"] == ki["n"]]
        groups += f"""<section class="art-group">
  <h2><a href="{ki['slug']}.html#arts-{ki['n']}">Key Insight {ki['n']}</a>: {ki['title']}</h2>
  <div class="art-grid">{''.join(artifact_card(a, compact=True) for a in mine)}</div>
</section>"""
    body = f"""<header class="page-head">
  <p class="eyebrow">Artifacts</p>
  <h1>Evidence from within and beyond the classroom</h1>
  <p class="legend"><span class="tag wtc">WTC</span> Within the classroom <span class="tag btc">BTC</span> Beyond the classroom</p>
</header>
<div class="wide">{groups}</div>"""
    (HERE / "artifacts.html").write_text(page("artifacts.html", "Artifacts", body))
    print("Built", len(INSIGHTS) + 3, "pages")


if __name__ == "__main__":
    build()
