"""
Benchmark Rate models for floating rate loan support.

BenchmarkRate: Defines a benchmark rate (e.g., SOFR, LIBOR, MCLR, T-Bill)
BenchmarkRateHistory: Historical rate values with effective dates
"""

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BenchmarkRate(Base):
    """
    Benchmark rate definition.

    Examples: SOFR, LIBOR, MCLR, PLR, T-Bill rates
    """
    __tablename__ = "benchmark_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rate_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    source: Mapped[str | None] = mapped_column(String(100))  # Data source/provider
    frequency: Mapped[str] = mapped_column(String(20), default="daily")  # Publication frequency
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    rate_history: Mapped[list["BenchmarkRateHistory"]] = relationship(
        "BenchmarkRateHistory",
        back_populates="benchmark",
        cascade="all, delete-orphan",
        order_by="desc(BenchmarkRateHistory.effective_date)"
    )


class BenchmarkRateHistory(Base):
    """
    Historical benchmark rate values.

    Each entry represents the rate value for a specific date.
    Rates are stored as percentages (e.g., 5.25 for 5.25%).
    """
    __tablename__ = "benchmark_rate_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    benchmark_id: Mapped[int] = mapped_column(
        ForeignKey("benchmark_rates.id", ondelete="CASCADE"),
        index=True
    )
    effective_date: Mapped[Date] = mapped_column(Date, index=True)
    rate_value: Mapped[float] = mapped_column(Numeric(10, 6))  # Up to 6 decimal places
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    benchmark: Mapped["BenchmarkRate"] = relationship(
        "BenchmarkRate",
        back_populates="rate_history"
    )

    # Ensure unique rate per date per benchmark
    __table_args__ = (
        {"sqlite_autoincrement": True},
    )
