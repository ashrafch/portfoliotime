from sqlalchemy import String, DateTime, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from database import Base
import enum
import uuid


class UserRole(str, enum.Enum):
    """Ruoli utente. super_admin ha accesso completo; user usa le funzionalità."""
    SUPER_ADMIN = "super_admin"
    USER = "user"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False, default="")
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    # Memorizzato come stringa ("super_admin" | "user") per semplicità di migrazione
    role: Mapped[str] = mapped_column(String, nullable=False, default=UserRole.USER.value)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @property
    def is_super_admin(self) -> bool:
        return self.role == UserRole.SUPER_ADMIN.value
