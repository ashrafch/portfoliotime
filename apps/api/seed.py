"""
Seeding utenti iniziali — eseguito all'avvio dell'app (idempotente).

Crea due account se non esistono:
  - Super Admin: accesso completo (gestione utenti, tutte le simulazioni)
  - Utente Demo: accesso alle funzionalità standard
"""

from sqlalchemy import select

from database import AsyncSessionLocal
from models.user import User, UserRole
from security import hash_password
from config import get_settings

settings = get_settings()


async def seed_users() -> None:
    """Crea gli utenti seed se non già presenti."""
    async with AsyncSessionLocal() as db:
        created = []

        # Super Admin
        result = await db.execute(select(User).where(User.email == settings.seed_admin_email))
        if result.scalar_one_or_none() is None:
            db.add(User(
                email=settings.seed_admin_email,
                full_name=settings.seed_admin_name,
                hashed_password=hash_password(settings.seed_admin_password),
                role=UserRole.SUPER_ADMIN.value,
                is_active=True,
            ))
            created.append(f"super_admin <{settings.seed_admin_email}>")

        # Utente standard
        result = await db.execute(select(User).where(User.email == settings.seed_user_email))
        if result.scalar_one_or_none() is None:
            db.add(User(
                email=settings.seed_user_email,
                full_name=settings.seed_user_name,
                hashed_password=hash_password(settings.seed_user_password),
                role=UserRole.USER.value,
                is_active=True,
            ))
            created.append(f"user <{settings.seed_user_email}>")

        if created:
            await db.commit()
            print(f"[seed] Utenti creati: {', '.join(created)}")
        else:
            print("[seed] Utenti seed già presenti — nessuna azione.")
