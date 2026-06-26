"""
Monte Carlo — proiezione statistica via bootstrap dei rendimenti storici.

ONESTÀ METODOLOGICA (esposta anche all'utente):
- I rendimenti giornalieri del periodo vengono ricampionati con reimmissione (i.i.d.).
- Questo IGNORA autocorrelazione e clustering di volatilità (i crash reali sono più
  "raggruppati" di così).
- I campioni provengono dallo stesso periodo simulato: la proiezione riflette quel
  regime di mercato, non il futuro.
- È una distribuzione di scenari plausibili, NON una previsione.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Optional

MIN_OBS = 20


def bootstrap_projection(returns: pd.Series, n_sims: int = 500, seed: int = 42) -> Optional[dict]:
    """Genera una distribuzione di esiti finali ricampionando i rendimenti.

    Args:
        returns: rendimenti giornalieri del portafoglio.
        n_sims: numero di simulazioni (traiettorie).
        seed: seme per la riproducibilità.

    Returns:
        dict con percentili del rendimento finale, probabilità di perdita,
        bande temporali (fan chart) e metadati sul metodo. None se dati insufficienti.
    """
    r = returns.dropna().to_numpy()
    n = len(r)
    if n < MIN_OBS:
        return None

    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_sims, n))
    sampled = r[idx]
    cum = np.cumprod(1.0 + sampled, axis=1)  # (n_sims, n) crescita cumulata
    finals = cum[:, -1] - 1.0

    pcts = {
        "p5": float(np.percentile(finals, 5)),
        "p25": float(np.percentile(finals, 25)),
        "p50": float(np.percentile(finals, 50)),
        "p75": float(np.percentile(finals, 75)),
        "p95": float(np.percentile(finals, 95)),
    }
    prob_loss = float((finals < 0).mean())

    # Punti temporali per il fan chart (~40 punti)
    step = max(1, n // 40)
    cols = list(range(0, n, step))
    if cols[-1] != n - 1:
        cols.append(n - 1)

    band = {
        "x": [round(c / (n - 1), 4) for c in cols],
        "p5": [round(float(np.percentile(cum[:, c], 5) * 100), 2) for c in cols],
        "p50": [round(float(np.percentile(cum[:, c], 50) * 100), 2) for c in cols],
        "p95": [round(float(np.percentile(cum[:, c], 95) * 100), 2) for c in cols],
    }

    return {
        "n_simulations": n_sims,
        "horizon_days": n,
        "final_return": pcts,
        "prob_loss": prob_loss,
        "band": band,
        "method": "Bootstrap i.i.d. dei rendimenti giornalieri del periodo",
        "disclaimer": (
            "Proiezione statistica, non una previsione. I rendimenti sono ricampionati "
            "con reimmissione dal periodo selezionato, con ipotesi di indipendenza "
            "(non modella il raggruppamento dei crash)."
        ),
    }
