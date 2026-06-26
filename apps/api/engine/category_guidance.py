"""
Guida per categoria di asset — contenuti curati (allineati ai documenti in
knowledge-base/categorie) + stima prospettica ONESTA.

Principio: la stima prospettica esiste solo dove è metodologicamente difendibile
(obbligazioni ≈ yield; azioni ≈ risk-free + premio storico). Per oro, materie prime
e Bitcoin il rendimento atteso NON è stimabile in modo affidabile e lo diciamo.
"""

from __future__ import annotations
from typing import Optional

# Premio al rischio azionario storico (assunzione esplicita, ~4-5%)
EQUITY_RISK_PREMIUM = 0.045

GUIDANCE: dict[str, dict] = {
    "azioni": {
        "label": "Azioni",
        "role": "Motore di crescita di lungo periodo: rendimento atteso più alto, ma oscillazioni ampie.",
        "what_to_choose": [
            "Indice ampio (globale o S&P 500), non singoli titoli",
            "ETF UCITS a replica fisica, costi bassi (TER < 0,20%)",
            "Accumulazione se non ti servono cedole (comodo in Italia)",
        ],
        "risks": ["Drawdown profondi (es. -50% nel 2008)", "Rischio di concentrazione", "Rischio di sequenza vicino all'obiettivo"],
        "forward_method": "tasso privo di rischio (10Y) + premio al rischio storico (~4,5%)",
    },
    "obbligazioni": {
        "label": "Obbligazioni",
        "role": "Stabilizzatore: riduce le oscillazioni e dà un reddito da cedole.",
        "what_to_choose": [
            "Titoli di Stato/aggregato di alta qualità",
            "Duration coerente: breve = più stabile",
            "Per chi è in euro, valutare versioni EUR hedged",
        ],
        "risks": ["Rischio tassi (male nel 2022)", "Rischio credito (high yield)", "Inflazione erode le cedole fisse"],
        "forward_method": "≈ rendimento a scadenza attuale (yield del 10Y come proxy)",
    },
    "oro": {
        "label": "Oro",
        "role": "Bene rifugio e diversificatore; quota piccola (5-10%).",
        "what_to_choose": [
            "ETC a replica fisica (oro allocato)",
            "Costi bassi, emittente solido",
            "Consapevolezza dell'effetto cambio EUR/USD",
        ],
        "risks": ["Nessuna cedola", "Lunghe fasi negative (1980-2000)", "Sensibile a tassi reali e dollaro"],
        "forward_method": None,  # non stimabile
    },
    "materie_prime": {
        "label": "Materie Prime",
        "role": "Diversificatore, possibile copertura dall'inflazione inattesa; quota piccola.",
        "what_to_choose": [
            "Paniere ampio (es. Bloomberg Commodity), non una sola commodity",
            "Attenzione al roll dei futures (contango/backwardation)",
            "Costi tipicamente più alti di un ETF azionario",
        ],
        "risks": ["Nessun flusso di cassa", "Molto cicliche e volatili", "Lunghe fasi di rendimento reale negativo"],
        "forward_method": None,
    },
    "bitcoin": {
        "label": "Bitcoin",
        "role": "Asset speculativo e volatile; solo quota piccola (1-5%) di capitale che puoi permetterti di perdere.",
        "what_to_choose": [
            "Exchange regolamentato o ETP a replica fisica (in UE non esistono ETF)",
            "Posizione piccola e coerente col rischio",
            "Custodia/sicurezza delle chiavi se detenuto direttamente",
        ],
        "risks": ["Volatilità estrema (-80% nel 2018/2022)", "Rischio exchange/custodia (FTX 2022)", "Nessun valore fondamentale condiviso"],
        "forward_method": None,
    },
}

ASSET_ORDER = ["azioni", "obbligazioni", "oro", "materie_prime", "bitcoin"]


def forward_estimate(asset: str, risk_free: Optional[float]) -> dict:
    """Stima prospettica del rendimento annuo atteso, dove difendibile.

    Args:
        asset: chiave categoria.
        risk_free: tasso privo di rischio in decimale (es. 0.04) o None se non disponibile.

    Returns:
        {"value": float|None, "method": str, "estimable": bool}
    """
    g = GUIDANCE.get(asset, {})
    method = g.get("forward_method")

    if method is None:
        return {
            "value": None,
            "method": "Asset senza cedole/utili: rendimento atteso non stimabile in modo affidabile.",
            "estimable": False,
        }

    if risk_free is None:
        return {
            "value": None,
            "method": f"Stima ({method}) non calcolabile senza i tassi correnti (FRED).",
            "estimable": False,
        }

    if asset == "obbligazioni":
        value = risk_free
    elif asset == "azioni":
        value = risk_free + EQUITY_RISK_PREMIUM
    else:
        value = None

    return {"value": value, "method": method, "estimable": value is not None}
