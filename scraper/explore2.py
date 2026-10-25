"""Vérifications avant intégration : doublons OFAG, format INSEE, BCE mensuel."""
import requests

from .lindas_explore import q, show, GRAPH

D = "https://agriculture.ld.admin.ch/foag/dimension/"
for label, cube in [("Bananes", "FruitsVegetablesPotatoes"), ("Lait drink UHT", "MilkDairyProducts"),
                    ("Pain mi-blanc , non bio, moyenne", "BreadCerealsFlourBakedGoods")]:
    print("== OFAG", label)
    show(q(f"""PREFIX schema: <http://schema.org/>
SELECT ?d ?price ?mL ?vcL ?vcdL ?srL ?dsL ?pgL WHERE {{ GRAPH <{GRAPH}> {{
 <https://agriculture.ld.admin.ch/foag/cube/{cube}/Consumption_Price_Month> <https://cube.link/observationSet> ?set .
 ?set <https://cube.link/observation> ?obs .
 ?obs <{D}product> ?p ; <{D}date> ?d ; <https://agriculture.ld.admin.ch/foag/measure/price> ?price ;
      <{D}market> ?m ; <{D}value-chain> ?vc ; <{D}value-chain-detail> ?vcd ; <{D}sales-region> ?sr ; <{D}data-source> ?ds ;
      <{D}key-indicator-type> ?k . }}
 ?p schema:name "{label}"@fr .
 ?k schema:name "Prix"@fr .
 OPTIONAL {{ ?m schema:name ?mL FILTER(LANG(?mL)="fr") }} OPTIONAL {{ ?vc schema:name ?vcL FILTER(LANG(?vcL)="fr") }}
 OPTIONAL {{ ?vcd schema:name ?vcdL FILTER(LANG(?vcdL)="fr") }} OPTIONAL {{ ?sr schema:name ?srL FILTER(LANG(?srL)="fr") }}
 OPTIONAL {{ ?ds schema:name ?dsL FILTER(LANG(?dsL)="fr") }}
}} ORDER BY DESC(?d) LIMIT 12"""))

print("== INSEE")
r = requests.get("https://bdm.insee.fr/series/sdmx/data/SERIES_BDM/000641432?lastNObservations=3", timeout=60)
print(r.text[:1500])
print("== BCE mensuel")
r = requests.get("https://data-api.ecb.europa.eu/service/data/EXR/M.CHF.EUR.SP00.A?format=csvdata&lastNObservations=3", timeout=60)
print(r.status_code, r.text[:800])
print("== OFDF T4.4")
r = requests.get("https://www.bazg.admin.ch/fr/statistique-sur-les-huiles-minerales", timeout=60)
print(r.status_code, len(r.text))
import re
print(sorted(set(re.findall(r'href="([^"]*(?:T%204\.4|T 4\.4|Monatstabelle)[^"]*)"', r.text)))[:20])
