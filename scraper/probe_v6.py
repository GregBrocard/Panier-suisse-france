"""Sonde v6 : identifiants INSEE des indices harmonisés base 2025 (crèmerie), par balayage autour de 011812307."""
import re
import time
import requests
UA = {"User-Agent": "panier-suisse-france/2.0 (https://github.com/GregBrocard/Panier-suisse-france)"}
start, end = 11811800, 11813200
for a in range(start, end, 60):
    ids = "+".join(f"{i:09d}" for i in range(a, a + 60))
    try:
        r = requests.get(f"https://bdm.insee.fr/series/sdmx/data/SERIES_BDM/{ids}", params={"firstNObservations": 1},
                         headers=UA, timeout=120)
    except Exception as e:  # noqa: BLE001
        print("ERR", a, e); continue
    for m in re.finditer(r'<Series ([^>]+)>\s*<Obs ([^>]+)/>', r.text):
        at = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        o = dict(re.findall(r'(\w+)="([^"]*)"', m.group(2)))
        t = at.get("TITLE_FR", "")
        if re.search(r"Lait|Beurre|Fromage|Yaourt|Huile|Œufs|Oeufs|œufs|01\.1\.4 |01\.1\.5 ", t) and at.get("FREQ") == "M":
            print(f"{at.get('IDBANK')} | {t[:170]} | début {o.get('TIME_PERIOD')}")
    time.sleep(1)
