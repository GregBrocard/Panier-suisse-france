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


if __name__ == "__main__":
    print("== cubes Consumption_Price_Month")
    show(q(f"""SELECT DISTINCT ?cube WHERE {{ GRAPH <{GRAPH}> {{ ?cube a <https://cube.link/Cube> }}
             FILTER(CONTAINS(STR(?cube),"Consumption_Price")) }}"""), 80)
    cube = sys.argv[1] if len(sys.argv) > 1 else "https://agriculture.ld.admin.ch/foag/cube/Eggs/Consumption_Price_Month"
    print("== prédicats d'une observation de", cube)
    show(q(f"""SELECT ?p ?o WHERE {{ GRAPH <{GRAPH}> {{
             <{cube}> <https://cube.link/observationSet> ?set . ?set <https://cube.link/observation> ?obs .
             ?obs ?p ?o }} }} LIMIT 40"""))
