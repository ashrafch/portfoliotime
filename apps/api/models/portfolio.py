from sqlalchemy import String, DateTime, JSON, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from database import Base
import uuid


class SimulationRecord(Base):
    """Una simulazione eseguita da un utente, con input e risultato persistiti.

    Sostituisce lo storage in-memory: ogni simulazione è legata a un utente
    e consultabile nello storico (R: tracciabilità + per-user history).
    """
    __tablename__ = "simulation_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True, nullable=False)

    status: Mapped[str] = mapped_column(String, default="completed")  # completed | failed
    label: Mapped[str] = mapped_column(String, default="")  # etichetta leggibile (es. periodo)

    input_params: Mapped[dict] = mapped_column(JSON, nullable=False)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    narrative: Mapped[str | None] = mapped_column(String, nullable=True)
    error: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
