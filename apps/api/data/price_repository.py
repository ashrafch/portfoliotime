"""
Repository prezzi con cache in TimescaleDB.

Strategia di affidabilità:
1. Per ogni ticker, verifica se la cache copre il periodo richiesto.
2. Per i ticker non coperti, scarica da Yahoo Finance e salva in cache.
3. Se il download fallisce ma esiste cache parziale → usa la cache (degradazione
   graziosa) e aggiunge un warning.
4. Se non c'è né cache né download → solleva errore esplicito.

Questo elimina yfinance come singolo punto di rottura: dopo il primo download,
le simulazioni sullo stesso periodo sono servite dal DB (veloci e resilienti).
"""

from __future__ import annotations

from datetime import date, timedelta
import pandas as pd
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.price_cache import PriceCache
from data.yfinance_client import fetch_prices

# Tolleranza ai bordi: i mercati sono chiusi nei weekend/festivi, quindi non
# pretendiamo copertura esatta agli estremi del range.
_EDGE_TOLERANCE_DAYS = 6
_MIN_COVERAGE_RATIO = 0.85


async def get_prices(
    db: AsyncSession,
    tickers: list[str],
    date_from: str,
    date_to: str,
) -> tuple[pd.DataFrame, list[str], dict[str, str]]:
    """Restituisce (DataFrame prezzi, warnings, sources_per_ticker).

    Il DataFrame ha colonne = ticker, indice = DatetimeIndex, valori = close.
    sources_per_ticker mappa ticker → "cache" | "yahoo_finance".
    """
    warnings: list[str] = []
    sources: dict[str, str] = {}
    d_from = date.fromisoformat(date_from)
    d_to = date.fromisoformat(date_to)

    series_by_ticker: dict[str, pd.Series] = {}

    for ticker in tickers:
        cached = await _read_cache(db, ticker, d_from, d_to)

        if _is_covered(cached, d_from, d_to):
            series_by_ticker[ticker] = cached
            sources[ticker] = "cache"
            continue

        # Cache insufficiente → prova il download
        try:
            downloaded = await fetch_prices([ticker], date_from, date_to)
            col = _extract_column(downloaded, ticker)
            if col is not None and not col.empty:
                await _write_cache(db, ticker, col)
                series_by_ticker[ticker] = col
                sources[ticker] = "yahoo_finance"
                continue
            raise RuntimeError("download vuoto")
        except Exception as e:  # noqa: BLE001
            # Fallback: usa la cache parziale se disponibile
            if cached is not None and not cached.empty:
                series_by_ticker[ticker] = cached
                sources[ticker] = "cache"
                warnings.append(
                    f"{ticker}: download non riuscito ({e}); uso i dati in cache (parziali)."
                )
            else:
                warnings.append(f"{ticker}: nessun dato disponibile (download fallito, cache vuota).")

    if not series_by_ticker:
        return pd.DataFrame(), warnings, sources

    df = pd.DataFrame(series_by_ticker).sort_index()
    return df, warnings, sources


async def _read_cache(db: AsyncSession, ticker: str, d_from: date, d_to: date) -> pd.Series:
    rows = (await db.execute(
        select(PriceCache.date, PriceCache.close_price)
        .where(PriceCache.ticker == ticker)
        .where(PriceCache.date >= d_from)
        .where(PriceCache.date <= d_to)
        .order_by(PriceCache.date)
    )).all()
    if not rows:
        return pd.Series(dtype=float, name=ticker)
    idx = pd.DatetimeIndex([r[0] for r in rows])
    return pd.Series([r[1] for r in rows], index=idx, name=ticker)


def _is_covered(series: pd.Series, d_from: date, d_to: date) -> bool:
    """Verifica euristica che la cache copra il periodo richiesto."""
    if series is None or len(series) < 2:
        return False
    cache_start = series.index[0].date()
    cache_end = series.index[-1].date()

    if (cache_start - d_from).days > _EDGE_TOLERANCE_DAYS:
        return False
    if (d_to - cache_end).days > _EDGE_TOLERANCE_DAYS:
        return False

    requested_span = max((d_to - d_from).days, 1)
    covered_span = (cache_end - cache_start).days
    return covered_span / requested_span >= _MIN_COVERAGE_RATIO


async def _write_cache(db: AsyncSession, ticker: str, series: pd.Series) -> None:
    """Sostituisce le righe in cache per il ticker nel range coperto dalla serie."""
    if series.empty:
        return
    d_from = series.index[0].date()
    d_to = series.index[-1].date()

    # delete+insert: portabile (no upsert specifico per dialetto) e idempotente
    await db.execute(
        delete(PriceCache)
        .where(PriceCache.ticker == ticker)
        .where(PriceCache.date >= d_from)
        .where(PriceCache.date <= d_to)
    )
    db.add_all([
        PriceCache(
            ticker=ticker,
            date=ts.date() if hasattr(ts, "date") else ts,
            close_price=float(val),
            source="yahoo_finance",
        )
        for ts, val in series.items()
        if pd.notna(val)
    ])
    await db.commit()


def _extract_column(df: pd.DataFrame, ticker: str) -> pd.Series | None:
    if df is None or df.empty:
        return None
    if ticker in df.columns:
        return df[ticker].dropna()
    # singolo ticker: yfinance può restituire una colonna sola con nome diverso
    if df.shape[1] == 1:
        s = df.iloc[:, 0].dropna()
        s.name = ticker
        return s
    return None
