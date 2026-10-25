"""Assemble le site : injecte data/latest.json et data/series.json dans site/template.html.

Sortie : site/index.html (page autonome, une seule requête externe : Chart.js et les polices).
"""
from __future__ import annotations

import json

from .common import ROOT


def main():
    latest = json.loads((ROOT / "data/latest.json").read_text(encoding="utf-8"))
    series = json.loads((ROOT / "data/series.json").read_text(encoding="utf-8"))
    latest.pop("journal", None)
    for z in (latest.get("carburant", {}).get("zones") or {}).values():
        if z:
            z.pop("stations", None)
    latest.get("carburant", {}).pop("historique_fr", None)
    payload = json.dumps({"latest": latest, "series": series}, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("</", "<\\/")
    tpl = (ROOT / "site/template.html").read_text(encoding="utf-8")
    out = tpl.replace("/*__DATA__*/", payload)
    (ROOT / "site/index.html").write_text(out, encoding="utf-8")
    print(f"site/index.html : {len(out) / 1024:.0f} Ko")


if __name__ == "__main__":
    main()
