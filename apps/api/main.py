import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import get_settings
from migrations import run_migrations
from seed import seed_users
from data import fred_client
from routers import simulate, scenarios, portfolio, auth, admin, macro, me

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: allinea lo schema via Alembic (in un thread, runner sincrono),
    # poi popola gli utenti seed (idempotente).
    await asyncio.get_event_loop().run_in_executor(None, run_migrations)
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
app.include_router(macro.router, prefix="/macro", tags=["macro"])
app.include_router(me.router, prefix="/me", tags=["me"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/config")
async def config_status():
    """Stato delle integrazioni opzionali (solo booleani, nessun segreto esposto).

    Usato dal frontend per mostrare avvisi quando una fonte dati non è configurata.
    """
    ai_key = settings.anthropic_api_key or ""
    ai_ok = bool(ai_key) and "INSERISCI" not in ai_key and ai_key.startswith("sk-")
    return {
        "fred_configured": fred_client.is_configured(),
        "ai_configured": ai_ok,
    }
