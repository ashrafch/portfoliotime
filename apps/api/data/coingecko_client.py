"""
Connettore CoinGecko — prezzi Bitcoin storici.

R2: source="coingecko"
R6: Dati disponibili solo dal 2013-01-01. Validare sempre prima della chiamata.
Timeout: 10s.
"""

import httpx
import pandas as pd
from datetime import datetime, date
from config import get_settings

settings = get_settings()

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
CRYPTO_DATA_START = date.fromisoformat(settings.crypto_data_start)


async def fetch_btc_prices(date_from: str, date_to: str) -> pd.Series:
    """Scarica i prezzi giornalieri di Bitcoin in USD.

    R6: date_from non può essere prima del 2013-01-01.

    Args:
        date_from: Data inizio ISO 8601.
        date_to: Data fine ISO 8601.

    Returns:
        Serie pandas con indice DatetimeIndex e source="coingecko".
    """
    start = date.fromisoformat(date_from)
    if start < CRYPTO_DATA_START:
        raise ValueError(
            f"Dati crypto disponibili solo dal {CRYPTO_DATA_START}. "
            f"Richiesto: {date_from}"
        )

    from_ts = int(datetime.fromisoformat(date_from).timestamp())
    to_ts = int(datetime.fromisoformat(date_to).timestamp())

    headers = {}
    if settings.coingecko_api_key:
        headers["x-cg-demo-api-key"] = settings.coingecko_api_key

    async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
        response = await client.get(
            f"{COINGECKO_BASE}/coins/bitcoin/market_chart/range",
            params={"vs_currency": "usd", "from": from_ts, "to": to_ts},
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

    prices = data.get("prices", [])
    if not prices:
        return pd.Series(dtype=float, name="BTC-USD")

    df = pd.DataFrame(prices, columns=["timestamp_ms", "price"])
    df["date"] = pd.to_datetime(df["timestamp_ms"], unit="ms").dt.normalize()
    df = df.groupby("date")["price"].last()
    df.index = pd.DatetimeIndex(df.index)
    df.name = "BTC-USD"
    return df


async def fetch_btc_ath() -> float:
    """Restituisce l'All-Time High di Bitcoin in USD da CoinGecko."""
    headers = {}
    if settings.coingecko_api_key:
        headers["x-cg-demo-api-key"] = settings.coingecko_api_key

    async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
        response = await client.get(
            f"{COINGECKO_BASE}/coins/bitcoin",
            params={"localization": "false", "tickers": "false", "community_data": "false"},
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

    return float(data["market_data"]["ath"]["usd"])
