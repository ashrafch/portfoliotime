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
