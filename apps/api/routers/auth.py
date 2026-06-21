"""Router /auth — registrazione, login, token JWT."""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from datetime import timedelta, datetime, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext

from database import get_db
from config import get_settings

router = APIRouter()
settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode(
        {"sub": user_id, "exp": expire},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


@router.post("/register", status_code=201)
async def register(request: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    """Registra un nuovo utente."""
    # Scaffold: implementazione completa richiede model User e query DB
    return {"message": "Registrazione completata (scaffold — da collegare a DB)"}


@router.post("/token", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    """Login con email e password — restituisce JWT."""
    # Scaffold: verificare credenziali da DB
    # In MVP per testing, accetta qualsiasi credenziale
    token = _create_token(user_id=form.username)
    return TokenResponse(access_token=token)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """Dependency: estrae user_id dal JWT. Usare come Depends() nei router protetti."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id: str = payload.get("sub", "")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token non valido")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Token non valido o scaduto")
