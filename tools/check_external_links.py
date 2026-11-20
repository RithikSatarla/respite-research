"""Check that every external link in _site/ answers (HEAD, then GET), with a short timeout. Prints and fails on errors."""
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "_site")
SKIP = ("https://rithiksatarla.github.io/respite-research",)        # this site itself: checked by tools/validate.py


def main():
    urls = set()
    for dirpath, _, files in os.walk(SITE):
        for fn in files:
            if fn.endswith(".html"):
                urls |= set(re.findall(r'href="(https?://[^"#]+)', open(os.path.join(dirpath, fn), encoding="utf-8").read()))
    bad = []
    for u in sorted(urls):
        if u.startswith(SKIP):
            continue
        ok = False
        for method in ("HEAD", "GET"):
            try:
                req = urllib.request.Request(u, method=method, headers={"User-Agent": "respite-research-linkcheck"})
                with urllib.request.urlopen(req, timeout=20) as r:
                    ok = r.status < 400
                    if ok:
                        break
            except Exception as e:
                last = f"{type(e).__name__}: {e}"
        if not ok:
            bad.append(f"{u}  ({last})")
    print(f"checked {len(urls)} external links")
    if bad:
        print("BROKEN:\n" + "\n".join(bad))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
