"""Router /auth — registrazione, login (JSON + OAuth2 form), profilo corrente."""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, Field

from database import get_db
from models.user import User, UserRole
from security import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter()


# ─────────────────────────── Schemi ───────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Almeno 8 caratteri")
    full_name: str = Field("", max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ─────────────────────────── Endpoint ───────────────────────────

@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Registra un nuovo utente (ruolo standard) e restituisce il token."""
    existing = await db.execute(select(User).where(User.email == request.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Email già registrata")

    user = User(
        email=request.email,
        full_name=request.full_name or request.email.split("@")[0],
        hashed_password=hash_password(request.password),
        role=UserRole.USER.value,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user)
    return AuthResponse(access_token=token, user=UserResponse.model_validate(user))


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login con email + password (JSON). Usato dal frontend."""
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenziali non valide")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disattivato")

    token = create_access_token(user)
    return AuthResponse(access_token=token, user=UserResponse.model_validate(user))


@router.post("/token", response_model=TokenResponse)
async def login_oauth_form(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Login OAuth2 form — compatibile con il bottone 'Authorize' di Swagger.

    Il campo 'username' corrisponde all'email.
    """
    result = await db.execute(select(User).where(User.email == form.username))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenziali non valide")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disattivato")
    return TokenResponse(access_token=create_access_token(user))


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    """Restituisce il profilo dell'utente autenticato."""
    return UserResponse.model_validate(current_user)
