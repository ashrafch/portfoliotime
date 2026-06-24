from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
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

    # CORS — origini consentite per il frontend
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ]

    # Seed utenti iniziali (creati automaticamente all'avvio se non esistono)
    # NB: il dominio .local è rifiutato dal validatore email → si usa .com
    seed_admin_email: str = "admin@portfoliotime.com"
    seed_admin_password: str = "Admin123!"
    seed_admin_name: str = "Super Admin"

    seed_user_email: str = "user@portfoliotime.com"
    seed_user_password: str = "User123!"
    seed_user_name: str = "Utente Demo"

    # Modello Claude per la narrativa AI (opzionale)
    claude_model: str = "claude-sonnet-4-6"

    # Limiti operativi
    max_simulation_years: int = 30
    celery_threshold_seconds: float = 2.0
    claude_max_tokens: int = 1500
    http_timeout_seconds: float = 15.0

    # Crypto: dati disponibili solo dal 2013-01-01
    crypto_data_start: str = "2013-01-01"


@lru_cache
def get_settings() -> Settings:
    return Settings()
