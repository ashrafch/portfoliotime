from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import get_settings
from database import init_db
from seed import seed_users
from routers import simulate, scenarios, portfolio, auth, admin

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: crea le tabelle e popola gli utenti seed (idempotente)
    await init_db()
    await seed_users()
    yield
    # Shutdown: niente da fare


app = FastAPI(
    title="PortfolioTime API",
    description="Simulazione portafoglio su scenari storici — motore finanziario verificato + AI narrativa",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(portfolio.router, prefix="/portfolio", tags=["portfolio"])
app.include_router(simulate.router, prefix="/simulate", tags=["simulate"])
app.include_router(scenarios.router, prefix="/scenarios", tags=["scenarios"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
