"""Taux de change EUR -> CHF.

Source principale : taux de référence quotidien de la Banque centrale européenne (BCE).
Secours : frankfurter.app (qui republie les taux BCE).
"""
from __future__ import annotations

import re

from .common import Session


def eur_chf(s: Session) -> dict:
    try:
        r = s.get("https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml", tag="fx_ecb")
        rate = re.search(r"currency=['\"]CHF['\"]\s+rate=['\"]([\d.]+)", r.text)
        day = re.search(r"time=['\"](\d{4}-\d{2}-\d{2})", r.text)
        if rate:
            return {"eur_chf": float(rate.group(1)), "date": day.group(1) if day else None,
                    "source": "BCE (taux de référence)"}
    except Exception:  # noqa: BLE001
        pass
    r = s.get("https://api.frankfurter.app/latest?from=EUR&to=CHF", tag="fx_frankfurter")
    j = r.json()
    return {"eur_chf": float(j["rates"]["CHF"]), "date": j.get("date"),
            "source": "BCE via frankfurter.app"}
