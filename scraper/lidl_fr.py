"""Lidl France — API de recherche publique utilisée par lidl.fr (prix nationaux)."""
from __future__ import annotations

from urllib.parse import quote_plus

from .common import Candidate, Session, parse_price


class Scraper:
    API = ("https://www.lidl.fr/q/api/search?assortment=FR&locale=fr_FR&version=v2.0.0"
           "&fetchsize=48&offset=0&q=")

    def __init__(self, s: Session, cfg: dict):
        self.s = s

    def search(self, item: dict) -> list[Candidate]:
        r = self.s.get(self.API + quote_plus(item["query"]), tag=f"lidl_fr_{item['id']}",
                       headers={"Accept": "application/json"})
        r.raise_for_status()
        j = r.json()
        out = []
        for it in j.get("items", []):
            d = (it.get("gridbox") or {}).get("data") or it.get("data") or {}
            title = d.get("fullTitle") or d.get("title")
            price = d.get("price") or {}
            if not title or not price:
                continue
            pack = (price.get("packaging") or {}).get("text", "")
            base = (price.get("basePrice") or {}).get("text", "")
            url = d.get("canonicalUrl") or d.get("canonicalPath") or ""
            if url.startswith("/"):
                url = "https://www.lidl.fr" + url
            out.append(Candidate(
                name=title, price=parse_price(price.get("price")), currency="EUR", url=url,
                raw_size=f"{pack} {base}".strip(),
                promo=bool(price.get("oldPrice") or price.get("discount")),
            ))
        return out
