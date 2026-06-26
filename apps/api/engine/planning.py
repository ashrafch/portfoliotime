"""
Pianificazione per obiettivi (goal-based) — proiezione forward via bootstrap.

ONESTÀ METODOLOGICA (esposta all'utente):
- La proiezione si basa sui rendimenti storici reali di un periodo di riferimento.
- I rendimenti futuri NON sono noti: questa è una distribuzione di scenari, non una
  garanzia. I risultati passati non garantiscono quelli futuri.
- Bootstrap i.i.d. (non modella il raggruppamento dei crash).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Optional

TRADING_DAYS_YEAR = 252
TRADING_DAYS_MONTH = 21

# Allocazioni di riferimento per profilo di rischio (somma 100). Trasparenti e fisse.
REFERENCE_ALLOCATIONS: dict[str, dict[str, float]] = {
    "conservativo": {"azioni": 30, "obbligazioni": 55, "oro": 10, "materie_prime": 5, "bitcoin": 0},
    "bilanciato": {"azioni": 55, "obbligazioni": 30, "oro": 8, "materie_prime": 5, "bitcoin": 2},
    "aggressivo": {"azioni": 75, "obbligazioni": 10, "oro": 5, "materie_prime": 5, "bitcoin": 5},
}

# Periodo storico di riferimento per le statistiche (dichiarato all'utente).
REFERENCE_PERIOD = ("2010-01-01", "2023-12-31")


def project_goal(
    daily_returns: pd.Series,
    horizon_years: int,
    initial: float,
    monthly_contribution: float,
    target: float,
    n_sims: int = 500,
    seed: int = 42,
) -> dict:
    """Proietta forward un piano con versamenti mensili e stima la probabilità di
    raggiungere `target`.

    Returns: dict con probabilità di successo, percentili del valore finale,
    totale versato e statistiche del riferimento.
    """
    finals, total_contributed = _simulate_finals(
        daily_returns, horizon_years, initial, monthly_contribution, n_sims, seed
    )
    if finals is None:
        return {"error": "Dati di riferimento insufficienti."}

    return {
        "probability_success": float((finals >= target).mean()),
        "final_value": {
            "p10": round(float(np.percentile(finals, 10)), 2),
            "p50": round(float(np.percentile(finals, 50)), 2),
            "p90": round(float(np.percentile(finals, 90)), 2),
        },
        "total_contributed": round(total_contributed, 2),
        "target": round(target, 2),
        "horizon_years": horizon_years,
        "monthly_contribution": round(monthly_contribution, 2),
    }


def required_monthly_contribution(
    daily_returns: pd.Series,
    horizon_years: int,
    initial: float,
    target: float,
    success_threshold: float = 0.75,
    n_sims: int = 400,
    seed: int = 42,
) -> Optional[float]:
    """Cerca (ricerca binaria) il versamento mensile per raggiungere `target` con
    probabilità >= success_threshold. None se i dati sono insufficienti.

    La probabilità di successo è monotòna crescente nel versamento → bisezione valida.
    """
    r = daily_returns.dropna().to_numpy()
    if len(r) < 60:
        return None

    def prob(c: float) -> float:
        finals, _ = _simulate_finals(daily_returns, horizon_years, initial, c, n_sims, seed)
        return float((finals >= target).mean()) if finals is not None else 0.0

    # Se il solo capitale iniziale basta già, contributo richiesto = 0
    if prob(0.0) >= success_threshold:
        return 0.0

    lo, hi = 0.0, max(target / max(horizon_years * 12, 1), 100.0)
    # espandi hi finché non supera la soglia (cap di sicurezza)
    for _ in range(20):
        if prob(hi) >= success_threshold:
            break
        hi *= 2
        if hi > 1_000_000:
            return None

    for _ in range(22):  # ~1e-5 di precisione relativa
        mid = (lo + hi) / 2
        if prob(mid) >= success_threshold:
            hi = mid
        else:
            lo = mid
    return round(hi, 2)


def _simulate_finals(
    daily_returns: pd.Series,
    horizon_years: int,
    initial: float,
    monthly_contribution: float,
    n_sims: int,
    seed: int,
) -> tuple[Optional[np.ndarray], float]:
    """Genera la distribuzione dei valori finali (bootstrap forward, versamenti mensili)."""
    r = daily_returns.dropna().to_numpy()
    n = len(r)
    if n < 60:
        return None, 0.0

    days = max(int(horizon_years * TRADING_DAYS_YEAR), TRADING_DAYS_MONTH)
    rng = np.random.default_rng(seed)
    sampled = r[rng.integers(0, n, size=(n_sims, days))]
    g = np.cumprod(1.0 + sampled, axis=1)  # fattore di crescita cumulato (n_sims, days)
    g_end = g[:, -1]

    # Giorni di versamento (mensili), escluso il giorno 0 (coperto dal capitale iniziale)
    contrib_days = list(range(TRADING_DAYS_MONTH, days, TRADING_DAYS_MONTH))
    finals = g_end * initial
    if monthly_contribution > 0 and contrib_days:
        inv_g = 1.0 / g[:, contrib_days]            # (n_sims, k)
        finals = finals + monthly_contribution * g_end * inv_g.sum(axis=1)

    total_contributed = initial + monthly_contribution * len(contrib_days)
    return finals, total_contributed


def reference_stats(daily_returns: pd.Series) -> dict:
    """Rendimento annualizzato e volatilità del periodo di riferimento (trasparenza)."""
    r = daily_returns.dropna()
    if len(r) < 2:
        return {"annual_return": None, "annual_volatility": None}
    ann_ret = float((1.0 + r.mean()) ** TRADING_DAYS_YEAR - 1.0)
    ann_vol = float(r.std() * np.sqrt(TRADING_DAYS_YEAR))
    return {"annual_return": ann_ret, "annual_volatility": ann_vol}
