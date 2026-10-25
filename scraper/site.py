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
    tpl = (ROOT / "site/template.html").read_text(encoding="utf-8")

    def render(data, name):
        payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        out = tpl.replace("/*__DATA__*/", payload)
        (ROOT / "site" / name).write_text(out, encoding="utf-8")
        print(f"site/{name} : {len(out) / 1024:.0f} Ko")

    # version complète (usage privé)
    render({"latest": latest, "series": series}, "index.html")
    # version publique : sans les données Que Choisir tant que leur accord n'est pas obtenu
    pub = dict(latest)
    if not (latest.get("magasins") or {}).get("publier"):
        pub["magasins"] = None
    render({"latest": pub, "series": series}, "public.html")


if __name__ == "__main__":
    main()
