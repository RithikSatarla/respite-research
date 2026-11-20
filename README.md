# Respite research

The public write-up, benchmark and demo for "Respite: Detecting Recording-Station Failures in Robot Training Data",
served with GitHub Pages at https://rithiksatarla.github.io/respite-research/.

- `src/` page sources. Every number is a token (`{{ path | format }}`) resolved from `data/results.json` at build time;
  a token that does not resolve stops the build.
- `data/` the exported results bundle (numbers, test-set tables, demo records) and `MANIFEST.json` with the SHA-256 of
  every data file and figure, plus the commit of Respite's repository they were exported from.
- `build.py` builds `_site/`; it also writes `_site/data/claims.json` (every number shown, with the stored file it came
  from), the report as Markdown and the model card.
- `tools/validate.py` checks links, figures, the data manifest, unresolved tokens, email addresses and a hashed
  deny list of private names; `tools/check_external_links.py` checks outside links. CI runs both before deploying.

Build locally: `pip install -r requirements.txt && python build.py && python tools/validate.py`.

The benchmark code lives in Respite's repository (private today). The test dataset is XDOF ABC-130k (Apache-2.0);
the development dataset is one robotics team's recordings and is not redistributed here.
