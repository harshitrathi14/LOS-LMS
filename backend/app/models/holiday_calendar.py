"""
Holiday Calendar models for business day adjustments.

HolidayCalendar: Defines a calendar (e.g., "IN" for India, "US" for United States)
Holiday: Individual holiday entries within a calendar
"""

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class HolidayCalendar(Base):
    """
    Holiday calendar definition.

    Each calendar represents a set of holidays for a specific country/region
    or custom business calendar.
    """
    __tablename__ = "holiday_calendars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    calendar_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    country_code: Mapped[str | None] = mapped_column(String(3))  # ISO 3166-1 alpha-2/3
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    holidays: Mapped[list["Holiday"]] = relationship(
        "Holiday",
        back_populates="calendar",
        cascade="all, delete-orphan"
    )


class Holiday(Base):
    """
    Individual holiday entry within a calendar.

    Holidays can be:
    - One-time: Specific date, non-recurring
    - Recurring: Same date every year (e.g., Jan 1 New Year's Day)
    """
    __tablename__ = "holidays"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    calendar_id: Mapped[int] = mapped_column(
        ForeignKey("holiday_calendars.id", ondelete="CASCADE"),
        index=True
    )
    holiday_date: Mapped[Date] = mapped_column(Date, index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    calendar: Mapped["HolidayCalendar"] = relationship(
        "HolidayCalendar",
        back_populates="holidays"
    )
