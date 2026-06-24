"""Cache prezzi in TimescaleDB — evita chiamate ripetute a Yahoo/CoinGecko."""

from sqlalchemy import String, Float, Date, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from datetime import date as date_type
from database import Base


class PriceCache(Base):
    __tablename__ = "price_cache"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    date: Mapped[date_type] = mapped_column(Date, nullable=False)
    close_price: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # R2: traccia la fonte

    __table_args__ = (UniqueConstraint("ticker", "date", name="uq_price_cache_ticker_date"),)
