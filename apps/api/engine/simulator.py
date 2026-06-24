"""
Orchestratore della simulazione portafoglio.

Riceve il profilo utente + scenario temporale, recupera i prezzi dalle fonti dati,
calcola l'allocazione Chameleon e restituisce le metriche calcolate + la curva equity.

R1: Questo modulo non chiama mai il LLM. Calcola solo numeri verificati.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Optional
from dataclasses import dataclass, field

from engine.metrics import (
    chameleon_portafoglio,
    calc_cagr,
    calc_max_drawdown,
    calc_sharpe_ratio,
    calc_annualized_volatility,
)
from data.yfinance_client import ASSET_TICKERS


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
    date_from: str  # ISO 8601: "2007-01-01"
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
    benchmark_total_return: float
    equity_curve: list[dict]  # [{"date": "2008-01-02", "portfolio": 100.0, "benchmark": 100.0}, ...]
    sources: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def run_simulation(sim_input: SimulationInput, prices: pd.DataFrame) -> SimulationResult:
    """Esegue la simulazione completa dato il DataFrame dei prezzi storici."""
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

    portfolio_series = _build_portfolio_series(prices, allocazione, warnings)

    if portfolio_series is None or len(portfolio_series) < 2:
        warnings.append("Dati di mercato insufficienti per il periodo selezionato.")
        return SimulationResult(
            allocazione=allocazione,
            cagr=float("nan"), max_drawdown=float("nan"),
            sharpe_ratio=float("nan"), annualized_volatility=float("nan"),
            real_return=None, total_return=float("nan"),
            benchmark_cagr=float("nan"), benchmark_max_drawdown=float("nan"),
            benchmark_total_return=float("nan"),
            equity_curve=[], warnings=warnings,
        )

    returns = portfolio_series.pct_change().dropna()

    cagr = calc_cagr(portfolio_series)
    max_dd = calc_max_drawdown(portfolio_series)
    sharpe = calc_sharpe_ratio(returns)
    volatility = calc_annualized_volatility(returns)
    total_ret = float(portfolio_series.iloc[-1] / portfolio_series.iloc[0] - 1.0)

    # Rendimento reale: dedotto dall'inflazione annua dichiarata (source: calculated)
    real_ret = _real_return_from_annual_inflation(total_ret, sim_input, portfolio_series)

    # Benchmark
    benchmark_series = prices.get(sim_input.benchmark_ticker)
    if benchmark_series is not None:
        benchmark_series = benchmark_series.dropna()
    benchmark_curve = None
    if benchmark_series is not None and len(benchmark_series) >= 2:
        benchmark_cagr = calc_cagr(benchmark_series)
        benchmark_dd = calc_max_drawdown(benchmark_series)
        benchmark_total = float(benchmark_series.iloc[-1] / benchmark_series.iloc[0] - 1.0)
        benchmark_curve = benchmark_series / benchmark_series.iloc[0] * 100.0
    else:
        benchmark_cagr = float("nan")
        benchmark_dd = float("nan")
        benchmark_total = float("nan")

    equity_curve = _build_equity_curve(portfolio_series, benchmark_curve)

    sources = {col: "yahoo_finance" for col in prices.columns}
    sources["real_return"] = "calculated"

    return SimulationResult(
        allocazione=allocazione,
        cagr=cagr, max_drawdown=max_dd,
        sharpe_ratio=sharpe, annualized_volatility=volatility,
        real_return=real_ret, total_return=total_ret,
        benchmark_cagr=benchmark_cagr, benchmark_max_drawdown=benchmark_dd,
        benchmark_total_return=benchmark_total,
        equity_curve=equity_curve, sources=sources, warnings=warnings,
    )


def _real_return_from_annual_inflation(
    total_ret: float, sim_input: SimulationInput, series: pd.Series
) -> Optional[float]:
    """Rendimento reale via Fisher usando l'inflazione annua dichiarata.

    R_reale = (1 + R_nominale) / (1 + pi)^anni - 1
    """
    if np.isnan(total_ret):
        return None
    years = max((series.index[-1] - series.index[0]).days / 365.25, 1e-9)
    infl_factor = (1.0 + sim_input.inflazione / 100.0) ** years
    if infl_factor <= 0:
        return None
    return (1.0 + total_ret) / infl_factor - 1.0


def _build_portfolio_series(
    prices: pd.DataFrame, allocazione: dict[str, float], warnings: list[str]
) -> Optional[pd.Series]:
    """Combina i prezzi dei singoli asset con i pesi Chameleon (rebalanced daily)."""
    weighted_returns = pd.Series(dtype=float)
    total_weight = 0.0

    for asset, ticker in ASSET_TICKERS.items():
        weight = allocazione.get(asset, 0.0) / 100.0
        if weight == 0.0:
            continue
        if ticker not in prices.columns:
            warnings.append(f"Dati mancanti per {ticker} ({asset}) — asset escluso.")
            continue
        asset_returns = prices[ticker].pct_change().dropna()
        if asset_returns.empty:
            continue
        if total_weight == 0.0:
            weighted_returns = asset_returns * weight
        else:
            weighted_returns = weighted_returns.add(asset_returns * weight, fill_value=0.0)
        total_weight += weight

    if total_weight == 0.0 or weighted_returns.empty:
        return None

    return (1.0 + weighted_returns).cumprod() * 100.0


def _build_equity_curve(
    portfolio_series: pd.Series, benchmark_curve: Optional[pd.Series], max_points: int = 90
) -> list[dict]:
    """Downsample della curva equity per il grafico frontend (base 100)."""
    pf = portfolio_series.copy()
    # Normalizza a base 100 dal primo punto
    pf = pf / pf.iloc[0] * 100.0

    n = len(pf)
    step = max(1, n // max_points)
    idx = list(range(0, n, step))
    if idx[-1] != n - 1:
        idx.append(n - 1)

    curve = []
    for i in idx:
        ts = pf.index[i]
        point = {"date": ts.strftime("%Y-%m-%d"), "portfolio": round(float(pf.iloc[i]), 2)}
        if benchmark_curve is not None:
            # Allinea il benchmark alla stessa data, se disponibile
            try:
                bval = benchmark_curve.iloc[benchmark_curve.index.get_indexer([ts], method="nearest")[0]]
                point["benchmark"] = round(float(bval), 2)
            except (KeyError, IndexError):
                pass
        curve.append(point)
    return curve
