"""Exploration des cubes OFAG (prix à la consommation) sur LINDAS (SPARQL)."""
from __future__ import annotations

import json
import sys

import requests

ENDPOINTS = ["https://lindas.admin.ch/query", "https://lindas.cz-aws.net/query"]
GRAPH = "https://lindas.admin.ch/foag/agricultural-market-data"


def q(sparql: str) -> list[dict]:
    last = None
    for ep in ENDPOINTS:
        try:
            r = requests.post(ep, data={"query": sparql},
                              headers={"Accept": "application/sparql-results+json"}, timeout=90)
            r.raise_for_status()
            return r.json()["results"]["bindings"]
        except Exception as e:  # noqa: BLE001
            last = e
    raise RuntimeError(last)


def show(rows, n=60):
    for b in rows[:n]:
        print("   ", {k: v["value"][:110] for k, v in b.items()})


if __name__ == "__main__" and (len(sys.argv) < 2 or sys.argv[1] != "catalog"):
    print("== cubes Consumption_Price_Month")
    show(q(f"""SELECT DISTINCT ?cube WHERE {{ GRAPH <{GRAPH}> {{ ?cube a <https://cube.link/Cube> }}
             FILTER(CONTAINS(STR(?cube),"Consumption_Price")) }}"""), 80)
    cube = sys.argv[1] if len(sys.argv) > 1 else "https://agriculture.ld.admin.ch/foag/cube/Eggs/Consumption_Price_Month"
    print("== prédicats d'une observation de", cube)
    show(q(f"""SELECT ?p ?o WHERE {{ GRAPH <{GRAPH}> {{
             <{cube}> <https://cube.link/observationSet> ?set . ?set <https://cube.link/observation> ?obs .
             ?obs ?p ?o }} }} LIMIT 40"""))


def catalog(cube: str):
    D = "https://agriculture.ld.admin.ch/foag/dimension/"
    rows = q(f"""PREFIX schema: <http://schema.org/>
SELECT ?prodL ?unitL ?kitL ?psL ?propL ?origL (MAX(?d) AS ?last) (COUNT(?obs) AS ?n) (MIN(?d) AS ?first) WHERE {{ GRAPH <{GRAPH}> {{
  <{cube}> <https://cube.link/observationSet> ?set . ?set <https://cube.link/observation> ?obs .
  ?obs <{D}product> ?p ; <{D}unit> ?u ; <{D}key-indicator-type> ?k ; <{D}production-system> ?ps ;
       <{D}product-properties> ?pp ; <{D}product-origin> ?po ; <{D}date> ?d . }}
  OPTIONAL {{ ?p schema:name ?prodL FILTER(LANG(?prodL)="fr") }}
  OPTIONAL {{ ?u schema:name ?unitL FILTER(LANG(?unitL)="fr") }}
  OPTIONAL {{ ?k schema:name ?kitL FILTER(LANG(?kitL)="fr") }}
  OPTIONAL {{ ?ps schema:name ?psL FILTER(LANG(?psL)="fr") }}
  OPTIONAL {{ ?pp schema:name ?propL FILTER(LANG(?propL)="fr") }}
  OPTIONAL {{ ?po schema:name ?origL FILTER(LANG(?origL)="fr") }}
}} GROUP BY ?prodL ?unitL ?kitL ?psL ?propL ?origL ORDER BY ?prodL""")
    print("==", cube.split("/cube/")[1], len(rows))
    show(rows, 400)


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "catalog":
    for c in ["Eggs", "MilkDairyProducts", "BreadCerealsFlourBakedGoods", "Oilseeds", "FruitsVegetablesPotatoes"]:
        try:
            catalog(f"https://agriculture.ld.admin.ch/foag/cube/{c}/Consumption_Price_Month")
        except Exception as e:  # noqa: BLE001
            print("ERR", c, e)
