"""
Pydantic schemas for Holiday Calendar API.
"""

from datetime import date, datetime
from pydantic import BaseModel, ConfigDict


# ---------- Holiday Schemas ----------

class HolidayBase(BaseModel):
    """Base schema for Holiday."""
    holiday_date: date
    name: str
    description: str | None = None
    is_recurring: bool = False


class HolidayCreate(HolidayBase):
    """Schema for creating a holiday."""
    pass


class HolidayUpdate(BaseModel):
    """Schema for updating a holiday."""
    holiday_date: date | None = None
    name: str | None = None
    description: str | None = None
    is_recurring: bool | None = None


class HolidayRead(HolidayBase):
    """Schema for reading a holiday."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    calendar_id: int
    created_at: datetime


# ---------- Holiday Calendar Schemas ----------

class HolidayCalendarBase(BaseModel):
    """Base schema for HolidayCalendar."""
    calendar_code: str
    name: str
    country_code: str | None = None
    description: str | None = None


class HolidayCalendarCreate(HolidayCalendarBase):
    """Schema for creating a holiday calendar."""
    is_active: bool = True


class HolidayCalendarUpdate(BaseModel):
    """Schema for updating a holiday calendar."""
    calendar_code: str | None = None
    name: str | None = None
    country_code: str | None = None
    description: str | None = None
    is_active: bool | None = None


class HolidayCalendarRead(HolidayCalendarBase):
    """Schema for reading a holiday calendar (without holidays)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None


class HolidayCalendarWithHolidays(HolidayCalendarRead):
    """Schema for reading a holiday calendar with its holidays."""
    holidays: list[HolidayRead] = []


# ---------- Bulk Operations ----------

class BulkHolidayCreate(BaseModel):
    """Schema for creating multiple holidays at once."""
    holidays: list[HolidayCreate]


class BulkHolidayResponse(BaseModel):
    """Response for bulk holiday creation."""
    created_count: int
    holidays: list[HolidayRead]
