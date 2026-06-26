"""Registra tutti i models SQLAlchemy per init_db / create_all."""

from models.user import User, UserRole
from models.portfolio import SimulationRecord
from models.price_cache import PriceCache
from models.profile import InvestorProfile

__all__ = ["User", "UserRole", "SimulationRecord", "PriceCache", "InvestorProfile"]
