"""Build the static site into _site/ from src/*.html and data/results.json.

    python build.py

Every number on a page is a token {{ path.to.value | format }} resolved from data/results.json, which is exported
from the benchmark's stored result files. A token that does not resolve stops the build. Formats: pct0, pct1, f0,
f1, f2, int, raw, ci_pct0 (a [low, high] pair as a percentage range), ci_f1.
"""
import hashlib
import html
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "_site")
TOKEN = re.compile(r"\{\{\s*([A-Za-z0-9_.\-\[\]]+)\s*(?:\|\s*([a-z_0-9]+))?\s*\}\}")
PAGES = ["index", "benchmark", "demo", "method", "reproduce", "limitations", "report", "contact"]
NAV = [("index", "Overview"), ("benchmark", "Benchmark"), ("demo", "Demo"), ("method", "Method"),
       ("reproduce", "Reproduce"), ("limitations", "Limitations"), ("report", "Report"), ("contact", "Contact")]
BASE_URL = "https://rithiksatarla.github.io/respite-research/"


def lookup(data, path: str):
    cur = data
    for part in path.split("."):
        if isinstance(cur, list):
            cur = cur[int(part)]
        elif isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            raise KeyError(path)
    return cur


def fmt(v, f):
    if f in (None, "raw"):
        return html.escape(str(v))
    if f == "int":
        return f"{int(round(float(v))):,}"
    if f.startswith("pct"):
        return f"{100 * float(v):.{int(f[3:])}f}%"
    if f.startswith("f"):
        return f"{float(v):,.{int(f[1:])}f}"
    if f == "yesno":
        return "yes" if v else "no"
    if f.startswith("ci_pp"):
        lo, hi = v
        d = int(f[5:])
        return f"{100 * float(lo):+.{d}f} to {100 * float(hi):+.{d}f} points"
    if f.startswith("pp"):
        return f"{100 * float(v):+.{int(f[2:])}f} points"
    if f.startswith("ci_pct"):
        lo, hi = v
        d = int(f[6:])
        return f"{100 * float(lo):.{d}f}&ndash;{100 * float(hi):.{d}f}%"
    if f.startswith("ci_f"):
        lo, hi = v
        d = int(f[4:])
        return f"{float(lo):.{d}f}&ndash;{float(hi):.{d}f}"
    raise ValueError(f"unknown format {f}")


SOURCES = [  # results.json prefix -> stored file in Respite's repository it was exported from
    ("test.by_fault", "experiments/results/test/by_fault.csv"), ("test.ablations", "experiments/results/test/ablations.csv"),
    ("test.failure", "experiments/results/test/failure_analysis.json"),
    ("test.unmodified_alerts", "experiments/results/test/control_alerts_adjudication.json"),
    ("test", "experiments/results/test/summary.json"), ("decision", "experiments/results/test/decision.json"),
    ("training", "experiments/results/thresholds.json"), ("retrospective", "experiments/results/retrospective/summary.json"),
    ("hflow", "experiments/results/hflow/summary.json"), ("dev_reference", "experiments/results/dev_101/summary.json"),
    ("data", "experiments/splits/split_v1.json and experiments/results/test/summary.json"), ("meta", "export_site.py run"),
    ("model_versions", "experiments/results/model_version_check/*.json (experiments/check_model_versions.py)"),
]
CLAIMS = []


def source_of(path: str) -> str:
    return next(src for pre, src in SOURCES if path == pre or path.startswith(pre + "."))


LOOP = re.compile(r"\{%\s*for\s+(\w+)\s+in\s+([A-Za-z0-9_.]+)\s*%\}(.*?)\{%\s*endfor\s*%\}", re.S)


def expand_loops(text: str, data: dict) -> str:
    """{% for x in path %}...{{ x.field }}...{% endfor %}: each item's tokens become ordinary paths (path.i.field)."""
    def sub(m):
        var, path, inner = m.group(1), m.group(2), m.group(3)
        items = lookup(data, path)
        return "".join(re.sub(r"\{\{\s*" + var + r"\.", "{{ " + f"{path}.{i}.", inner) for i in range(len(items)))
    return LOOP.sub(sub, text)


def render(text: str, data: dict, page: str) -> str:
    text = expand_loops(text, data)
    missing = []

    def sub(m):
        try:
            val = fmt(lookup(data, m.group(1)), m.group(2))
            CLAIMS.append(dict(page=page, token=m.group(1), format=m.group(2) or "raw", shown=html.unescape(val), source=source_of(m.group(1))))
            return val
        except (KeyError, IndexError, TypeError, ValueError) as e:
            missing.append(f"{page}: {m.group(0)} ({type(e).__name__})")
            return "MISSING"
    out = TOKEN.sub(sub, text)
    if missing:
        raise SystemExit("unresolved tokens:\n  " + "\n  ".join(missing))
    return out


def shell(page: str, title: str, desc: str, body: str, bundle_hash: str) -> str:
    links = []
    for p, t in NAV:
        href = "./" if p == "index" else f"{p}.html"
        current = ' aria-current="page"' if p == page else ""
        links.append(f'<a href="{href}"{current}>{t}</a>')
    nav = "".join(links)
    canonical = BASE_URL + ("" if page == "index" else f"{page}.html")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="canonical" href="{canonical}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:type" content="article">
<meta property="og:url" content="{canonical}">
<meta name="twitter:card" content="summary">
<link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="assets/site.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="top">
  <div class="wrap top-inner">
    <a class="brand" href="./"><span class="mark" aria-hidden="true"></span>Respite research</a>
    <nav aria-label="Pages">{nav}</nav>
  </div>
</header>
<main id="main" class="wrap">
{body}
</main>
<footer class="foot">
  <div class="wrap foot-inner">
    <p>Respite Labs. Every number on this site is generated from stored benchmark outputs; results bundle sha256 <code>{bundle_hash[:16]}</code>.</p>
    <p><a href="https://respitelabs.net">respitelabs.net</a> · <a href="reproduce.html">How to reproduce</a> · <a href="limitations.html">Limitations</a></p>
  </div>
</footer>
</body>
</html>
"""


def main():
    data_path = os.path.join(ROOT, "data", "results.json")
    data = json.load(open(data_path, encoding="utf-8"))
    bundle_hash = hashlib.sha256(open(data_path, "rb").read()).hexdigest()
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    for d in ("assets", "figures", "data"):
        shutil.copytree(os.path.join(ROOT, d), os.path.join(OUT, d))
    meta = json.load(open(os.path.join(ROOT, "src", "pages.json"), encoding="utf-8"))
    for page in PAGES:
        if page == "report":
            import markdown
            md_text = render(open(os.path.join(ROOT, "src", "report.md"), encoding="utf-8").read(), data, page)
            with open(os.path.join(OUT, "data", "REPORT.md"), "w", encoding="utf-8", newline="\n") as f:
                f.write(md_text)
            body = ('<article class="prose report">' + markdown.markdown(md_text, extensions=["tables", "toc", "fenced_code"]) +
                    '<p><a href="data/REPORT.md">This report as Markdown</a></p></article>')
            body = body.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
        else:
            src = open(os.path.join(ROOT, "src", f"{page}.html"), encoding="utf-8").read()
            body = render(src, data, page)
        title, desc = meta[page]["title"], meta[page]["description"]
        name = "index.html" if page == "index" else f"{page}.html"
        with open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n") as f:
            f.write(shell(page, title, desc, body, bundle_hash))
    with open(os.path.join(OUT, "404.html"), "w", encoding="utf-8") as f:
        f.write(shell("404", "Not found | Respite research", "Page not found",
                      '<section class="hero"><h1>Page not found</h1><p><a href="./">Back to the overview</a></p></section>', bundle_hash))
    mc = render(open(os.path.join(ROOT, "src", "model_card.md"), encoding="utf-8").read(), data, "model_card")
    with open(os.path.join(OUT, "data", "MODEL_CARD.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(mc)
    with open(os.path.join(OUT, "data", "claims.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(dict(note="Every number shown on this site: the page, the value shown, the results.json path and the stored file it was exported from.",
                       bundle_sha256=bundle_hash, numbers=CLAIMS), f, indent=1)
    with open(os.path.join(OUT, ".nojekyll"), "w") as f:
        f.write("")
    sm = "".join(f"<url><loc>{BASE_URL}{'' if p == 'index' else p + '.html'}</loc></url>" for p in PAGES)
    with open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>')
    with open(os.path.join(OUT, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}sitemap.xml\n")
    print(f"built {len(PAGES)} pages into {OUT}")


if __name__ == "__main__":
    sys.exit(main())
