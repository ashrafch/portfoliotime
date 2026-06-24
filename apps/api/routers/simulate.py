"""
Router /simulate — esegue simulazioni, le persiste per-utente e ne consente lo storico.

Flusso: POST /simulate (autenticato) → esegue, salva, restituisce record completo.
        GET  /simulate          → storico dell'utente corrente
        GET  /simulate/{id}     → dettaglio (proprietario o super_admin)

R6: dati crypto validati >= 2013-01-01.
"""

import math
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from database import get_db
from models.user import User, UserRole
from models.portfolio import SimulationRecord
from security import get_current_user
from engine.simulator import SimulationInput, run_simulation
from engine.narrative import build_narrative
from data.yfinance_client import fetch_prices, ASSET_TICKERS
from config import get_settings

router = APIRouter()
settings = get_settings()

CRYPTO_START = date.fromisoformat(settings.crypto_data_start)


class SimulateRequest(BaseModel):
    eta: int = Field(..., ge=18, le=100)
    tasso_fed: float = Field(..., ge=0.0, le=25.0)
    delta_tasso: float = Field(0.0)
    btc_prezzo_corrente: float = Field(0.0, ge=0.0)
    btc_ath: float = Field(0.0, ge=0.0)
    is_post_halving: bool = False
    tasso_nominale: float = Field(..., ge=0.0, le=25.0)
    inflazione: float = Field(..., ge=-5.0, le=50.0)
    tassi_in_calo: bool = False
    qe_attivo: bool = False
    date_from: str = Field(..., examples=["2007-01-01"])
    date_to: str = Field(..., examples=["2009-12-31"])
    benchmark_ticker: str = "SPY"

    @field_validator("date_from", "date_to")
    @classmethod
    def _valid_date(cls, v: str) -> str:
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError("Formato data non valido. Usa YYYY-MM-DD")
        return v


class SimulationSummary(BaseModel):
    id: str
    label: str
    status: str
    created_at: Optional[str] = None
    total_return: Optional[float] = None
    cagr: Optional[float] = None

    class Config:
        from_attributes = True


def _clean_nan(obj):
    """Converte i NaN in None così il JSON è valido."""
    if isinstance(obj, float):
        return None if math.isnan(obj) else obj
    if isinstance(obj, dict):
        return {k: _clean_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean_nan(v) for v in obj]
    return obj


@router.post("", status_code=201)
async def create_simulation(
    request: SimulateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Esegue una simulazione, la salva nello storico dell'utente e restituisce il record."""
    # R6: validazione crypto
    if request.is_post_halving and request.btc_prezzo_corrente > 0:
        if date.fromisoformat(request.date_from) < CRYPTO_START:
            raise HTTPException(
                status_code=422,
                detail=f"Dati crypto disponibili solo dal {CRYPTO_START.isoformat()}.",
            )

    sim_input = SimulationInput(
        eta=request.eta, tasso_fed=request.tasso_fed, delta_tasso=request.delta_tasso,
        btc_prezzo_corrente=request.btc_prezzo_corrente, btc_ath=request.btc_ath,
        is_post_halving=request.is_post_halving, tasso_nominale=request.tasso_nominale,
        inflazione=request.inflazione, tassi_in_calo=request.tassi_in_calo,
        qe_attivo=request.qe_attivo, date_from=request.date_from, date_to=request.date_to,
        benchmark_ticker=request.benchmark_ticker,
    )

    label = f"{request.date_from} → {request.date_to}"
    record = SimulationRecord(
        user_id=current_user.id,
        label=label,
        input_params=request.model_dump(),
        status="completed",
    )

    try:
        tickers = ["SPY", "TLT", "GLD", "GSG"]
        if request.is_post_halving and request.btc_prezzo_corrente > 0:
            tickers.append("BTC-USD")

        prices = await fetch_prices(tickers, request.date_from, request.date_to)
        result = run_simulation(sim_input, prices)
        narrative = build_narrative(sim_input, result)

        result_dict = _clean_nan({
            "allocazione": result.allocazione,
            "cagr": result.cagr,
            "max_drawdown": result.max_drawdown,
            "sharpe_ratio": result.sharpe_ratio,
            "annualized_volatility": result.annualized_volatility,
            "real_return": result.real_return,
            "total_return": result.total_return,
            "benchmark_cagr": result.benchmark_cagr,
            "benchmark_max_drawdown": result.benchmark_max_drawdown,
            "benchmark_total_return": result.benchmark_total_return,
            "equity_curve": result.equity_curve,
            "sources": result.sources,
            "warnings": result.warnings,
        })
        record.result = result_dict
        record.narrative = narrative
    except Exception as e:  # noqa: BLE001
        record.status = "failed"
        record.error = str(e)

    db.add(record)
    await db.commit()
    await db.refresh(record)

    return {
        "id": record.id,
        "status": record.status,
        "label": record.label,
        "result": record.result,
        "narrative": record.narrative,
        "error": record.error,
    }


@router.get("", response_model=list[SimulationSummary])
async def list_my_simulations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Storico simulazioni dell'utente corrente (più recenti prima)."""
    result = await db.execute(
        select(SimulationRecord)
        .where(SimulationRecord.user_id == current_user.id)
        .order_by(desc(SimulationRecord.created_at))
    )
    records = result.scalars().all()
    return [_to_summary(r) for r in records]


@router.get("/{sim_id}")
async def get_simulation(
    sim_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dettaglio di una simulazione. Accesso: proprietario o super_admin."""
    result = await db.execute(select(SimulationRecord).where(SimulationRecord.id == sim_id))
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Simulazione non trovata")
    if record.user_id != current_user.id and current_user.role != UserRole.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Accesso negato")

    return {
        "id": record.id,
        "status": record.status,
        "label": record.label,
        "input_params": record.input_params,
        "result": record.result,
        "narrative": record.narrative,
        "error": record.error,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


def _to_summary(r: SimulationRecord) -> SimulationSummary:
    res = r.result or {}
    return SimulationSummary(
        id=r.id,
        label=r.label,
        status=r.status,
        created_at=r.created_at.isoformat() if r.created_at else None,
        total_return=res.get("total_return"),
        cagr=res.get("cagr"),
    )
