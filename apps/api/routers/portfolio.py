"""Router /portfolio — allocazione Chameleon, stress test, goal planning, consigliata."""

import math
from datetime import date, timedelta, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models.user import User
from models.profile import InvestorProfile
from security import get_current_user
from engine.metrics import chameleon_portafoglio
from engine.simulator import SimulationInput, run_simulation, compute_portfolio_returns, normalize_allocation
from engine import planning
from data import price_repository, fred_client

router = APIRouter()

ASSET_KEYS = ["azioni", "obbligazioni", "oro", "materie_prime", "bitcoin"]
ASSET_TO_TICKER = {
    "azioni": "SPY", "obbligazioni": "TLT", "oro": "GLD",
    "materie_prime": "GSG", "bitcoin": "BTC-USD",
}


def _clean(obj):
    if isinstance(obj, float):
        return None if math.isnan(obj) else obj
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean(v) for v in obj]
    return obj


def _tickers_for_weights(weights: dict[str, float]) -> list[str]:
    return [ASSET_TO_TICKER[k] for k in ASSET_KEYS if weights.get(k, 0) > 0]


class AllocationRequest(BaseModel):
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


class AllocationResponse(BaseModel):
    allocazione: dict[str, float]
    somma_totale: float
    note: list[str]


@router.post("/allocation", response_model=AllocationResponse)
async def calc_allocation(request: AllocationRequest):
    """Calcola l'allocazione Chameleon per il profilo fornito.

    Questo endpoint è sincrono e < 1ms — nessun dato esterno richiesto.
    Utile per il preview live nel frontend mentre l'utente modifica i parametri.
    """
    allocazione = chameleon_portafoglio(
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
    )

    somma = sum(allocazione.values())
    note: list[str] = []

    if request.qe_attivo:
        note.append("QE attivo: obbligazioni escluse dal portafoglio.")
    if somma < 99.0:
        note.append(f"Somma allocazioni: {somma:.1f}% — la liquidità residua rimane in cash/money market.")
    if not request.is_post_halving:
        note.append("Bitcoin non incluso: non siamo in periodo post-halving.")

    return AllocationResponse(allocazione=allocazione, somma_totale=round(somma, 2), note=note)


# ─────────────────────────────────────────────────────────────────────────────
# Feature 1 — Stress test del portafoglio reale
# ─────────────────────────────────────────────────────────────────────────────

STRESS_SCENARIOS = [
    {"label": "Grande Recessione 2008", "date_from": "2007-10-09", "date_to": "2009-03-09"},
    {"label": "COVID Crash 2020", "date_from": "2020-02-19", "date_to": "2020-03-23"},
    {"label": "Inflazione / Bear 2022", "date_from": "2022-01-01", "date_to": "2022-12-31"},
    {"label": "Dot-com 2000-2002", "date_from": "2000-03-10", "date_to": "2002-10-09"},
]


class StressTestRequest(BaseModel):
    holdings: dict[str, float] = Field(..., description="Importo per asset class, es. {azioni: 5000, ...}")


@router.post("/stress-test")
async def stress_test(
    request: StressTestRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stress-testa il portafoglio posseduto contro alcune crisi storiche reali."""
    holdings = {k: max(0.0, float(request.holdings.get(k, 0.0))) for k in ASSET_KEYS}
    total = sum(holdings.values())
    if total <= 0:
        raise HTTPException(status_code=422, detail="Inserisci almeno un importo positivo.")

    weights = {k: holdings[k] / total * 100.0 for k in ASSET_KEYS}
    tickers = _tickers_for_weights(weights)

    results = []
    for sc in STRESS_SCENARIOS:
        prices, warns, _ = await price_repository.get_prices(db, tickers, sc["date_from"], sc["date_to"])
        sim_input = SimulationInput(
            eta=40, tasso_fed=0, delta_tasso=0, btc_prezzo_corrente=0, btc_ath=0,
            is_post_halving=False, tasso_nominale=0, inflazione=0, tassi_in_calo=False,
            qe_attivo=False, date_from=sc["date_from"], date_to=sc["date_to"],
            initial_capital=total,
        )
        res = run_simulation(sim_input, prices, allocation_override=weights)
        results.append(_clean({
            "label": sc["label"],
            "date_from": sc["date_from"], "date_to": sc["date_to"],
            "total_return": res.total_return,
            "max_drawdown": res.max_drawdown,
            "final_value": (res.money or {}).get("final_value"),
            "warnings": list(res.warnings) + warns,
        }))

    return {
        "total_value": round(total, 2),
        "weights": {k: round(v, 2) for k, v in weights.items()},
        "scenarios": results,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Feature 2 — Pianificazione per obiettivi (goal-based)
# ─────────────────────────────────────────────────────────────────────────────

class GoalPlanRequest(BaseModel):
    target: float = Field(..., gt=0)
    horizon_years: int = Field(..., ge=1, le=50)
    initial_capital: float = Field(0.0, ge=0)
    monthly_contribution: float = Field(0.0, ge=0)
    risk_profile: Optional[str] = None  # conservativo | bilanciato | aggressivo


@router.post("/goal-plan")
async def goal_plan(
    request: GoalPlanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stima la probabilità di raggiungere un obiettivo e il versamento necessario."""
    # Profilo di rischio: dalla richiesta o dal profilo utente
    risk = request.risk_profile
    if risk not in planning.REFERENCE_ALLOCATIONS:
        profile = (await db.execute(
            select(InvestorProfile).where(InvestorProfile.user_id == current_user.id)
        )).scalar_one_or_none()
        risk = (profile.risk_profile if profile else "bilanciato")
        if risk not in planning.REFERENCE_ALLOCATIONS:
            risk = "bilanciato"

    allocation = planning.REFERENCE_ALLOCATIONS[risk]
    ref_from, ref_to = planning.REFERENCE_PERIOD

    sim_input = SimulationInput(
        eta=40, tasso_fed=0, delta_tasso=0, btc_prezzo_corrente=0, btc_ath=0,
        is_post_halving=False, tasso_nominale=0, inflazione=0, tassi_in_calo=False,
        qe_attivo=False, date_from=ref_from, date_to=ref_to,
    )
    tickers = _tickers_for_weights(allocation)
    prices, _, _ = await price_repository.get_prices(db, tickers, ref_from, ref_to)
    returns = compute_portfolio_returns(sim_input, prices, allocation_override=allocation)
    if returns is None or len(returns) < 60:
        raise HTTPException(status_code=422, detail="Dati di riferimento insufficienti.")

    projection = planning.project_goal(
        returns, request.horizon_years, request.initial_capital,
        request.monthly_contribution, request.target,
    )
    required = planning.required_monthly_contribution(
        returns, request.horizon_years, request.initial_capital, request.target,
    )
    stats = planning.reference_stats(returns)

    return _clean({
        "risk_profile": risk,
        "allocation": allocation,
        "reference_period": {"from": ref_from, "to": ref_to},
        "reference_stats": stats,
        "projection": projection,
        "required_monthly_contribution": required,
        "disclaimer": (
            "Proiezione basata sui rendimenti storici reali del periodo di riferimento "
            "tramite bootstrap. Non è una garanzia: i risultati futuri possono differire."
        ),
    })


# ─────────────────────────────────────────────────────────────────────────────
# Feature 3 — Allocazione consigliata "oggi" + rilevazione cambiamenti
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/recommended")
async def recommended(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Allocazione Chameleon sulla situazione macro attuale, con i cambiamenti
    rispetto all'ultimo calcolo salvato.

    Fonte macro: FRED (se configurato) altrimenti le assunzioni del profilo utente.
    """
    profile = (await db.execute(
        select(InvestorProfile).where(InvestorProfile.user_id == current_user.id)
    )).scalar_one_or_none()
    if profile is None:
        profile = InvestorProfile(user_id=current_user.id)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

    source = "profilo"
    tasso_fed = profile.default_tasso_fed
    inflazione = profile.default_inflazione
    tasso_nominale = profile.default_tasso_fed
    delta_tasso = 0.0
    tassi_in_calo = False

    if fred_client.is_configured():
        try:
            today = date.today()
            snap = await fred_client.macro_snapshot(
                (today - timedelta(days=400)).isoformat(), today.isoformat()
            )
            if snap:
                tasso_fed = snap["tasso_fed"]
                inflazione = snap["inflazione"]
                tasso_nominale = snap["tasso_nominale"]
                delta_tasso = snap["delta_tasso"]
                tassi_in_calo = snap["tassi_in_calo"]
                source = "fred"
        except Exception:  # noqa: BLE001
            pass

    allocazione = chameleon_portafoglio(
        eta=profile.eta, tasso_fed=tasso_fed, delta_tasso=delta_tasso,
        btc_prezzo_corrente=0, btc_ath=0, is_post_halving=False,
        tasso_nominale=tasso_nominale, inflazione=inflazione,
        tassi_in_calo=tassi_in_calo, qe_attivo=False,
    )

    # Differenze rispetto all'ultimo snapshot salvato
    previous = profile.last_recommended or None
    changes = []
    if previous:
        for k in ASSET_KEYS:
            old = float(previous.get(k, 0))
            new = float(allocazione.get(k, 0))
            if abs(new - old) >= 0.5:
                changes.append({"asset": k, "da": round(old, 1), "a": round(new, 1)})

    previous_at = profile.last_recommended_at.isoformat() if profile.last_recommended_at else None

    # Salva il nuovo snapshot
    profile.last_recommended = allocazione
    profile.last_recommended_at = datetime.now(timezone.utc)
    await db.commit()

    return {
        "allocazione": allocazione,
        "source": source,
        "macro_used": {
            "tasso_fed": tasso_fed, "inflazione": inflazione,
            "tasso_nominale": tasso_nominale, "delta_tasso": delta_tasso,
            "tassi_in_calo": tassi_in_calo,
        },
        "changes": changes,
        "previous_at": previous_at,
        "note": (
            "Bitcoin escluso (richiede stato post-halving) e QE non attivo per default. "
            "Fonte macro: " + ("FRED (dati reali)" if source == "fred"
                               else "assunzioni del tuo profilo")
        ),
    }
