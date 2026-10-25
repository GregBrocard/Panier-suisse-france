"""Recherche des EAN les plus relevés dans Open Prices + texte du PDF OFDF."""
import io

import requests
from pypdf import PdfReader

from .sources import OFDF_T44

for term in ["coca-cola", "evian", "red bull", "lindt excellence", "pringles", "nescafe", "barilla", "kinder bueno",
             "heineken", "ricore", "lactel", "president"]:
    for params in ({"product_name__like": term}, {"brands__like": term}):
        try:
            r = requests.get("https://prices.openfoodfacts.org/api/v1/products",
                             params={**params, "order_by": "-price_count", "size": 6}, timeout=60)
            items = r.json().get("items", [])
        except Exception as e:  # noqa: BLE001
            print(term, params, "ERR", e)
            continue
        if items:
            print(f"== {term} {list(params)[0]} ({r.status_code})")
            for p in items:
                print(f"   {p.get('code')} | {p.get('product_name')} | {p.get('product_quantity')}{p.get('product_quantity_unit') or ''}"
                      f" | {p.get('brands')} | prix={p.get('price_count')}")
            break
    else:
        print("== rien pour", term)

r = requests.get(OFDF_T44, timeout=60)
text = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(r.content)).pages)
print("== OFDF texte\n", text[:4000])
