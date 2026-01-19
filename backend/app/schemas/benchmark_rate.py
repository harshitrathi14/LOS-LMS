"""
Pydantic schemas for Benchmark Rate API.
"""

from datetime import date, datetime
from pydantic import BaseModel, ConfigDict


# ---------- Benchmark Rate History Schemas ----------

class BenchmarkRateHistoryBase(BaseModel):
    """Base schema for benchmark rate history."""
    effective_date: date
    rate_value: float


class BenchmarkRateHistoryCreate(BenchmarkRateHistoryBase):
    """Schema for creating a rate history entry."""
    pass


class BenchmarkRateHistoryRead(BenchmarkRateHistoryBase):
    """Schema for reading a rate history entry."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    benchmark_id: int
    created_at: datetime


# ---------- Benchmark Rate Schemas ----------

class BenchmarkRateBase(BaseModel):
    """Base schema for benchmark rate."""
    rate_code: str
    name: str
    description: str | None = None
    currency: str = "INR"
    source: str | None = None
    frequency: str = "daily"


class BenchmarkRateCreate(BenchmarkRateBase):
    """Schema for creating a benchmark rate."""
    is_active: bool = True


class BenchmarkRateUpdate(BaseModel):
    """Schema for updating a benchmark rate."""
    rate_code: str | None = None
    name: str | None = None
    description: str | None = None
    currency: str | None = None
    source: str | None = None
    frequency: str | None = None
    is_active: bool | None = None


class BenchmarkRateRead(BenchmarkRateBase):
    """Schema for reading a benchmark rate (without history)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None


class BenchmarkRateWithHistory(BenchmarkRateRead):
    """Schema for reading a benchmark rate with its history."""
    rate_history: list[BenchmarkRateHistoryRead] = []


class BenchmarkRateWithCurrentRate(BenchmarkRateRead):
    """Schema for reading a benchmark rate with current rate value."""
    current_rate: float | None = None
    current_rate_date: date | None = None


# ---------- Bulk Operations ----------

class BulkRateHistoryCreate(BaseModel):
    """Schema for creating multiple rate history entries at once."""
    rates: list[BenchmarkRateHistoryCreate]


class BulkRateHistoryResponse(BaseModel):
    """Response for bulk rate history creation."""
    created_count: int
    rates: list[BenchmarkRateHistoryRead]


# ---------- Rate Lookup ----------

class RateLookupRequest(BaseModel):
    """Request for looking up a rate on a specific date."""
    benchmark_id: int | None = None
    rate_code: str | None = None
    as_of_date: date


class RateLookupResponse(BaseModel):
    """Response for rate lookup."""
    benchmark_id: int
    rate_code: str
    as_of_date: date
    effective_date: date
    rate_value: float
