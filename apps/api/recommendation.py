"""
Servizio condiviso per l'allocazione consigliata "oggi".

Usato sia da /portfolio/recommended (che salva lo snapshot) sia da
/me/notifications (che rileva i cambiamenti senza salvare).
"""

from __future__ import annotations

from datetime import date, timedelta

from engine.metrics import chameleon_portafoglio
from data import fred_client

ASSET_KEYS = ["azioni", "obbligazioni", "oro", "materie_prime", "bitcoin"]


async def current_recommendation(profile) -> dict:
    """Calcola l'allocazione Chameleon nella situazione macro attuale.

    Fonte macro: FRED (dati reali) se configurato, altrimenti le assunzioni del
    profilo utente. Non salva nulla.
    """
    source = "profilo"
    tasso_fed = profile.default_tasso_fed
    inflazione = profile.default_inflazione
    tasso_nominale = profile.default_tasso_fed
    delta_tasso = 0.0
    tassi_in_calo = False

    if fred_client.is_configured():
        try:
            today = date.today()
            snap = await fred_client.macro_snapshot(
                (today - timedelta(days=400)).isoformat(), today.isoformat()
            )
            if snap:
                tasso_fed = snap["tasso_fed"]
                inflazione = snap["inflazione"]
                tasso_nominale = snap["tasso_nominale"]
                delta_tasso = snap["delta_tasso"]
                tassi_in_calo = snap["tassi_in_calo"]
                source = "fred"
        except Exception:  # noqa: BLE001
            pass

    allocazione = chameleon_portafoglio(
        eta=profile.eta, tasso_fed=tasso_fed, delta_tasso=delta_tasso,
        btc_prezzo_corrente=0, btc_ath=0, is_post_halving=False,
        tasso_nominale=tasso_nominale, inflazione=inflazione,
        tassi_in_calo=tassi_in_calo, qe_attivo=False,
    )

    return {
        "allocazione": allocazione,
        "source": source,
        "macro_used": {
            "tasso_fed": tasso_fed, "inflazione": inflazione,
            "tasso_nominale": tasso_nominale, "delta_tasso": delta_tasso,
            "tassi_in_calo": tassi_in_calo,
        },
    }


def diff_allocations(old: dict | None, new: dict, threshold: float = 0.5) -> list[dict]:
    """Differenze significative (>= threshold punti %) tra due allocazioni."""
    if not old:
        return []
    changes = []
    for k in ASSET_KEYS:
        o = float(old.get(k, 0))
        n = float(new.get(k, 0))
        if abs(n - o) >= threshold:
            changes.append({"asset": k, "da": round(o, 1), "a": round(n, 1)})
    return changes
