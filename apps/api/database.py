from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import get_settings

settings = get_settings()

# asyncpg driver: sostituisce postgresql:// con postgresql+asyncpg://
_db_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(_db_url, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """Dependency FastAPI: fornisce una sessione DB per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Crea tutte le tabelle se non esistono (idempotente).

    Chiamato all'avvio dell'app. Importa i models prima del create_all
    affinché siano registrati nel metadata.
    """
    import models  # noqa: F401 — registra User, SimulationRecord, PriceCache

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
