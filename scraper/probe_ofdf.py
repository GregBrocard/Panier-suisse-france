"""Sonde : texte brut du tableau OFDF T 4.4 (vérifier l'ordre diesel / essence)."""
import io, requests
from pypdf import PdfReader
from .sources import OFDF_T44
r = requests.get(OFDF_T44, timeout=60, headers={"User-Agent": "panier-suisse-france"})
for i, p in enumerate(PdfReader(io.BytesIO(r.content)).pages):
    print(f"===== page {i}")
    print(p.extract_text())
open("debug/t44.pdf", "wb").write(r.content)
