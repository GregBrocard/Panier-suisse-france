"""Localités de Suisse : répertoire officiel des localités de swisstopo (avec NPA et coordonnées WGS84)."""
from __future__ import annotations

import csv
import io
import re
import statistics
import zipfile

import requests

URL = ("https://data.geo.admin.ch/ch.swisstopo-vd.ortschaftenverzeichnis_plz/"
       "ortschaftenverzeichnis_plz/ortschaftenverzeichnis_plz_4326.csv.zip")


def localites() -> list[dict]:
    """Une entrée par localité : nom, canton, NPA (le plus petit), latitude, longitude (moyenne des points)."""
    r = requests.get(URL, timeout=120)
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    name = [n for n in z.namelist() if n.endswith(".csv")][0]
    rows = csv.DictReader(io.StringIO(z.read(name).decode("utf-8-sig")), delimiter=";")
    acc: dict[tuple, dict] = {}
    for row in rows:
        nom = re.sub(r"\s+\d+$", "", row["Ortschaftsname"]).strip()   # "Lausanne 25" -> "Lausanne"
        key = (nom, row["Kantonskürzel"])
        a = acc.setdefault(key, {"nom": nom, "canton": row["Kantonskürzel"], "npa": [], "lat": [], "lon": []})
        a["npa"].append(row["PLZ4"])
        a["lat"].append(float(row["N"]))
        a["lon"].append(float(row["E"]))
    out = []
    for a in acc.values():
        out.append({"nom": a["nom"], "canton": a["canton"], "npa": min(a["npa"]),
                    "lat": round(statistics.mean(a["lat"]), 4), "lon": round(statistics.mean(a["lon"]), 4)})
    out.sort(key=lambda x: (x["nom"], x["canton"]))
    return out
