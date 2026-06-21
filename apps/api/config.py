from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    database_url: str = "postgresql://portfoliotime:portfoliotime@localhost:5432/portfoliotime"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"

    anthropic_api_key: str = ""
    fred_api_key: str = ""
    coingecko_api_key: str = ""

    jwt_secret: str = "dev_secret_change_in_production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    next_public_api_url: str = "http://localhost:8000"

    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # Limiti operativi
    max_simulation_years: int = 30
    celery_threshold_seconds: float = 2.0
    claude_max_tokens: int = 1500
    http_timeout_seconds: float = 10.0

    # Crypto: dati disponibili solo dal 2013-01-01
    crypto_data_start: str = "2013-01-01"


@lru_cache
def get_settings() -> Settings:
    return Settings()
