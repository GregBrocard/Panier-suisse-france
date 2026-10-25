"""Migros — API publique utilisée par migros.ch (jeton invité, prix nationaux)."""
from __future__ import annotations

from .common import Candidate, Session, parse_price

BASE = "https://www.migros.ch"


class Scraper:
    def __init__(self, s: Session, cfg: dict):
        self.s = s
        self.token = None

    def _auth(self):
        r = self.s.get(f"{BASE}/authentication/public/v1/api/guest?authorizationNotRequired=true",
                       tag="migros_guest")
        r.raise_for_status()
        self.token = r.headers.get("leshopch")
        self.h = {"leshopch": self.token, "Accept": "application/json",
                  "Content-Type": "application/json", "Origin": BASE, "Referer": BASE + "/fr",
                  "accept-language": "fr", "migros-language": "fr"}

    def search(self, item: dict) -> list[Candidate]:
        if not self.token:
            self._auth()
        body = {"regionId": "national", "language": "fr", "productIds": [], "query": item["query"],
                "sortFields": [], "sortOrder": "asc", "algorithm": "DEFAULT", "filters": {}}
        r = self.s.post(f"{BASE}/onesearch-oc-seaapi/public/v5/search", json=body, headers=self.h,
                        tag=f"migros_search_{item['id']}")
        r.raise_for_status()
        ids = r.json().get("productIds", [])[:30]
        if not ids:
            return []
        r = self.s.post(f"{BASE}/product-display/public/v4/product-cards",
                        json={"offerFilter": {"storeType": "OFFLINE", "region": "national", "ongoingOfferDate": None},
                              "productFilter": {"uids": ids}},
                        headers=self.h, tag=f"migros_cards_{item['id']}")
        r.raise_for_status()
        out = []
        data = r.json()
        for p in (data if isinstance(data, list) else data.get("products", [])):
            offer = p.get("offer") or {}
            price = offer.get("price") or {}
            brand = p.get("brandLine") or p.get("brand") or ""
            name = " ".join(x for x in [brand, p.get("title") or p.get("name")] if x)
            eff, adv = price.get("effectiveValue"), price.get("advertisedValue")
            out.append(Candidate(
                name=name,
                price=parse_price(adv if adv else eff),
                currency="CHF",
                url=p.get("productUrls") or f"{BASE}/fr/product/{p.get('migrosId')}",
                raw_size=str(offer.get("quantity") or ""),
                promo=(offer.get("type") not in (None, "STANDARD")) or (eff is not None and adv is not None and eff < adv),
                variable_weight=bool(offer.get("isVariableWeight")),
            ))
        return out
