"""
Orchestratore della simulazione portafoglio.

Riceve il profilo utente + scenario temporale, recupera i prezzi dalle fonti dati,
calcola l'allocazione Chameleon e restituisce le metriche calcolate.

R1: Questo modulo non chiama mai il LLM. Passa solo l'output a rag/retrieval.py.
R5: Simulazioni > 2s vengono eseguite via Celery.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import date, datetime
from typing import Optional
from dataclasses import dataclass, field

from engine.metrics import (
    chameleon_portafoglio,
    calc_cagr,
    calc_max_drawdown,
    calc_sharpe_ratio,
    calc_annualized_volatility,
    calc_real_return,
)


@dataclass
class SimulationInput:
    """Parametri di ingresso per una simulazione."""
    eta: int
    tasso_fed: float
    delta_tasso: float
    btc_prezzo_corrente: float
    btc_ath: float
    is_post_halving: bool
    tasso_nominale: float
    inflazione: float
    tassi_in_calo: bool
    qe_attivo: bool
    date_from: str  # formato ISO 8601: "2007-01-01"
    date_to: str
    benchmark_ticker: str = "SPY"


@dataclass
class SimulationResult:
    """Risultato calcolato di una simulazione — tutti i valori sono numerici verificati."""
    allocazione: dict[str, float]
    cagr: float
    max_drawdown: float
    sharpe_ratio: float
    annualized_volatility: float
    real_return: Optional[float]
    total_return: float
    benchmark_cagr: float
    benchmark_max_drawdown: float
    sources: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def run_simulation(sim_input: SimulationInput, prices: pd.DataFrame) -> SimulationResult:
    """Esegue la simulazione completa dato il DataFrame dei prezzi storici.

    Args:
        sim_input: Parametri del profilo utente e del regime macro.
        prices: DataFrame con colonne per ogni asset (ticker come nome colonna),
                indice DatetimeIndex, prezzi giornalieri in USD.

    Returns:
        SimulationResult con tutte le metriche calcolate.
    """
    warnings: list[str] = []

    allocazione = chameleon_portafoglio(
        eta=sim_input.eta,
        tasso_fed=sim_input.tasso_fed,
        delta_tasso=sim_input.delta_tasso,
        btc_prezzo_corrente=sim_input.btc_prezzo_corrente,
        btc_ath=sim_input.btc_ath,
        is_post_halving=sim_input.is_post_halving,
        tasso_nominale=sim_input.tasso_nominale,
        inflazione=sim_input.inflazione,
        tassi_in_calo=sim_input.tassi_in_calo,
        qe_attivo=sim_input.qe_attivo,
    )

    # Costruisci serie portafoglio aggregato con pesi Chameleon
    # R6: Dati crypto disponibili solo dal 2013-01-01
    portfolio_series = _build_portfolio_series(prices, allocazione, warnings)

    if portfolio_series is None or len(portfolio_series) < 2:
        warnings.append("Dati insufficienti per calcolare le metriche.")
        return SimulationResult(
            allocazione=allocazione,
            cagr=float("nan"),
            max_drawdown=float("nan"),
            sharpe_ratio=float("nan"),
            annualized_volatility=float("nan"),
            real_return=None,
            total_return=float("nan"),
            benchmark_cagr=float("nan"),
            benchmark_max_drawdown=float("nan"),
            warnings=warnings,
        )

    returns = portfolio_series.pct_change().dropna()

    cagr = calc_cagr(portfolio_series)
    max_dd = calc_max_drawdown(portfolio_series)
    sharpe = calc_sharpe_ratio(returns)
    volatility = calc_annualized_volatility(returns)
    total_ret = float(portfolio_series.iloc[-1] / portfolio_series.iloc[0] - 1.0)

    # Benchmark
    benchmark_series = prices.get(sim_input.benchmark_ticker)
    benchmark_cagr = calc_cagr(benchmark_series) if benchmark_series is not None else float("nan")
    benchmark_dd = calc_max_drawdown(benchmark_series) if benchmark_series is not None else float("nan")

    sources = {col: "yahoo_finance" for col in prices.columns}
    if "BTC-USD" in prices.columns:
        sources["BTC-USD"] = "coingecko"

    return SimulationResult(
        allocazione=allocazione,
        cagr=cagr,
        max_drawdown=max_dd,
        sharpe_ratio=sharpe,
        annualized_volatility=volatility,
        real_return=None,  # Richiede FRED inflation — collegato in seguito
        total_return=total_ret,
        benchmark_cagr=benchmark_cagr,
        benchmark_max_drawdown=benchmark_dd,
        sources=sources,
        warnings=warnings,
    )


def _build_portfolio_series(
    prices: pd.DataFrame,
    allocazione: dict[str, float],
    warnings: list[str],
) -> Optional[pd.Series]:
    """Combina i prezzi dei singoli asset con i pesi Chameleon in una serie portafoglio."""

    # Mapping asset class → ticker (semplificato MVP)
    asset_to_ticker = {
        "azioni": "SPY",
        "obbligazioni": "TLT",
        "oro": "GLD",
        "bitcoin": "BTC-USD",
        "materie_prime": "GSG",
    }

    weighted_returns = pd.Series(dtype=float)
    total_weight = 0.0

    for asset, ticker in asset_to_ticker.items():
        weight = allocazione.get(asset, 0.0) / 100.0
        if weight == 0.0:
            continue
        if ticker not in prices.columns:
            warnings.append(f"Dati mancanti per {ticker} ({asset}) — asset escluso dal calcolo.")
            continue
        asset_returns = prices[ticker].pct_change().dropna()
        if total_weight == 0.0:
            weighted_returns = asset_returns * weight
        else:
            weighted_returns = weighted_returns.add(asset_returns * weight, fill_value=0.0)
        total_weight += weight

    if total_weight == 0.0 or weighted_returns.empty:
        return None

    # Ricostruisce serie prezzi da rendimenti pesati (base 100)
    portfolio_series = (1.0 + weighted_returns).cumprod() * 100.0
    return portfolio_series
