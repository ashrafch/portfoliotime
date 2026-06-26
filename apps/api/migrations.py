"""
Runner migrazioni all'avvio.

Logica robusta che gestisce tre casi senza perdita di dati:
1. DB vuoto              → upgrade head (crea tutto da 0001)
2. DB legacy (create_all, senza alembic_version) → stamp head (adotta lo schema
   esistente) poi upgrade head (no-op)
3. DB già migrato       → upgrade head (applica eventuali migrazioni pendenti)

Funzione sincrona: va invocata in un thread (run_in_executor) dal lifespan async.
"""

import os
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, inspect

from config import get_settings

settings = get_settings()
_HERE = os.path.dirname(os.path.abspath(__file__))


def _alembic_config() -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", os.path.join(_HERE, "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    return cfg


def run_migrations() -> None:
    cfg = _alembic_config()
    engine = create_engine(settings.database_url)
    try:
        with engine.connect() as conn:
            insp = inspect(conn)
            has_version = insp.has_table("alembic_version")
            has_legacy_tables = insp.has_table("users")

        if has_legacy_tables and not has_version:
            # DB creato da create_all in passato: lo adottiamo senza ricrearlo
            command.stamp(cfg, "head")
            print("[migrations] DB esistente adottato (stamp head).")

        command.upgrade(cfg, "head")
        print("[migrations] Schema allineato a head.")
    finally:
        engine.dispose()
