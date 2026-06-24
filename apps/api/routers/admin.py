"""
Router /admin — riservato ai super_admin (R: RBAC).

Gestione utenti, statistiche di piattaforma, vista su tutte le simulazioni.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Optional

from database import get_db
from models.user import User, UserRole
from models.portfolio import SimulationRecord
from security import require_super_admin

router = APIRouter()


class AdminUser(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    created_at: Optional[str] = None
    simulations_count: int = 0


class UpdateUserRequest(BaseModel):
    role: Optional[str] = None        # "super_admin" | "user"
    is_active: Optional[bool] = None


class PlatformStats(BaseModel):
    total_users: int
    active_users: int
    super_admins: int
    total_simulations: int
    failed_simulations: int


@router.get("/stats", response_model=PlatformStats)
async def platform_stats(
    _: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    active_users = (await db.execute(
        select(func.count(User.id)).where(User.is_active.is_(True))
    )).scalar() or 0
    super_admins = (await db.execute(
        select(func.count(User.id)).where(User.role == UserRole.SUPER_ADMIN.value)
    )).scalar() or 0
    total_sims = (await db.execute(select(func.count(SimulationRecord.id)))).scalar() or 0
    failed_sims = (await db.execute(
        select(func.count(SimulationRecord.id)).where(SimulationRecord.status == "failed")
    )).scalar() or 0

    return PlatformStats(
        total_users=total_users, active_users=active_users, super_admins=super_admins,
        total_simulations=total_sims, failed_simulations=failed_sims,
    )


@router.get("/users", response_model=list[AdminUser])
async def list_users(
    _: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    users = (await db.execute(select(User).order_by(User.created_at))).scalars().all()

    # Conteggio simulazioni per utente
    counts_rows = (await db.execute(
        select(SimulationRecord.user_id, func.count(SimulationRecord.id))
        .group_by(SimulationRecord.user_id)
    )).all()
    counts = {uid: c for uid, c in counts_rows}

    return [
        AdminUser(
            id=u.id, email=u.email, full_name=u.full_name, role=u.role,
            is_active=u.is_active,
            created_at=u.created_at.isoformat() if u.created_at else None,
            simulations_count=counts.get(u.id, 0),
        )
        for u in users
    ]


@router.patch("/users/{user_id}", response_model=AdminUser)
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Aggiorna ruolo e/o stato attivo di un utente."""
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="Utente non trovato")

    if request.role is not None:
        if request.role not in (UserRole.SUPER_ADMIN.value, UserRole.USER.value):
            raise HTTPException(status_code=422, detail="Ruolo non valido")
        user.role = request.role

    if request.is_active is not None:
        # Impedisce all'admin di disattivare se stesso
        if user.id == admin.id and request.is_active is False:
            raise HTTPException(status_code=400, detail="Non puoi disattivare il tuo account")
        user.is_active = request.is_active

    await db.commit()
    await db.refresh(user)
    return AdminUser(
        id=user.id, email=user.email, full_name=user.full_name, role=user.role,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Elimina un utente e tutte le sue simulazioni."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Non puoi eliminare il tuo account")

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="Utente non trovato")

    # Elimina prima le simulazioni collegate
    sims = (await db.execute(
        select(SimulationRecord).where(SimulationRecord.user_id == user_id)
    )).scalars().all()
    for s in sims:
        await db.delete(s)
    await db.delete(user)
    await db.commit()


@router.get("/simulations")
async def list_all_simulations(
    _: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
    limit: int = 100,
):
    """Tutte le simulazioni della piattaforma (con email del proprietario)."""
    rows = (await db.execute(
        select(SimulationRecord, User.email)
        .join(User, User.id == SimulationRecord.user_id)
        .order_by(desc(SimulationRecord.created_at))
        .limit(limit)
    )).all()

    out = []
    for record, email in rows:
        res = record.result or {}
        out.append({
            "id": record.id,
            "user_email": email,
            "label": record.label,
            "status": record.status,
            "total_return": res.get("total_return"),
            "created_at": record.created_at.isoformat() if record.created_at else None,
        })
    return out
