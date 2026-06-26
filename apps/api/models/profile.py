"""Profilo investitore — dati personalizzati 1:1 con l'utente."""

from sqlalchemy import String, Integer, Float, DateTime, JSON, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from database import Base


class InvestorProfile(Base):
    """Preferenze e profilo dell'utente, usati per pre-compilare le simulazioni."""
    __tablename__ = "investor_profiles"

    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), primary_key=True)

    eta: Mapped[int] = mapped_column(Integer, default=40)
    # conservativo | bilanciato | aggressivo
    risk_profile: Mapped[str] = mapped_column(String, default="bilanciato")
    base_currency: Mapped[str] = mapped_column(String(3), default="EUR")
    goal: Mapped[str] = mapped_column(String, default="")

    # Assunzioni macro di default (pre-compilano il form simulazione)
    default_tasso_fed: Mapped[float] = mapped_column(Float, default=5.25)
    default_inflazione: Mapped[float] = mapped_column(Float, default=3.5)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Ultima allocazione consigliata calcolata (per rilevare i cambiamenti / "alert")
    last_recommended: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_recommended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
