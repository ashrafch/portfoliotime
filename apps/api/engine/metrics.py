"""
Motore finanziario PortfolioTime — metriche e formule.

STRATO 1: Formule proprietarie del Chameleon Portfolio (da PDF cliente).
STRATO 2: Metriche standard aggiuntive (CAGR, Sharpe, Drawdown, Volatilità).

Regola R1: Questo modulo calcola SEMPRE i numeri. Il LLM riceve solo l'output.
"""

import numpy as np
import pandas as pd
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# STRATO 1 — Formule dal PDF cliente (Chameleon Portfolio)
# ─────────────────────────────────────────────────────────────────────────────

def chameleon_azioni(eta: int, tasso_fed: float, delta_tasso: float) -> float:
    """Formula da PDF cliente — Allocazione Azioni.

    Formula: Azioni = 125 - eta - (tasso_fed * 5) - (delta_tasso * 3)

    Args:
        eta: Età dell'investitore in anni.
        tasso_fed: Tasso FED corrente in percentuale (es. 5.25).
        delta_tasso: Variazione recente del tasso FED in punti percentuali
                     (positivo = aumento, negativo = calo).

    Returns:
        Percentuale allocata ad azioni, clampata in [0, 100].

    Example:
        >>> chameleon_azioni(40, 5.25, 0.25)
        58.5   # 125 - 40 - (5.25*5) - (0.25*3) = 125 - 40 - 26.25 - 0.75
    """
    raw = 125.0 - eta - (tasso_fed * 5) - (delta_tasso * 3)
    return max(0.0, min(100.0, raw))


def chameleon_bitcoin(
    btc_prezzo_corrente: float,
    btc_ath: float,
    is_post_halving: bool,
) -> float:
    """Formula da PDF cliente — Allocazione Bitcoin.

    Formula: Bitcoin = max(0, 5 - 10 * ((P_cur / P_ath) - 1))  se post-halving
             Bitcoin = 0                                         altrimenti

    La formula assegna più peso quando Bitcoin è lontano dal suo ATH (potenziale
    di recupero) e meno quando è vicino o supera il vecchio massimo.

    Args:
        btc_prezzo_corrente: Prezzo corrente di Bitcoin in USD.
        btc_ath: All-Time High storico di Bitcoin in USD.
        is_post_halving: True se siamo nel periodo post-halving (12-18 mesi dopo).

    Returns:
        Percentuale allocata a Bitcoin, >= 0.

    Example:
        >>> chameleon_bitcoin(30000, 69000, True)
        10.65   # max(0, 5 - 10 * ((30000/69000) - 1)) = 5 - 10 * (-0.565) = 10.65
        >>> chameleon_bitcoin(69000, 69000, True)
        5.0     # all'ATH: 5 - 10 * 0 = 5
        >>> chameleon_bitcoin(30000, 69000, False)
        0.0     # non post-halving
    """
    if not is_post_halving:
        return 0.0
    if btc_ath <= 0:
        return 0.0
    ratio = btc_prezzo_corrente / btc_ath
    return max(0.0, 5.0 - 10.0 * (ratio - 1.0))


def chameleon_oro(tasso_nominale: float, inflazione: float) -> float:
    """Formula da PDF cliente — Allocazione Oro.

    Formula: Oro = max(5, min(10, 5 + (1 - (tasso_reale / 2)) * 5))
             tasso_reale = tasso_nominale - inflazione

    Soglie esplicite PDF: Min 5%, Max 10%.

    Args:
        tasso_nominale: Tasso nominale corrente in % (es. FED Funds Rate = 5.25).
        inflazione: Inflazione corrente in % (es. CPI YoY = 3.5).

    Returns:
        Percentuale allocata ad Oro, in [5, 10].

    Example:
        >>> chameleon_oro(5.25, 3.5)  # tasso_reale = 1.75
        8.625   # 5 + (1 - 1.75/2) * 5 = 5 + (1 - 0.875) * 5 = 5 + 0.625 = 5.625 → clamp 5..10 = 5.625 ?
        # Calcoliamo: tasso_reale=1.75, raw=5+(1-0.875)*5=5+0.625=5.625
        >>> chameleon_oro(1.0, 6.0)   # tasso_reale = -5.0 (repressione finanziaria)
        10.0    # raw = 5 + (1 - (-5/2)) * 5 = 5 + (1+2.5)*5 = 5+17.5=22.5 → clamp a 10
    """
    tasso_reale = tasso_nominale - inflazione
    raw = 5.0 + (1.0 - (tasso_reale / 2.0)) * 5.0
    return max(5.0, min(10.0, raw))


def chameleon_materie_prime(
    inflazione: float,
    tasso_nominale: float,
    tassi_in_calo: bool,
) -> float:
    """Formula da PDF cliente — Allocazione Materie Prime.

    Formula: 0%                                           se tassi in calo
             max(0, min(10, 5 + (inflazione - tasso_reale) * 2))  altrimenti
             tasso_reale = tasso_nominale - inflazione

    Args:
        inflazione: Inflazione corrente in %.
        tasso_nominale: Tasso nominale corrente in %.
        tassi_in_calo: True se il trend FED è discendente (ultimi 3 mesi).

    Returns:
        Percentuale allocata a Materie Prime, in [0, 10].

    Example:
        >>> chameleon_materie_prime(6.0, 4.0, False)  # tasso_reale = -2.0
        10.0   # 5 + (6 - (-2)) * 2 = 5 + 16 = 21 → clamp a 10
        >>> chameleon_materie_prime(6.0, 4.0, True)
        0.0    # tassi in calo → forza a 0
    """
    if tassi_in_calo:
        return 0.0
    tasso_reale = tasso_nominale - inflazione
    raw = 5.0 + (inflazione - tasso_reale) * 2.0
    return max(0.0, min(10.0, raw))


def chameleon_portafoglio(
    eta: int,
    tasso_fed: float,
    delta_tasso: float,
    btc_prezzo_corrente: float,
    btc_ath: float,
    is_post_halving: bool,
    tasso_nominale: float,
    inflazione: float,
    tassi_in_calo: bool,
    qe_attivo: bool,
) -> dict[str, float]:
    """Formula da PDF cliente — Portafoglio Chameleon completo.

    Calcola le allocazioni percentuali per tutte le asset class.
    Ordine obbligatorio: Azioni → Bitcoin → Oro → Materie Prime → Obbligazioni → QE override.

    Args:
        eta: Età dell'investitore (anni).
        tasso_fed: Tasso FED corrente (%).
        delta_tasso: Variazione recente del tasso FED (pp).
        btc_prezzo_corrente: Prezzo BTC corrente (USD).
        btc_ath: All-Time High BTC storico (USD).
        is_post_halving: True se nel periodo post-halving.
        tasso_nominale: Tasso nominale corrente (%).
        inflazione: Inflazione corrente (%).
        tassi_in_calo: True se trend FED discendente.
        qe_attivo: True se QE attivo da FED/BCE/BOJ.

    Returns:
        Dict con chiavi: azioni, bitcoin, oro, materie_prime, obbligazioni.
        Valori in percentuale (es. 60.0 = 60%).
    """
    azioni = chameleon_azioni(eta, tasso_fed, delta_tasso)
    bitcoin = chameleon_bitcoin(btc_prezzo_corrente, btc_ath, is_post_halving)
    oro = chameleon_oro(tasso_nominale, inflazione)
    materie_prime = chameleon_materie_prime(inflazione, tasso_nominale, tassi_in_calo)

    if qe_attivo:
        obbligazioni = 0.0
    else:
        obbligazioni = max(0.0, 100.0 - (azioni + bitcoin + oro + materie_prime))

    return {
        "azioni": round(azioni, 2),
        "bitcoin": round(bitcoin, 2),
        "oro": round(oro, 2),
        "materie_prime": round(materie_prime, 2),
        "obbligazioni": round(obbligazioni, 2),
    }


# ─────────────────────────────────────────────────────────────────────────────
# STRATO 2 — Metriche standard (non nel PDF, servono per valutare la strategia)
# ─────────────────────────────────────────────────────────────────────────────

def calc_cagr(prices: pd.Series) -> float:
    """Compound Annual Growth Rate (CAGR).

    Formula: CAGR = (P_end / P_start)^(1 / anni) - 1

    Args:
        prices: Serie temporale dei prezzi con indice DatetimeIndex.

    Returns:
        CAGR come decimale (es. 0.12 = 12%). NaN se serie insufficiente.

    Example:
        >>> prices = pd.Series([100, 121], index=pd.date_range('2020-01-01', periods=2, freq='YE'))
        >>> calc_cagr(prices)
        0.21  # appross. per 1 anno: 21%
    """
    prices = prices.dropna()
    if len(prices) < 2:
        return float("nan")
    start, end = prices.iloc[0], prices.iloc[-1]
    if start <= 0:
        return float("nan")
    years = (prices.index[-1] - prices.index[0]).days / 365.25
    if years <= 0:
        return float("nan")
    return (end / start) ** (1.0 / years) - 1.0


def calc_max_drawdown(prices: pd.Series) -> float:
    """Maximum Drawdown — perdita massima dal picco al minimo successivo.

    Formula: MDD = min((P_t - P_peak) / P_peak)

    Args:
        prices: Serie temporale dei prezzi con indice DatetimeIndex.

    Returns:
        Max drawdown come decimale negativo (es. -0.37 = -37%). NaN se serie vuota.

    Example:
        >>> prices = pd.Series([100, 150, 80, 120])
        >>> calc_max_drawdown(prices)
        -0.4667  # (80-150)/150
    """
    prices = prices.dropna()
    if len(prices) < 2:
        return float("nan")
    rolling_max = prices.cummax()
    drawdown = (prices - rolling_max) / rolling_max
    return float(drawdown.min())


def calc_sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.02,
    periods_per_year: int = 252,
) -> float:
    """Sharpe Ratio annualizzato.

    Formula: Sharpe = (R_portfolio - R_free) / sigma_portfolio * sqrt(periods_per_year)

    Args:
        returns: Serie di rendimenti periodici (non cumulativi).
        risk_free_rate: Tasso risk-free annuale (default 2%).
        periods_per_year: 252 per dati giornalieri, 12 per mensili.

    Returns:
        Sharpe ratio. NaN se deviazione standard = 0.

    Example:
        >>> import numpy as np
        >>> returns = pd.Series(np.random.normal(0.001, 0.01, 252))
        >>> calc_sharpe_ratio(returns)  # valore tipico: 0.5-2.0
    """
    returns = returns.dropna()
    if len(returns) < 2:
        return float("nan")
    rf_per_period = risk_free_rate / periods_per_year
    excess = returns - rf_per_period
    std = returns.std()
    if std == 0 or np.isnan(std):
        return float("nan")
    return float((excess.mean() / std) * np.sqrt(periods_per_year))


def calc_annualized_volatility(
    returns: pd.Series,
    periods_per_year: int = 252,
) -> float:
    """Volatilità annualizzata (deviazione standard dei rendimenti).

    Formula: Volatilità = std(returns) * sqrt(periods_per_year)

    Args:
        returns: Serie di rendimenti periodici (non cumulativi).
        periods_per_year: 252 per dati giornalieri, 12 per mensili.

    Returns:
        Volatilità annualizzata come decimale (es. 0.20 = 20%). NaN se serie vuota.

    Example:
        >>> returns = pd.Series([0.01, -0.005, 0.008, -0.012])
        >>> calc_annualized_volatility(returns, periods_per_year=252)
    """
    returns = returns.dropna()
    if len(returns) < 2:
        return float("nan")
    return float(returns.std() * np.sqrt(periods_per_year))


def calc_real_return(
    nominal_return: float,
    inflation_series: pd.Series,
) -> float:
    """Rendimento reale (corretto per inflazione) — formula di Fisher.

    Formula: R_reale = (1 + R_nominale) / (1 + pi) - 1
             dove pi è l'inflazione media annua del periodo.

    Args:
        nominal_return: Rendimento nominale totale del periodo (decimale, es. 0.50 = 50%).
        inflation_series: Serie mensile o annuale dell'inflazione (CPI YoY da FRED).

    Returns:
        Rendimento reale come decimale. NaN se inflation_series è vuota.

    Example:
        >>> inflation = pd.Series([0.03, 0.035, 0.04])  # 3%, 3.5%, 4% per anno
        >>> calc_real_return(0.20, inflation)
        # approx (1.20 / 1.035) - 1 ≈ 0.158 (15.8%)
    """
    inflation_series = inflation_series.dropna()
    if len(inflation_series) == 0:
        return float("nan")
    avg_inflation = float(inflation_series.mean())
    return (1.0 + nominal_return) / (1.0 + avg_inflation) - 1.0


# ─────────────────────────────────────────────────────────────────────────────
# STRATO 2b — Metriche di rischio avanzate
# ─────────────────────────────────────────────────────────────────────────────

def calc_sortino_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.02,
    periods_per_year: int = 252,
) -> float:
    """Sortino Ratio annualizzato — come Sharpe ma penalizza solo la volatilità negativa.

    Formula: Sortino = (mean(excess) / downside_deviation) * sqrt(periods_per_year)
             downside_deviation = sqrt( mean( min(0, excess)^2 ) )

    A differenza dello Sharpe, non penalizza le oscillazioni positive.

    Args:
        returns: rendimenti periodici (non cumulativi).
        risk_free_rate: tasso risk-free annuale.
        periods_per_year: 252 per dati giornalieri.

    Returns:
        Sortino ratio. NaN se non ci sono rendimenti sotto la soglia (downside dev = 0).

    Example:
        >>> r = pd.Series([0.01, -0.02, 0.015, -0.01, 0.02])
        >>> calc_sortino_ratio(r, risk_free_rate=0.0)  # > Sharpe sugli stessi dati
    """
    returns = returns.dropna()
    if len(returns) < 2:
        return float("nan")
    rf_per_period = risk_free_rate / periods_per_year
    excess = returns - rf_per_period
    downside = excess.clip(upper=0.0)
    downside_dev = float(np.sqrt((downside ** 2).mean()))
    if downside_dev == 0 or np.isnan(downside_dev):
        return float("nan")
    return float((excess.mean() / downside_dev) * np.sqrt(periods_per_year))


def calc_calmar_ratio(cagr: float, max_drawdown: float) -> float:
    """Calmar Ratio = CAGR / |Max Drawdown|.

    Misura il rendimento per unità di perdita massima subita. Più alto è meglio.

    Args:
        cagr: CAGR come decimale.
        max_drawdown: max drawdown come decimale negativo.

    Returns:
        Calmar ratio. NaN se max_drawdown è 0 o non valido.

    Example:
        >>> calc_calmar_ratio(0.12, -0.30)
        0.4
    """
    if max_drawdown is None or np.isnan(max_drawdown) or max_drawdown == 0:
        return float("nan")
    if cagr is None or np.isnan(cagr):
        return float("nan")
    return float(cagr / abs(max_drawdown))


def calc_historical_var(returns: pd.Series, confidence: float = 0.95) -> float:
    """Value at Risk storico (per periodo, tipicamente giornaliero).

    Definizione: la perdita che NON viene superata nel `confidence`% dei periodi.
    Restituita come rendimento decimale NEGATIVO (es. -0.034 = nel 5% dei giorni
    peggiori si perde più del 3.4%).

    Metodo: quantile empirico (storico), nessuna assunzione di normalità.

    Args:
        returns: rendimenti periodici.
        confidence: livello di confidenza (default 0.95).

    Returns:
        VaR come decimale negativo. NaN se dati insufficienti.

    Example:
        >>> r = pd.Series([-0.05, -0.02, 0.0, 0.01, 0.03])
        >>> calc_historical_var(r, 0.95)  # quantile 5%
    """
    returns = returns.dropna()
    if len(returns) < 2:
        return float("nan")
    q = float(np.quantile(returns, 1.0 - confidence))
    return q


def calc_historical_cvar(returns: pd.Series, confidence: float = 0.95) -> float:
    """Conditional VaR (Expected Shortfall): perdita media nei periodi peggiori.

    Media dei rendimenti che cadono oltre la soglia VaR (coda sinistra).
    Più severa del VaR. Restituita come decimale negativo.

    Args:
        returns: rendimenti periodici.
        confidence: livello di confidenza (default 0.95).

    Returns:
        CVaR come decimale negativo. NaN se dati insufficienti.
    """
    returns = returns.dropna()
    if len(returns) < 2:
        return float("nan")
    threshold = np.quantile(returns, 1.0 - confidence)
    tail = returns[returns <= threshold]
    if len(tail) == 0:
        return float(threshold)
    return float(tail.mean())


def calc_beta(returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """Beta del portafoglio rispetto al benchmark.

    Formula: Beta = Cov(R_p, R_b) / Var(R_b)
    Beta=1 → si muove come il benchmark; >1 più volatile; <1 meno volatile.

    Args:
        returns: rendimenti del portafoglio.
        benchmark_returns: rendimenti del benchmark.

    Returns:
        Beta. NaN se dati insufficienti o varianza benchmark = 0.

    Example:
        >>> import numpy as np
        >>> b = pd.Series(np.random.normal(0, 0.01, 300))
        >>> p = 1.5 * b  # beta atteso ~1.5
        >>> round(calc_beta(p, b), 1)
        1.5
    """
    df = pd.concat([returns, benchmark_returns], axis=1, join="inner").dropna()
    if len(df) < 2:
        return float("nan")
    p = df.iloc[:, 0]
    b = df.iloc[:, 1]
    var_b = float(b.var())
    if var_b == 0 or np.isnan(var_b):
        return float("nan")
    cov = float(np.cov(p, b)[0, 1])
    return cov / var_b


def calc_underwater_recovery(prices: pd.Series) -> dict:
    """Tempo di recupero: il periodo più lungo passato sotto un massimo precedente.

    Calcola, lungo la serie, la durata massima in giorni tra un picco e il momento
    in cui il valore torna a superarlo (periodo "underwater"). Se alla fine del
    periodo il portafoglio non ha recuperato l'ultimo picco, lo segnala.

    Args:
        prices: serie prezzi/equity con DatetimeIndex.

    Returns:
        dict con:
          - max_underwater_days: int | None — durata massima del periodo underwater
          - recovered: bool — se il drawdown peggiore è stato recuperato nel periodo

    Example:
        >>> idx = pd.to_datetime(["2020-01-01","2020-02-01","2020-06-01","2020-12-01"])
        >>> calc_underwater_recovery(pd.Series([100, 80, 100, 120], index=idx))
        # underwater da 2020-01-01 a 2020-06-01 → ~152 giorni, recovered True
    """
    prices = prices.dropna()
    if len(prices) < 2:
        return {"max_underwater_days": None, "recovered": True}

    running_max = prices.cummax()
    underwater = prices < running_max

    max_days = 0
    cur_start = None
    longest_recovered = True

    # peak time corrente = ultima data in cui prices == running_max
    peak_time = prices.index[0]
    for ts, is_uw in underwater.items():
        if not is_uw:
            # nuovo massimo: chiude eventuale periodo underwater
            if cur_start is not None:
                days = (ts - cur_start).days
                if days > max_days:
                    max_days = days
                cur_start = None
            peak_time = ts
        else:
            if cur_start is None:
                cur_start = peak_time  # il periodo underwater parte dall'ultimo picco

    # periodo underwater ancora aperto a fine serie → non recuperato
    if cur_start is not None:
        days = (prices.index[-1] - cur_start).days
        if days >= max_days:
            max_days = days
            longest_recovered = False
        else:
            longest_recovered = False

    return {
        "max_underwater_days": int(max_days) if max_days > 0 else 0,
        "recovered": longest_recovered,
    }
