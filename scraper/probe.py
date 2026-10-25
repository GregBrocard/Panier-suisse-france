"""Sonde : télécharge les pages de recherche de chaque enseigne et les garde dans debug/.

Sert à (re)caler les parseurs quand un site change sa structure.
Lancement : SCRAPER_DEBUG=1 python -m scraper.probe
"""
from __future__ import annotations

import os
import sys

from .common import Session

Q = os.environ.get("PROBE_QUERY", "nutella")

URLS = {
    # Suisse
    "coop_search": f"https://www.coop.ch/fr/search/?text={Q}",
    "coop_product": "https://www.coop.ch/fr/alimentation/garde-manger/pates-a-tartiner/autres-pates-a-tartiner-sucrees/nutella-pate-a-tartiner/p/7222609",
    "migros_search": f"https://www.migros.ch/fr/search?query={Q}",
    "migros_guest": "https://www.migros.ch/authentication/public/v1/api/guest?authorizationNotRequired=true",
    "lidl_ch_search": f"https://sortiment.lidl.ch/fr/catalogsearch/result/?q={Q}",
    "lidl_ch_product": "https://sortiment.lidl.ch/fr/catalog/product/view/_ignore_category/1/id/11270/s/ferrero-nutella-0003365/",
    "aldi_ch_search": f"https://www.aldi-suisse.ch/fr/rechercher.html?query={Q}",
    "aldi_now_search": f"https://www.aldi-now.ch/fr/search?q={Q}",
    # France - localisation des drives Leclerc
    "leclerc_home": "https://www.leclercdrive.fr/",
    "leclerc_annemasse": "https://www.leclercdrive.fr/region-auvergne-rhone-alpes/annemasse/",
    "leclerc_gex": "https://www.leclercdrive.fr/region-auvergne-rhone-alpes/gex/",
    "leclerc_pontarlier": "https://www.leclercdrive.fr/region-bourgogne-franche-comte/pontarlier/",
    "leclerc_sitemap": "https://www.leclercdrive.fr/sitemap.aspx",
    # Change
    "ecb": "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml",
}


def main(names: list[str]) -> None:
    s = Session(delay=1.0, debug=True)
    for tag, url in URLS.items():
        if names and tag not in names:
            continue
        try:
            r = s.get(url, tag=tag)
            print(f"{tag:22s} {r.status_code} {len(r.text):>8} B  {r.url}")
        except Exception as e:  # noqa: BLE001
            print(f"{tag:22s} ERREUR {e}")
    # PROBE_EXTRA="tag1=https://...;tag2=https://..." pour sonder des URL supplémentaires
    extra = [x.split("=", 1) for x in os.environ.get("PROBE_EXTRA", "").split(";") if "=" in x]
    for tag, url in extra:
        try:
            r = s.get(url, tag=tag)
            print(f"{tag:22s} {r.status_code} {len(r.text):>8} B  {r.url}")
        except Exception as e:  # noqa: BLE001
            print(f"{tag:22s} ERREUR {e}")


if __name__ == "__main__":
    main(sys.argv[1:])
