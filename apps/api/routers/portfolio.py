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
import recommendation

# Proxy reali usati dal motore (trasparenza: l'utente sa "cosa" sono le categorie)
INSTRUMENT_PROXY = {
    "azioni": "Azioni globali — proxy: S&P 500 (ETF SPY)",
    "obbligazioni": "Obbligazioni governative — proxy: Treasury USA 20+ anni (ETF TLT)",
    "oro": "Oro — proxy: ETF oro (GLD)",
    "materie_prime": "Materie prime — proxy: ETF commodity (GSG)",
    "bitcoin": "Bitcoin (BTC-USD)",
}

# Esempi REALI di strumenti UCITS (adatti a un investitore in UE) allineati alla
# categoria simulata. NON sono consigli personalizzati: vedi instruments_note.
INSTRUMENT_EXAMPLES = {
    "azioni": [
        {"name": "iShares Core S&P 500 UCITS", "ticker": "CSPX", "type": "ETF azionario USA"},
        {"name": "Vanguard FTSE All-World UCITS", "ticker": "VWCE", "type": "ETF azionario globale"},
    ],
    "obbligazioni": [
        {"name": "iShares $ Treasury Bond 20+yr UCITS", "ticker": "IDTL", "type": "ETF Treasury USA lunghe"},
        {"name": "iShares Core Global Aggregate Bond UCITS", "ticker": "AGGH", "type": "ETF obbligazionario globale"},
    ],
    "oro": [
        {"name": "iShares Physical Gold ETC", "ticker": "SGLN", "type": "ETC oro fisico"},
        {"name": "Invesco Physical Gold ETC", "ticker": "SGLD", "type": "ETC oro fisico"},
    ],
    "materie_prime": [
        {"name": "Invesco Bloomberg Commodity UCITS", "ticker": "CMOD", "type": "ETF materie prime"},
        {"name": "iShares Diversified Commodity Swap UCITS", "ticker": "ICOM", "type": "ETF materie prime"},
    ],
    "bitcoin": [
        {"name": "ETP Bitcoin fisico (es. CoinShares, 21Shares)", "ticker": "—", "type": "ETP cripto (in UE non esistono ETF)"},
    ],
}

INSTRUMENTS_NOTE = (
    "Esempi di strumenti UCITS adatti a un investitore in UE, allineati alla categoria "
    "simulata (stesso indice/asset). NON sono consigli personalizzati: verifica costi "
    "annui (TER), ISIN, valuta, politica dei dividendi (accumulazione/distribuzione) e "
    "disponibilità sul tuo broker. In caso di dubbio rivolgiti a un consulente."
)

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
    profile = await _get_or_create_profile(db, current_user.id)

    rec = await recommendation.current_recommendation(profile)
    allocazione = rec["allocazione"]
    source = rec["source"]

    changes = recommendation.diff_allocations(profile.last_recommended, allocazione)
    previous_at = profile.last_recommended_at.isoformat() if profile.last_recommended_at else None

    # Salva il nuovo snapshot (questo "segna come visto" per le notifiche)
    profile.last_recommended = allocazione
    profile.last_recommended_at = datetime.now(timezone.utc)
    await db.commit()

    return {
        "allocazione": allocazione,
        "source": source,
        "macro_used": rec["macro_used"],
        "changes": changes,
        "previous_at": previous_at,
        "note": (
            "Bitcoin escluso (richiede stato post-halving) e QE non attivo per default. "
            "Fonte macro: " + ("FRED (dati reali)" if source == "fred"
                               else "assunzioni del tuo profilo")
        ),
    }


@router.get("/allocation-presets")
async def allocation_presets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Allocazioni pronte da caricare in una simulazione (senza effetti collaterali):
    - strategica: il mix legato al profilo di rischio dell'utente
    - consigliata: l'allocazione Chameleon sulla macro attuale
    """
    profile = await _get_or_create_profile(db, current_user.id)
    risk = profile.risk_profile if profile.risk_profile in planning.REFERENCE_ALLOCATIONS else "bilanciato"
    rec = await recommendation.current_recommendation(profile)
    return {
        "strategic": planning.REFERENCE_ALLOCATIONS[risk],
        "strategic_risk": risk,
        "recommended": rec["allocazione"],
        "recommended_source": rec["source"],
    }


async def _get_or_create_profile(db: AsyncSession, user_id: str) -> InvestorProfile:
    profile = (await db.execute(
        select(InvestorProfile).where(InvestorProfile.user_id == user_id)
    )).scalar_one_or_none()
    if profile is None:
        profile = InvestorProfile(user_id=user_id)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return profile


# ─────────────────────────────────────────────────────────────────────────────
# Piano consigliato unico (sintesi: cosa investire + probabilità di successo)
# ─────────────────────────────────────────────────────────────────────────────

class AdviceRequest(BaseModel):
    initial_capital: float = Field(0.0, ge=0)
    monthly_contribution: float = Field(0.0, ge=0)
    horizon_years: int = Field(..., ge=1, le=50)
    target: Optional[float] = Field(None, gt=0)
    risk_profile: Optional[str] = None
    basis: str = "strategic"  # strategic (in base al rischio) | chameleon (macro oggi)
    glide_path: bool = False   # riduci gradualmente il rischio avvicinandoti all'obiettivo


@router.post("/advice")
async def advice(
    request: AdviceRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Piano consigliato unico: una sola allocazione concreta (importi in valuta) con
    la sua probabilità di raggiungere l'obiettivo, su dati storici reali.
    """
    profile = await _get_or_create_profile(db, current_user.id)

    risk = request.risk_profile if request.risk_profile in planning.REFERENCE_ALLOCATIONS else profile.risk_profile
    if risk not in planning.REFERENCE_ALLOCATIONS:
        risk = "bilanciato"

    # Allocazione consigliata: strategica (in base al rischio) o tattica (Chameleon oggi)
    if request.basis == "chameleon":
        rec = await recommendation.current_recommendation(profile)
        allocation = rec["allocazione"]
        alloc_source = rec["source"]  # fred | profilo
    else:
        allocation = planning.REFERENCE_ALLOCATIONS[risk]
        alloc_source = "reference"

    ref_from, ref_to = planning.REFERENCE_PERIOD
    sim_input = SimulationInput(
        eta=profile.eta, tasso_fed=0, delta_tasso=0, btc_prezzo_corrente=0, btc_ath=0,
        is_post_halving=False, tasso_nominale=0, inflazione=0, tassi_in_calo=False,
        qe_attivo=False, date_from=ref_from, date_to=ref_to,
    )
    # Glide path: l'allocazione finale (più prudente) è la "conservativa"
    end_alloc = planning.REFERENCE_ALLOCATIONS["conservativo"] if request.glide_path else None

    tickers = set(_tickers_for_weights(allocation))
    if end_alloc:
        tickers |= set(_tickers_for_weights(end_alloc))
    prices, _, _ = await price_repository.get_prices(db, sorted(tickers), ref_from, ref_to)

    returns = compute_portfolio_returns(sim_input, prices, allocation_override=allocation)
    if returns is None or len(returns) < 60:
        raise HTTPException(status_code=422, detail="Dati di riferimento insufficienti.")
    returns_end = compute_portfolio_returns(sim_input, prices, allocation_override=end_alloc) if end_alloc else None

    # Ripartizione concreta per categoria: vale sia per il capitale iniziale sia
    # per OGNI versamento mensile (stesse percentuali). Così è utile anche con
    # capitale iniziale = 0 (piano di solo accumulo).
    breakdown = []
    for k in ASSET_KEYS:
        w = float(allocation.get(k, 0))
        if w <= 0:
            continue
        breakdown.append({
            "asset": k,
            "instrument": INSTRUMENT_PROXY[k],
            "examples": INSTRUMENT_EXAMPLES.get(k, []),
            "weight_pct": round(w, 1),
            "amount_now": round(request.initial_capital * w / 100.0, 2),       # compat
            "amount_initial": round(request.initial_capital * w / 100.0, 2),
            "amount_monthly": round(request.monthly_contribution * w / 100.0, 2),
        })

    projection = planning.project_goal(
        returns, request.horizon_years, request.initial_capital,
        request.monthly_contribution, request.target or 0.0, returns_end=returns_end,
    )
    stats = planning.reference_stats(returns)
    required = None
    prob_txt = ""
    if request.target:
        required = planning.required_monthly_contribution(
            returns, request.horizon_years, request.initial_capital, request.target,
            returns_end=returns_end,
        )
        p = round(projection["probability_success"] * 100)
        prob_txt = (
            f"Significa che in circa {p} scenari su 100 — basati sui rendimenti storici "
            f"reali del periodo di riferimento — avresti raggiunto l'obiettivo."
        )

    fv = projection["final_value"]
    mix_txt = _explain_mix(risk, request.basis)
    if request.glide_path and end_alloc:
        mix_txt += (
            f" Col tempo il rischio si riduce: la quota azioni passa gradualmente "
            f"da circa {allocation.get('azioni', 0):.0f}% a {end_alloc['azioni']:.0f}% "
            f"avvicinandoti all'obiettivo."
        )
    explanations = {
        "mix": mix_txt,
        "probability": prob_txt,
        "scenarios": (
            f"Nello scenario sfavorevole arriveresti a circa {fv['p10']:,.0f}, "
            f"in quello mediano a {fv['p50']:,.0f}, in quello favorevole a {fv['p90']:,.0f} "
            f"(valuta del profilo)."
        ).replace(",", "."),
    }

    total_contrib = projection["total_contributed"]
    composition = {
        "initial": round(request.initial_capital, 2),
        "monthly_total": round(total_contrib - request.initial_capital, 2),
        "total": round(total_contrib, 2),
        "initial_share": (request.initial_capital / total_contrib) if total_contrib > 0 else 0.0,
        "months": max(request.horizon_years * 12 - 1, 0) if request.monthly_contribution > 0 else 0,
    }

    return _clean({
        "basis": request.basis,
        "risk_profile": risk,
        "allocation_source": alloc_source,
        "allocation": allocation,
        "breakdown": breakdown,
        "composition": composition,
        "glide": {
            "enabled": request.glide_path,
            "start_equity": round(float(allocation.get("azioni", 0)), 1),
            "end_equity": round(float(end_alloc["azioni"]), 1) if end_alloc else None,
        },
        "reference_period": {"from": ref_from, "to": ref_to},
        "reference_stats": stats,
        "projection": projection,
        "required_monthly_contribution": required,
        "explanations": explanations,
        "instruments_note": INSTRUMENTS_NOTE,
        "disclaimer": (
            "Questo è uno strumento educativo basato su dati storici reali, non una "
            "consulenza finanziaria personalizzata. I risultati passati non garantiscono "
            "quelli futuri."
        ),
    })


def _explain_mix(risk: str, basis: str) -> str:
    base = {
        "conservativo": "Mix prudente: prevalgono le obbligazioni per limitare le oscillazioni, con una quota di azioni per la crescita e un po' d'oro come riserva.",
        "bilanciato": "Mix equilibrato tra azioni (crescita) e obbligazioni (stabilità), con oro e materie prime per diversificare.",
        "aggressivo": "Mix orientato alla crescita: forte peso delle azioni e una piccola quota di Bitcoin, con più oscillazioni nel breve.",
    }.get(risk, "")
    if basis == "chameleon":
        base += " Pesi calcolati dal modello Chameleon sulla situazione macro attuale (tattico)."
    else:
        base += " Pesi strategici legati al tuo profilo di rischio, adatti a un orizzonte pluriennale."
    return base
