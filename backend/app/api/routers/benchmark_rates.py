"""
API router for Benchmark Rate management.

Provides CRUD operations for benchmark rates and rate history.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.benchmark_rate import BenchmarkRate, BenchmarkRateHistory
from app.schemas.benchmark_rate import (
    BenchmarkRateCreate,
    BenchmarkRateHistoryCreate,
    BenchmarkRateHistoryRead,
    BenchmarkRateRead,
    BenchmarkRateUpdate,
    BenchmarkRateWithCurrentRate,
    BenchmarkRateWithHistory,
    BulkRateHistoryCreate,
    BulkRateHistoryResponse,
    RateLookupResponse,
)
from app.services.floating_rate import (
    get_benchmark_rate,
    get_current_benchmark_rate,
    add_benchmark_rate_value,
)

router = APIRouter(prefix="/benchmark-rates", tags=["benchmark-rates"])


# ---------- Benchmark Rate Endpoints ----------

@router.post("/", response_model=BenchmarkRateRead, status_code=status.HTTP_201_CREATED)
def create_benchmark_rate(
    rate_in: BenchmarkRateCreate,
    db: Session = Depends(get_db)
):
    """Create a new benchmark rate."""
    # Check for duplicate rate_code
    existing = db.query(BenchmarkRate).filter(
        BenchmarkRate.rate_code == rate_in.rate_code
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Benchmark rate with code '{rate_in.rate_code}' already exists"
        )

    rate = BenchmarkRate(**rate_in.model_dump())
    db.add(rate)
    db.commit()
    db.refresh(rate)
    return rate


@router.get("/", response_model=list[BenchmarkRateWithCurrentRate])
def list_benchmark_rates(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
    as_of_date: date | None = None,
    db: Session = Depends(get_db)
):
    """List all benchmark rates with current rate values."""
    query = db.query(BenchmarkRate)
    if active_only:
        query = query.filter(BenchmarkRate.is_active == True)

    rates = query.offset(skip).limit(limit).all()

    # Add current rate to each
    check_date = as_of_date or date.today()
    result = []
    for rate in rates:
        rate_entry = get_benchmark_rate(rate.id, check_date, db)
        result.append(BenchmarkRateWithCurrentRate(
            **BenchmarkRateRead.model_validate(rate).model_dump(),
            current_rate=rate_entry.rate_value if rate_entry else None,
            current_rate_date=rate_entry.effective_date if rate_entry else None
        ))

    return result


@router.get("/{rate_id}", response_model=BenchmarkRateWithHistory)
def get_benchmark_rate_by_id(
    rate_id: int,
    db: Session = Depends(get_db)
):
    """Get a benchmark rate by ID with its history."""
    rate = db.query(BenchmarkRate).filter(BenchmarkRate.id == rate_id).first()
    if not rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Benchmark rate {rate_id} not found"
        )
    return rate


@router.get("/code/{rate_code}", response_model=BenchmarkRateWithHistory)
def get_benchmark_rate_by_code(
    rate_code: str,
    db: Session = Depends(get_db)
):
    """Get a benchmark rate by code with its history."""
    rate = db.query(BenchmarkRate).filter(
        BenchmarkRate.rate_code == rate_code
    ).first()
    if not rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Benchmark rate with code '{rate_code}' not found"
        )
    return rate


@router.patch("/{rate_id}", response_model=BenchmarkRateRead)
def update_benchmark_rate(
    rate_id: int,
    rate_in: BenchmarkRateUpdate,
    db: Session = Depends(get_db)
):
    """Update a benchmark rate."""
    rate = db.query(BenchmarkRate).filter(BenchmarkRate.id == rate_id).first()
    if not rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Benchmark rate {rate_id} not found"
        )

    update_data = rate_in.model_dump(exclude_unset=True)

    # Check for duplicate rate_code if being changed
    if "rate_code" in update_data and update_data["rate_code"] != rate.rate_code:
        existing = db.query(BenchmarkRate).filter(
            BenchmarkRate.rate_code == update_data["rate_code"]
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Benchmark rate with code '{update_data['rate_code']}' already exists"
            )

    for field, value in update_data.items():
        setattr(rate, field, value)

    db.commit()
    db.refresh(rate)
    return rate


@router.delete("/{rate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_benchmark_rate(
    rate_id: int,
    db: Session = Depends(get_db)
):
    """Delete a benchmark rate and all its history."""
    rate = db.query(BenchmarkRate).filter(BenchmarkRate.id == rate_id).first()
    if not rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Benchmark rate {rate_id} not found"
        )

    db.delete(rate)
    db.commit()
    return None


# ---------- Rate History Endpoints ----------

@router.post("/{rate_id}/history", response_model=BenchmarkRateHistoryRead, status_code=status.HTTP_201_CREATED)
def add_rate_history(
    rate_id: int,
    history_in: BenchmarkRateHistoryCreate,
    db: Session = Depends(get_db)
):
    """Add a rate value for a specific date."""
    rate = db.query(BenchmarkRate).filter(BenchmarkRate.id == rate_id).first()
    if not rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Benchmark rate {rate_id} not found"
        )

    history = add_benchmark_rate_value(
        benchmark_id=rate_id,
        effective_date=history_in.effective_date,
        rate_value=history_in.rate_value,
        db=db
    )
    return history


@router.post("/{rate_id}/history/bulk", response_model=BulkRateHistoryResponse, status_code=status.HTTP_201_CREATED)
def add_rate_history_bulk(
    rate_id: int,
    bulk_in: BulkRateHistoryCreate,
    db: Session = Depends(get_db)
):
    """Add multiple rate values at once."""
    rate = db.query(BenchmarkRate).filter(BenchmarkRate.id == rate_id).first()
    if not rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Benchmark rate {rate_id} not found"
        )

    created = []
    for rate_data in bulk_in.rates:
        history = add_benchmark_rate_value(
            benchmark_id=rate_id,
            effective_date=rate_data.effective_date,
            rate_value=rate_data.rate_value,
            db=db
        )
        created.append(history)

    return BulkRateHistoryResponse(
        created_count=len(created),
        rates=[BenchmarkRateHistoryRead.model_validate(h) for h in created]
    )


@router.get("/{rate_id}/history", response_model=list[BenchmarkRateHistoryRead])
def list_rate_history(
    rate_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db)
):
    """List rate history for a benchmark."""
    rate = db.query(BenchmarkRate).filter(BenchmarkRate.id == rate_id).first()
    if not rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Benchmark rate {rate_id} not found"
        )

    query = db.query(BenchmarkRateHistory).filter(
        BenchmarkRateHistory.benchmark_id == rate_id
    )

    if start_date:
        query = query.filter(BenchmarkRateHistory.effective_date >= start_date)
    if end_date:
        query = query.filter(BenchmarkRateHistory.effective_date <= end_date)

    return query.order_by(BenchmarkRateHistory.effective_date.desc()).limit(limit).all()


@router.get("/{rate_id}/lookup", response_model=RateLookupResponse)
def lookup_rate(
    rate_id: int,
    as_of_date: date = Query(..., description="Date for which to look up the rate"),
    db: Session = Depends(get_db)
):
    """Look up the effective rate for a specific date."""
    rate = db.query(BenchmarkRate).filter(BenchmarkRate.id == rate_id).first()
    if not rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Benchmark rate {rate_id} not found"
        )

    rate_entry = get_benchmark_rate(rate_id, as_of_date, db)
    if not rate_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No rate found for {rate.rate_code} on or before {as_of_date}"
        )

    return RateLookupResponse(
        benchmark_id=rate_id,
        rate_code=rate.rate_code,
        as_of_date=as_of_date,
        effective_date=rate_entry.effective_date,
        rate_value=rate_entry.rate_value
    )


@router.delete("/{rate_id}/history/{history_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rate_history(
    rate_id: int,
    history_id: int,
    db: Session = Depends(get_db)
):
    """Delete a specific rate history entry."""
    history = db.query(BenchmarkRateHistory).filter(
        BenchmarkRateHistory.id == history_id,
        BenchmarkRateHistory.benchmark_id == rate_id
    ).first()
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rate history {history_id} not found for benchmark {rate_id}"
        )

    db.delete(history)
    db.commit()
    return None
