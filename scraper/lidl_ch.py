"""Lidl Suisse — assortiment permanent publié sur sortiment.lidl.ch (Magento)."""
from __future__ import annotations

import re
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from .common import Candidate, Session, parse_price


class Scraper:
    BASE = "https://sortiment.lidl.ch/fr/catalogsearch/result/?q="

    def __init__(self, s: Session, cfg: dict):
        self.s = s

    def search(self, item: dict) -> list[Candidate]:
        r = self.s.get(self.BASE + quote_plus(item["query"]), tag=f"lidl_ch_{item['id']}")
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        out = []
        for li in soup.select("li.product-item, .product-item-info, div.product-item"):
            a = li.select_one("a.product-item-link") or li.select_one("a[href*='/p/'], a[href*='product']")
            pr = li.select_one("[data-price-amount]")
            if not a or not pr:
                continue
            name = " ".join(a.get_text(" ").split())
            extra = " ".join(x.get_text(" ") for x in li.select(".product-item-details, .weight, .base-price, .product-item-subtitle"))
            price = parse_price(pr.get("data-price-amount"))
            special = li.select_one(".special-price, .old-price, .price-label")
            out.append(Candidate(
                name=name, price=price, currency="CHF", url=a.get("href", ""),
                raw_size=" ".join((extra + " " + name).split()),
                promo=bool(special),
            ))
        # dédoublonnage (Magento répète parfois les blocs)
        seen, uniq = set(), []
        for c in out:
            k = (c.name, c.price)
            if k not in seen:
                seen.add(k)
                uniq.append(c)
        return uniq
