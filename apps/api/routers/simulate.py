"""
Router /simulate — esegue simulazioni, le persiste per-utente e ne consente lo storico.

Flusso: POST /simulate (autenticato) → esegue, salva, restituisce record completo.
        GET  /simulate          → storico dell'utente corrente
        GET  /simulate/{id}     → dettaglio (proprietario o super_admin)

R6: dati crypto validati >= 2013-01-01.
"""

import csv
import io
import math
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from database import get_db
from models.user import User, UserRole
from models.portfolio import SimulationRecord
from models.profile import InvestorProfile
from security import get_current_user
from engine.simulator import SimulationInput, run_simulation, compute_portfolio_returns
from engine.narrative import build_narrative
from engine.montecarlo import bootstrap_projection
from data import price_repository, fred_client
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
    # Allocazione personalizzata (opzionale): se presente sostituisce il Chameleon.
    # Chiavi: azioni, bitcoin, oro, materie_prime, obbligazioni. Somma normalizzata a 100.
    custom_allocation: Optional[dict[str, float]] = None
    # Importi (proiezione in denaro)
    initial_capital: float = Field(10000.0, ge=0.0, le=1_000_000_000.0)
    contribution: float = Field(0.0, ge=0.0, le=10_000_000.0)
    contribution_frequency: str = "none"  # none | monthly | quarterly

    @field_validator("contribution_frequency")
    @classmethod
    def _valid_freq(cls, v: str) -> str:
        if v not in ("none", "monthly", "quarterly"):
            raise ValueError("contribution_frequency deve essere none|monthly|quarterly")
        return v

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
        initial_capital=request.initial_capital,
        contribution=request.contribution,
        contribution_frequency=request.contribution_frequency,
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

        # Prezzi con cache TimescaleDB + fallback (affidabilità)
        # Se l'utente fornisce un'allocazione custom con BTC > 0, includi il ticker
        if request.custom_allocation and request.custom_allocation.get("bitcoin", 0) > 0:
            if "BTC-USD" not in tickers:
                tickers.append("BTC-USD")

        prices, cache_warnings, price_sources = await price_repository.get_prices(
            db, tickers, request.date_from, request.date_to
        )
        result = run_simulation(sim_input, prices, allocation_override=request.custom_allocation)

        # FRED: rendimento reale da inflazione storica reale, se configurato
        real_source = "calculated"
        if (
            fred_client.is_configured()
            and result.total_return is not None
            and not math.isnan(result.total_return)
        ):
            try:
                infl_total = await fred_client.period_inflation_total(
                    request.date_from, request.date_to
                )
                if infl_total is not None:
                    result.real_return = (1.0 + result.total_return) / (1.0 + infl_total) - 1.0
                    real_source = "fred"
            except Exception:  # noqa: BLE001
                pass

        # Narrativa personalizzata sul profilo dell'utente
        profile = (await db.execute(
            select(InvestorProfile).where(InvestorProfile.user_id == current_user.id)
        )).scalar_one_or_none()
        narrative = build_narrative(sim_input, result, profile=profile)

        sources = {**result.sources, **price_sources, "real_return": real_source}
        all_warnings = list(result.warnings) + cache_warnings

        result_dict = _clean_nan({
            "allocazione": result.allocazione,
            "allocation_source": result.allocation_source,
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
            "sortino_ratio": result.sortino_ratio,
            "calmar_ratio": result.calmar_ratio,
            "var_95": result.var_95,
            "cvar_95": result.cvar_95,
            "beta": result.beta,
            "max_underwater_days": result.max_underwater_days,
            "drawdown_recovered": result.drawdown_recovered,
            "money": result.money,
            "sources": sources,
            "warnings": all_warnings,
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


async def _load_owned_record(sim_id: str, current_user: User, db: AsyncSession) -> SimulationRecord:
    record = (await db.execute(
        select(SimulationRecord).where(SimulationRecord.id == sim_id)
    )).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Simulazione non trovata")
    if record.user_id != current_user.id and current_user.role != UserRole.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Accesso negato")
    return record


def _input_from_params(p: dict) -> SimulationInput:
    return SimulationInput(
        eta=p.get("eta", 40), tasso_fed=p.get("tasso_fed", 0.0), delta_tasso=p.get("delta_tasso", 0.0),
        btc_prezzo_corrente=p.get("btc_prezzo_corrente", 0.0), btc_ath=p.get("btc_ath", 0.0),
        is_post_halving=p.get("is_post_halving", False), tasso_nominale=p.get("tasso_nominale", 0.0),
        inflazione=p.get("inflazione", 0.0), tassi_in_calo=p.get("tassi_in_calo", False),
        qe_attivo=p.get("qe_attivo", False), date_from=p["date_from"], date_to=p["date_to"],
        benchmark_ticker=p.get("benchmark_ticker", "SPY"),
        initial_capital=p.get("initial_capital", 10000.0),
        contribution=p.get("contribution", 0.0),
        contribution_frequency=p.get("contribution_frequency", "none"),
    )


def _tickers_for(p: dict) -> list[str]:
    tickers = ["SPY", "TLT", "GLD", "GSG"]
    custom = p.get("custom_allocation") or {}
    if (p.get("is_post_halving") and p.get("btc_prezzo_corrente", 0) > 0) or custom.get("bitcoin", 0) > 0:
        tickers.append("BTC-USD")
    return tickers


@router.get("/{sim_id}/montecarlo")
async def montecarlo(
    sim_id: str,
    n_sims: int = 500,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Proiezione Monte Carlo (bootstrap) ricostruita dai dati della simulazione.

    È una distribuzione di scenari plausibili, NON una previsione (vedi disclaimer).
    """
    n_sims = max(100, min(n_sims, 2000))
    record = await _load_owned_record(sim_id, current_user, db)
    p = record.input_params or {}

    sim_input = _input_from_params(p)
    prices, _, _ = await price_repository.get_prices(
        db, _tickers_for(p), p["date_from"], p["date_to"]
    )
    returns = compute_portfolio_returns(sim_input, prices, p.get("custom_allocation"))
    if returns is None or len(returns) < 20:
        raise HTTPException(status_code=422, detail="Dati insufficienti per la proiezione Monte Carlo.")

    projection = bootstrap_projection(returns, n_sims=n_sims)
    if projection is None:
        raise HTTPException(status_code=422, detail="Proiezione non calcolabile.")
    return projection


@router.get("/{sim_id}/export.csv")
async def export_csv(
    sim_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Esporta la curva equity e le metriche principali in CSV."""
    record = await _load_owned_record(sim_id, current_user, db)
    res = record.result or {}

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["PortfolioTime — esportazione simulazione"])
    w.writerow(["periodo", record.label])
    w.writerow([])
    w.writerow(["metrica", "valore"])
    for key in ["total_return", "cagr", "max_drawdown", "annualized_volatility",
                "sharpe_ratio", "sortino_ratio", "calmar_ratio", "var_95", "cvar_95",
                "beta", "real_return", "benchmark_total_return", "max_underwater_days"]:
        if key in res:
            w.writerow([key, res.get(key)])
    money = res.get("money") or {}
    for mk in ["initial_capital", "total_invested", "final_value", "gain", "money_return"]:
        if mk in money:
            w.writerow([f"money_{mk}", money.get(mk)])
    w.writerow([])
    w.writerow(["data", "portafoglio_base100", "benchmark_base100"])
    for pt in res.get("equity_curve", []):
        w.writerow([pt.get("date"), pt.get("portfolio"), pt.get("benchmark", "")])

    buf.seek(0)
    filename = f"portfoliotime_{sim_id[:8]}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
