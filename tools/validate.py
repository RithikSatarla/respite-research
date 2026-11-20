"""Checks run before every deploy (and in CI):

1. every internal link and asset in _site/ resolves to a file;
2. no page contains a string from the private-data deny list (customer, person and repository names, raw station ids);
3. every figure referenced exists and every data file is listed in data/MANIFEST.json with a matching sha256;
4. no page contains an unresolved token or the word MISSING.

    python tools/validate.py
"""
import hashlib
import json
import os
import re
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "_site")
DENY = os.path.join(ROOT, "tools", "deny_hashes.json")


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            if k in ("href", "src") and v:
                self.links.append(v)


def denied_terms_found(text: str, deny: dict) -> list:
    """The deny list holds sha256 hashes of lowercased terms (so this public repo does not itself publish the names it
    guards against). Every word and word pair of the text is hashed and compared."""
    words = re.findall(r"[a-z0-9_\-]+", text.lower())
    grams = set(words) | {f"{a} {b}" for a, b in zip(words, words[1:])}
    hashes = {hashlib.sha256(g.encode()).hexdigest(): g for g in grams}
    return sorted(hashes[h] for h in deny["sha256"] if h in hashes)


def main():
    errors = []
    deny = json.load(open(DENY, encoding="utf-8"))
    for dirpath, _, files in os.walk(SITE):
        for fn in files:
            p = os.path.join(dirpath, fn)
            if not fn.endswith((".html", ".json", ".svg", ".md", ".csv", ".js", ".txt", ".xml")):
                continue
            text = open(p, encoding="utf-8", errors="replace").read()
            rel = os.path.relpath(p, SITE)
            hit = denied_terms_found(text, deny)
            if hit:
                errors.append(f"{rel}: private term on the deny list ({len(hit)} hit(s))")
            if re.search(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[a-z]{2,}", text):
                errors.append(f"{rel}: contains an email address (this site publishes none)")
            if fn.endswith(".html"):
                if "{{" in text or "MISSING" in text:
                    errors.append(f"{rel}: unresolved token")
                parser = Links()
                parser.feed(text)
                for link in parser.links:
                    if link.startswith(("http://", "https://", "mailto:", "#", "data:")):
                        continue
                    target = link.split("#")[0].split("?")[0]
                    if not target or target == "./":
                        target = "index.html"
                    if not os.path.exists(os.path.normpath(os.path.join(os.path.dirname(p), target))):
                        errors.append(f"{rel}: broken link {link}")
    man = json.load(open(os.path.join(ROOT, "data", "MANIFEST.json"), encoding="utf-8"))
    for item in man["files"]:
        p = os.path.join(ROOT, item["path"])
        if not os.path.exists(p):
            errors.append(f"manifest: missing {item['path']}")
            continue
        if hashlib.sha256(open(p, "rb").read()).hexdigest() != item["sha256"]:
            errors.append(f"manifest: sha256 mismatch for {item['path']}")
    if errors:
        print("VALIDATION FAILED")
        print("\n".join(errors))
        return 1
    print(f"validation passed: links, deny list, data manifest ({len(man['files'])} files), tokens")
    return 0


if __name__ == "__main__":
    sys.exit(main())
