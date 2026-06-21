from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import get_settings
from routers import simulate, scenarios, portfolio, auth

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: verifica connessioni
    yield
    # Shutdown: cleanup


app = FastAPI(
    title="PortfolioTime API",
    description="Simulazione portafoglio su scenari storici — motore finanziario verificato + AI narrativa",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.next_public_api_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(portfolio.router, prefix="/portfolio", tags=["portfolio"])
app.include_router(simulate.router, prefix="/simulate", tags=["simulate"])
app.include_router(scenarios.router, prefix="/scenarios", tags=["scenarios"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
