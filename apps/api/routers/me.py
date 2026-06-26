"""
Router /me — dati personali dell'utente: profilo investitore e analytics sullo storico.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from database import get_db
from models.user import User
from models.profile import InvestorProfile
from models.portfolio import SimulationRecord
from security import get_current_user
import recommendation

router = APIRouter()

VALID_RISK = {"conservativo", "bilanciato", "aggressivo"}


class ProfileResponse(BaseModel):
    eta: int
    risk_profile: str
    base_currency: str
    goal: str
    default_tasso_fed: float
    default_inflazione: float
    country: str
    dividend_preference: str

    class Config:
        from_attributes = True


class ProfileUpdate(BaseModel):
    eta: Optional[int] = Field(None, ge=18, le=100)
    risk_profile: Optional[str] = None
    base_currency: Optional[str] = Field(None, min_length=3, max_length=3)
    goal: Optional[str] = Field(None, max_length=200)
    default_tasso_fed: Optional[float] = Field(None, ge=0.0, le=25.0)
    default_inflazione: Optional[float] = Field(None, ge=-5.0, le=50.0)
    country: Optional[str] = Field(None, max_length=60)
    dividend_preference: Optional[str] = None


VALID_DIVIDEND_PREF = {"accumulazione", "distribuzione", "indifferente"}


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


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Profilo investitore dell'utente (creato con default al primo accesso)."""
    profile = await _get_or_create_profile(db, current_user.id)
    return ProfileResponse.model_validate(profile)


@router.put("/profile", response_model=ProfileResponse)
async def update_profile(
    update: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggiorna il profilo investitore."""
    profile = await _get_or_create_profile(db, current_user.id)

    data = update.model_dump(exclude_none=True)
    if "risk_profile" in data and data["risk_profile"] not in VALID_RISK:
        data.pop("risk_profile")
    if "dividend_preference" in data and data["dividend_preference"] not in VALID_DIVIDEND_PREF:
        data.pop("dividend_preference")
    if "base_currency" in data:
        data["base_currency"] = data["base_currency"].upper()

    for k, v in data.items():
        setattr(profile, k, v)

    await db.commit()
    await db.refresh(profile)
    return ProfileResponse.model_validate(profile)


class AnalyticsResponse(BaseModel):
    total_simulations: int
    completed: int
    avg_total_return: Optional[float] = None
    avg_max_drawdown: Optional[float] = None
    avg_sharpe: Optional[float] = None
    best: Optional[dict] = None
    worst: Optional[dict] = None
    benchmark_win_rate: Optional[float] = None  # % simulazioni che battono il benchmark


class NotificationsResponse(BaseModel):
    has_changes: bool
    changes: list[dict]
    source: str
    last_checked: Optional[str] = None


@router.get("/notifications", response_model=NotificationsResponse)
async def notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Segnala se l'allocazione consigliata è cambiata dall'ultima volta che l'hai vista.

    Non salva nulla: lo snapshot si aggiorna quando apri la pagina 'Oggi'
    (GET /portfolio/recommended).
    """
    profile = await _get_or_create_profile(db, current_user.id)
    rec = await recommendation.current_recommendation(profile)
    changes = recommendation.diff_allocations(profile.last_recommended, rec["allocazione"])
    return NotificationsResponse(
        has_changes=bool(changes),
        changes=changes,
        source=rec["source"],
        last_checked=profile.last_recommended_at.isoformat() if profile.last_recommended_at else None,
    )


@router.get("/analytics", response_model=AnalyticsResponse)
async def my_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Statistiche aggregate sullo storico simulazioni dell'utente."""
    records = (await db.execute(
        select(SimulationRecord).where(SimulationRecord.user_id == current_user.id)
    )).scalars().all()

    completed = [r for r in records if r.status == "completed" and r.result]
    if not completed:
        return AnalyticsResponse(total_simulations=len(records), completed=0)

    def vals(key: str) -> list[float]:
        out = []
        for r in completed:
            v = (r.result or {}).get(key)
            if isinstance(v, (int, float)):
                out.append(float(v))
        return out

    returns = [(r, (r.result or {}).get("total_return")) for r in completed]
    returns = [(r, v) for r, v in returns if isinstance(v, (int, float))]

    best = worst = None
    if returns:
        best_r = max(returns, key=lambda x: x[1])
        worst_r = min(returns, key=lambda x: x[1])
        best = {"label": best_r[0].label, "total_return": best_r[1], "id": best_r[0].id}
        worst = {"label": worst_r[0].label, "total_return": worst_r[1], "id": worst_r[0].id}

    # Win rate vs benchmark
    wins = 0
    comparable = 0
    for r in completed:
        res = r.result or {}
        tr, br = res.get("total_return"), res.get("benchmark_total_return")
        if isinstance(tr, (int, float)) and isinstance(br, (int, float)):
            comparable += 1
            if tr > br:
                wins += 1
    win_rate = (wins / comparable) if comparable else None

    def avg(xs: list[float]) -> Optional[float]:
        return sum(xs) / len(xs) if xs else None

    return AnalyticsResponse(
        total_simulations=len(records),
        completed=len(completed),
        avg_total_return=avg(vals("total_return")),
        avg_max_drawdown=avg(vals("max_drawdown")),
        avg_sharpe=avg(vals("sharpe_ratio")),
        best=best,
        worst=worst,
        benchmark_win_rate=win_rate,
    )
