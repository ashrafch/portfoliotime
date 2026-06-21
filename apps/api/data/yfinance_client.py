"""
Connettore Yahoo Finance via yfinance.

R2: Tutte le serie restituite hanno source="yahoo_finance".
Timeout esplicito: 10s (R in AGENT.md).
"""

import asyncio
import pandas as pd
import yfinance as yf
from config import get_settings

settings = get_settings()


async def fetch_prices(
    tickers: list[str],
    date_from: str,
    date_to: str,
) -> pd.DataFrame:
    """Scarica i prezzi di chiusura giornalieri per i ticker richiesti.

    Args:
        tickers: Lista di ticker Yahoo Finance (es. ["SPY", "TLT", "BTC-USD"]).
        date_from: Data inizio ISO 8601 (es. "2007-01-01").
        date_to: Data fine ISO 8601 (es. "2009-12-31").

    Returns:
        DataFrame con colonne = ticker, indice = DatetimeIndex, valori = prezzi chiusura.
        Fonte: yahoo_finance.
    """
    loop = asyncio.get_event_loop()
    df = await loop.run_in_executor(None, _download_sync, tickers, date_from, date_to)
    return df


def _download_sync(tickers: list[str], date_from: str, date_to: str) -> pd.DataFrame:
    """Download sincrono (eseguito in thread pool per non bloccare l'event loop)."""
    raw = yf.download(
        tickers=tickers,
        start=date_from,
        end=date_to,
        auto_adjust=True,
        progress=False,
        timeout=int(settings.http_timeout_seconds),
    )

    if isinstance(raw.columns, pd.MultiIndex):
        # Più ticker: prendi solo la colonna "Close"
        if "Close" in raw.columns.get_level_values(0):
            df = raw["Close"]
        else:
            df = raw.iloc[:, :len(tickers)]
    else:
        # Singolo ticker
        df = raw[["Close"]].rename(columns={"Close": tickers[0]})

    return df.dropna(how="all")
