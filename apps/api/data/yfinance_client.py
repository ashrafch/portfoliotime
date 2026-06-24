"""
Connettore Yahoo Finance via yfinance.

R2: Tutte le serie restituite hanno source="yahoo_finance".
Copre azioni/ETF e crypto (BTC-USD), evitando la dipendenza da chiavi esterne.
Timeout esplicito + retry.
"""

import asyncio
import pandas as pd
import yfinance as yf
from config import get_settings

settings = get_settings()

# Mapping asset class Chameleon → ticker Yahoo Finance
ASSET_TICKERS: dict[str, str] = {
    "azioni": "SPY",        # S&P 500
    "obbligazioni": "TLT",  # Treasury 20+ anni
    "oro": "GLD",           # Oro
    "materie_prime": "GSG", # Commodity broad
    "bitcoin": "BTC-USD",   # Bitcoin
}


async def fetch_prices(tickers: list[str], date_from: str, date_to: str) -> pd.DataFrame:
    """Scarica i prezzi di chiusura giornalieri per i ticker richiesti.

    Returns:
        DataFrame con colonne = ticker, indice = DatetimeIndex, valori = prezzi chiusura.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _download_with_retry, tickers, date_from, date_to)


def _download_with_retry(tickers: list[str], date_from: str, date_to: str, attempts: int = 3) -> pd.DataFrame:
    last_err: Exception | None = None
    for i in range(attempts):
        try:
            df = _download_sync(tickers, date_from, date_to)
            if not df.empty:
                return df
        except Exception as e:  # noqa: BLE001 — yfinance può sollevare errori di rete vari
            last_err = e
    if last_err is not None:
        raise RuntimeError(f"Download prezzi fallito dopo {attempts} tentativi: {last_err}")
    return pd.DataFrame()


def _download_sync(tickers: list[str], date_from: str, date_to: str) -> pd.DataFrame:
    raw = yf.download(
        tickers=tickers,
        start=date_from,
        end=date_to,
        auto_adjust=True,
        progress=False,
        timeout=int(settings.http_timeout_seconds),
    )

    if raw is None or len(raw) == 0:
        return pd.DataFrame()

    if isinstance(raw.columns, pd.MultiIndex):
        if "Close" in raw.columns.get_level_values(0):
            df = raw["Close"].copy()
        else:
            df = raw.iloc[:, : len(tickers)].copy()
    else:
        # Singolo ticker: yfinance restituisce colonne semplici
        col = "Close" if "Close" in raw.columns else raw.columns[0]
        df = raw[[col]].rename(columns={col: tickers[0]})

    return df.dropna(how="all")
