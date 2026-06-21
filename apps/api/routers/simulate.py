"""
Router /simulate — avvia e interroga simulazioni portafoglio.

Pattern (R5): POST /simulate → job_id → GET /simulate/{job_id}/result
Simulazioni > 2s vanno su Celery.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, field_validator
from datetime import date
from typing import Optional
import uuid

from engine.simulator import SimulationInput

router = APIRouter()


class SimulateRequest(BaseModel):
    # Profilo investitore
    eta: int = Field(..., ge=18, le=100, description="Età dell'investitore")

    # Parametri macro (regime corrente al momento della simulazione)
    tasso_fed: float = Field(..., ge=0.0, le=25.0)
    delta_tasso: float = Field(0.0, description="Variazione recente tasso FED in pp")
    btc_prezzo_corrente: float = Field(0.0, ge=0.0)
    btc_ath: float = Field(0.0, ge=0.0)
    is_post_halving: bool = False
    tasso_nominale: float = Field(..., ge=0.0, le=25.0)
    inflazione: float = Field(..., ge=-5.0, le=50.0)
    tassi_in_calo: bool = False
    qe_attivo: bool = False

    # Periodo storico
    date_from: str = Field(..., example="2007-01-01")
    date_to: str = Field(..., example="2009-12-31")
    benchmark_ticker: str = "SPY"

    @field_validator("date_from", "date_to")
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError("Formato data non valido. Usa ISO 8601: YYYY-MM-DD")
        return v


class SimulateJobResponse(BaseModel):
    job_id: str
    status: str = "queued"
    message: str


class SimulateResultResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None


# Storage in-memory per MVP (sostituire con Redis/DB in produzione)
_jobs: dict[str, dict] = {}


@router.post("", response_model=SimulateJobResponse, status_code=202)
async def start_simulation(request: SimulateRequest, background_tasks: BackgroundTasks):
    """Avvia una simulazione. Restituisce job_id per polling del risultato."""
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "queued", "result": None, "error": None}

    sim_input = SimulationInput(
        eta=request.eta,
        tasso_fed=request.tasso_fed,
        delta_tasso=request.delta_tasso,
        btc_prezzo_corrente=request.btc_prezzo_corrente,
        btc_ath=request.btc_ath,
        is_post_halving=request.is_post_halving,
        tasso_nominale=request.tasso_nominale,
        inflazione=request.inflazione,
        tassi_in_calo=request.tassi_in_calo,
        qe_attivo=request.qe_attivo,
        date_from=request.date_from,
        date_to=request.date_to,
        benchmark_ticker=request.benchmark_ticker,
    )

    background_tasks.add_task(_run_simulation_task, job_id, sim_input)

    return SimulateJobResponse(
        job_id=job_id,
        status="queued",
        message="Simulazione avviata. Usa GET /simulate/{job_id}/result per il risultato.",
    )


@router.get("/{job_id}/result", response_model=SimulateResultResponse)
async def get_simulation_result(job_id: str):
    """Recupera il risultato di una simulazione avviata."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job non trovato")
    job = _jobs[job_id]
    return SimulateResultResponse(
        job_id=job_id,
        status=job["status"],
        result=job.get("result"),
        error=job.get("error"),
    )


async def _run_simulation_task(job_id: str, sim_input: SimulationInput):
    """Task asincrono che esegue la simulazione e aggiorna _jobs."""
    import pandas as pd
    from data.yfinance_client import fetch_prices

    _jobs[job_id]["status"] = "running"
    try:
        tickers = ["SPY", "TLT", "GLD", "GSG"]
        if sim_input.is_post_halving and sim_input.btc_prezzo_corrente > 0:
            tickers.append("BTC-USD")

        prices = await fetch_prices(tickers, sim_input.date_from, sim_input.date_to)
        from engine.simulator import run_simulation
        result = run_simulation(sim_input, prices)

        _jobs[job_id]["status"] = "completed"
        _jobs[job_id]["result"] = {
            "allocazione": result.allocazione,
            "cagr": result.cagr,
            "max_drawdown": result.max_drawdown,
            "sharpe_ratio": result.sharpe_ratio,
            "annualized_volatility": result.annualized_volatility,
            "total_return": result.total_return,
            "benchmark_cagr": result.benchmark_cagr,
            "benchmark_max_drawdown": result.benchmark_max_drawdown,
            "sources": result.sources,
            "warnings": result.warnings,
        }
    except Exception as e:
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = str(e)
