"""Teste un scraper sur quelques besoins et affiche les candidats et le produit retenu.

python -m scraper.test_store <store_id> [item_id ...]
"""
from __future__ import annotations

import importlib
import sys
import traceback

from .common import Session, pick
from .run import load_cfg


def main(store_id: str, item_ids: list[str]) -> None:
    basket, stores = load_cfg()
    st = next(s for s in stores["stores"] if s["id"] == store_id)
    mod = importlib.import_module(f"scraper.{st['scraper']}")
    scraper = mod.Scraper(Session(delay=1.0), st.get("store") or {})
    items = [i for i in basket["items"] if not item_ids or i["id"] in item_ids]
    for item in items:
        print(f"\n=== {item['id']} ({item['query']})")
        try:
            cands = scraper.search(item)
        except Exception:  # noqa: BLE001
            traceback.print_exc()
            continue
        for c in cands[:12]:
            print(f"   - {c.name[:60]:60s} {c.price} {c.currency} size={c.raw_size!r} up={c.unit_price} promo={c.promo}")
        chosen = pick(item, cands)
        print(f"   => {chosen.name if chosen else 'AUCUN'} | {chosen.price if chosen else ''} "
              f"| {chosen.size if chosen else ''} {chosen.unit if chosen else ''} | {chosen.unit_price if chosen else ''}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
