"""Sonde v5 : identifiants INSEE (IPC base 2025) des postes lait, beurre, fromages, yaourts, huiles."""
import re
import requests
UA = {"User-Agent": "panier-suisse-france/2.0 (https://github.com/GregBrocard/Panier-suisse-france)"}
for flow in ["IPC-2025", "IPC-2015"]:
    r = requests.get(f"https://bdm.insee.fr/series/sdmx/datastructure/FR1/{flow}", params={"references": "children"},
                     headers=UA, timeout=180)
    print("==", flow, r.status_code, len(r.text))
    dims = re.findall(r'<str:Dimension id="([^"]+)"[^>]*position="(\d+)"', r.text)
    print("   dimensions", dims)
    # codelists
    for cl in re.finditer(r'<str:Codelist[^>]*id="([^"]+)"[^>]*>(.*?)</str:Codelist>', r.text, re.S):
        cid, body = cl.group(1), cl.group(2)
        codes = re.findall(r'<str:Code id="([^"]+)"[^>]*>.*?<com:Name xml:lang="fr">([^<]+)</com:Name>', body, re.S)
        hits = [(c, n) for c, n in codes if re.search(r"[Ll]ait|[Bb]eurre|[Ff]romage|[Yy]a?ourt|[Hh]uile|[Œœ]uf", n)]
        print(f"   codelist {cid}: {len(codes)} codes", hits[:25] if hits else [c for c in codes[:6]])
    # séries correspondantes : on parcourt les codes trouvés dans la liste des produits
    prod_cl = [m.group(1) for m in re.finditer(r'<str:Codelist[^>]*id="([^"]*(?:COICOP|PRODUIT|PRODUCT)[^"]*)"', r.text)]
    print("   listes produit", prod_cl)
    # requête des séries pour chaque code trouvé (clé partielle : seule la dimension produit est fixée)
    pos = {d: int(p) for d, p in dims}
    order = [d for d, _ in sorted(dims, key=lambda x: int(x[1]))]
    prod_dim = next((d for d in order if "COICOP" in d or "PRODUIT" in d), None)
    print("   dimension produit", prod_dim, order)
    cl_body = ""
    for cl in re.finditer(r'<str:Codelist[^>]*id="([^"]+)"[^>]*>(.*?)</str:Codelist>', r.text, re.S):
        if "COICOP" in cl.group(1) or "PRODUIT" in cl.group(1):
            cl_body += cl.group(2)
    codes = re.findall(r'<str:Code id="([^"]+)"[^>]*>.*?<com:Name xml:lang="fr">([^<]+)</com:Name>', cl_body, re.S)
    hits = [c for c, n in codes if re.search(r"^(Lait|Beurre|Fromage|Yaourt|Huile|Œuf|Oeuf)", n.strip())]
    for code in hits[:20]:
        key = ".".join(code if d == prod_dim else "" for d in order)
        d = requests.get(f"https://bdm.insee.fr/series/sdmx/data/{flow}/{key}", params={"lastNObservations": 1},
                         headers=UA, timeout=180)
        for m in re.finditer(r'<Series ([^>]+)>\s*<Obs ([^>]+)/>', d.text):
            a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
            o = dict(re.findall(r'(\w+)="([^"]*)"', m.group(2)))
            t = a.get("TITLE_FR", "")
            if "Ensemble des ménages" in t and "France" in t and "mensuel" in t.lower():
                print(f"   {a.get('IDBANK')} | {t[:160]} | {o.get('TIME_PERIOD')} {o.get('OBS_VALUE')}")
