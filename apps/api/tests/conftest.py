"""
Fixture condivise per i test API.

Usa SQLite in-memory + override di get_db, e mocka il repository prezzi per
evitare chiamate di rete. Permette di testare auth, RBAC e simulazioni offline.
"""

import pytest_asyncio
import pandas as pd
import numpy as np
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

import main
from database import Base, get_db
import models  # noqa: F401 — registra i model nel metadata
from models.user import User, UserRole
from security import hash_password


@pytest_asyncio.fixture
async def client(monkeypatch):
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSession = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed: un admin e un utente
    async with TestSession() as s:
        s.add(User(
            email="admin@portfoliotime.com", full_name="Admin",
            hashed_password=hash_password("Admin123!"),
            role=UserRole.SUPER_ADMIN.value, is_active=True,
        ))
        s.add(User(
            email="user@portfoliotime.com", full_name="User",
            hashed_password=hash_password("User123!"),
            role=UserRole.USER.value, is_active=True,
        ))
        await s.commit()

    async def override_get_db():
        async with TestSession() as session:
            yield session

    main.app.dependency_overrides[get_db] = override_get_db

    # Mock prezzi: dati sintetici deterministici, niente rete
    async def fake_get_prices(db, tickers, date_from, date_to):
        idx = pd.date_range(date_from, date_to, freq="B")
        rng = np.random.default_rng(7)
        data = {t: 100 * (1 + rng.normal(0.0003, 0.01, len(idx))).cumprod() for t in tickers}
        return pd.DataFrame(data, index=idx), [], {t: "cache" for t in tickers}

    monkeypatch.setattr("routers.simulate.price_repository.get_prices", fake_get_prices)

    transport = ASGITransport(app=main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    main.app.dependency_overrides.clear()
    await engine.dispose()


async def _token(client: AsyncClient, email: str, password: str) -> str:
    r = await client.post("/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"]


@pytest_asyncio.fixture
async def admin_headers(client):
    token = await _token(client, "admin@portfoliotime.com", "Admin123!")
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def user_headers(client):
    token = await _token(client, "user@portfoliotime.com", "User123!")
    return {"Authorization": f"Bearer {token}"}


SIM_BODY = {
    "eta": 40, "tasso_fed": 5.25, "delta_tasso": -0.5,
    "btc_prezzo_corrente": 0, "btc_ath": 0, "is_post_halving": False,
    "tasso_nominale": 5.25, "inflazione": 3.5,
    "tassi_in_calo": True, "qe_attivo": False,
    "date_from": "2007-10-09", "date_to": "2009-03-09", "benchmark_ticker": "SPY",
}
