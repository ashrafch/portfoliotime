"""
Connettore FRED (Federal Reserve Economic Data).

R2: source="fred"
Serie utilizzate:
    DFF   — Federal Funds Rate (tasso FED giornaliero)
    CPIAUCSL — Consumer Price Index (inflazione mensile)
    GS10  — 10-Year Treasury Constant Maturity Rate
Timeout: 10s.
"""

import httpx
import pandas as pd
from config import get_settings

settings = get_settings()

FRED_BASE = "https://api.stlouisfed.org/fred"


async def fetch_series(series_id: str, date_from: str, date_to: str) -> pd.Series:
    """Scarica una serie FRED per il periodo richiesto.

    Args:
        series_id: ID FRED (es. "DFF", "CPIAUCSL", "GS10").
        date_from: Data inizio ISO 8601.
        date_to: Data fine ISO 8601.

    Returns:
        Serie pandas con indice DatetimeIndex e valori float.
    """
    async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
        response = await client.get(
            f"{FRED_BASE}/series/observations",
            params={
                "series_id": series_id,
                "observation_start": date_from,
                "observation_end": date_to,
                "api_key": settings.fred_api_key,
                "file_type": "json",
            },
        )
        response.raise_for_status()
        data = response.json()

    observations = data.get("observations", [])
    if not observations:
        return pd.Series(dtype=float, name=series_id)

    df = pd.DataFrame(observations)[["date", "value"]]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.set_index("date")["value"].dropna()
    df.name = series_id
    return df


async def fetch_fed_rate(date_from: str, date_to: str) -> pd.Series:
    """Tasso FED (DFF) per il periodo."""
    return await fetch_series("DFF", date_from, date_to)


async def fetch_cpi(date_from: str, date_to: str) -> pd.Series:
    """CPI mensile (CPIAUCSL) per il periodo."""
    return await fetch_series("CPIAUCSL", date_from, date_to)


async def fetch_10y_treasury(date_from: str, date_to: str) -> pd.Series:
    """Treasury 10 anni (GS10) per il periodo."""
    return await fetch_series("GS10", date_from, date_to)


def is_configured() -> bool:
    """True se è impostata una FRED_API_KEY."""
    return bool(settings.fred_api_key and settings.fred_api_key not in ("", "INSERISCI_QUI"))


async def period_inflation_total(date_from: str, date_to: str) -> float | None:
    """Inflazione cumulata reale sul periodo, da CPIAUCSL.

    Returns: variazione percentuale del CPI tra inizio e fine periodo (decimale),
    es. 0.08 = +8%. None se i dati non sono disponibili.
    """
    cpi = await fetch_cpi(date_from, date_to)
    if cpi is None or len(cpi) < 2:
        return None
    start, end = float(cpi.iloc[0]), float(cpi.iloc[-1])
    if start <= 0:
        return None
    return end / start - 1.0


async def macro_snapshot(date_from: str, date_to: str) -> dict | None:
    """Snapshot macro reale per pre-compilare la simulazione.

    Restituisce tasso_fed (inizio periodo), delta_tasso (variazione nel periodo),
    inflazione (CPI YoY annualizzato sul periodo) e tasso_nominale (GS10).
    None se FRED non è configurato o i dati mancano.
    """
    if not is_configured():
        return None

    fed = await fetch_fed_rate(date_from, date_to)
    cpi = await fetch_cpi(date_from, date_to)
    gs10 = await fetch_10y_treasury(date_from, date_to)

    if fed is None or len(fed) == 0:
        return None

    tasso_fed = round(float(fed.iloc[0]), 2)
    delta_tasso = round(float(fed.iloc[-1] - fed.iloc[0]), 2)

    # Inflazione annualizzata sul periodo
    inflazione = 3.0
    if cpi is not None and len(cpi) >= 2:
        years = max((cpi.index[-1] - cpi.index[0]).days / 365.25, 1e-9)
        total = float(cpi.iloc[-1]) / float(cpi.iloc[0]) - 1.0
        inflazione = round(((1 + total) ** (1 / years) - 1) * 100, 2)

    tasso_nominale = tasso_fed
    if gs10 is not None and len(gs10) > 0:
        tasso_nominale = round(float(gs10.iloc[0]), 2)

    return {
        "tasso_fed": tasso_fed,
        "delta_tasso": delta_tasso,
        "tasso_nominale": tasso_nominale,
        "inflazione": inflazione,
        "tassi_in_calo": delta_tasso < 0,
        "source": "fred",
    }
