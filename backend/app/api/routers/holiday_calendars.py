"""
API router for Holiday Calendar management.

Provides CRUD operations for holiday calendars and their holidays.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.holiday_calendar import Holiday, HolidayCalendar
from app.schemas.holiday_calendar import (
    BulkHolidayCreate,
    BulkHolidayResponse,
    HolidayCalendarCreate,
    HolidayCalendarRead,
    HolidayCalendarUpdate,
    HolidayCalendarWithHolidays,
    HolidayCreate,
    HolidayRead,
    HolidayUpdate,
)

router = APIRouter(prefix="/holiday-calendars", tags=["holiday-calendars"])


# ---------- Holiday Calendar Endpoints ----------

@router.post("/", response_model=HolidayCalendarRead, status_code=status.HTTP_201_CREATED)
def create_holiday_calendar(
    calendar_in: HolidayCalendarCreate,
    db: Session = Depends(get_db)
):
    """Create a new holiday calendar."""
    # Check for duplicate calendar_code
    existing = db.query(HolidayCalendar).filter(
        HolidayCalendar.calendar_code == calendar_in.calendar_code
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Calendar with code '{calendar_in.calendar_code}' already exists"
        )

    calendar = HolidayCalendar(**calendar_in.model_dump())
    db.add(calendar)
    db.commit()
    db.refresh(calendar)
    return calendar


@router.get("/", response_model=list[HolidayCalendarRead])
def list_holiday_calendars(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """List all holiday calendars."""
    query = db.query(HolidayCalendar)
    if active_only:
        query = query.filter(HolidayCalendar.is_active == True)
    return query.offset(skip).limit(limit).all()


@router.get("/{calendar_id}", response_model=HolidayCalendarWithHolidays)
def get_holiday_calendar(
    calendar_id: int,
    db: Session = Depends(get_db)
):
    """Get a holiday calendar by ID with its holidays."""
    calendar = db.query(HolidayCalendar).filter(
        HolidayCalendar.id == calendar_id
    ).first()
    if not calendar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Holiday calendar {calendar_id} not found"
        )
    return calendar


@router.get("/code/{calendar_code}", response_model=HolidayCalendarWithHolidays)
def get_holiday_calendar_by_code(
    calendar_code: str,
    db: Session = Depends(get_db)
):
    """Get a holiday calendar by code with its holidays."""
    calendar = db.query(HolidayCalendar).filter(
        HolidayCalendar.calendar_code == calendar_code
    ).first()
    if not calendar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Holiday calendar with code '{calendar_code}' not found"
        )
    return calendar


@router.patch("/{calendar_id}", response_model=HolidayCalendarRead)
def update_holiday_calendar(
    calendar_id: int,
    calendar_in: HolidayCalendarUpdate,
    db: Session = Depends(get_db)
):
    """Update a holiday calendar."""
    calendar = db.query(HolidayCalendar).filter(
        HolidayCalendar.id == calendar_id
    ).first()
    if not calendar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Holiday calendar {calendar_id} not found"
        )

    update_data = calendar_in.model_dump(exclude_unset=True)

    # Check for duplicate calendar_code if being changed
    if "calendar_code" in update_data and update_data["calendar_code"] != calendar.calendar_code:
        existing = db.query(HolidayCalendar).filter(
            HolidayCalendar.calendar_code == update_data["calendar_code"]
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Calendar with code '{update_data['calendar_code']}' already exists"
            )

    for field, value in update_data.items():
        setattr(calendar, field, value)

    db.commit()
    db.refresh(calendar)
    return calendar


@router.delete("/{calendar_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_holiday_calendar(
    calendar_id: int,
    db: Session = Depends(get_db)
):
    """Delete a holiday calendar and all its holidays."""
    calendar = db.query(HolidayCalendar).filter(
        HolidayCalendar.id == calendar_id
    ).first()
    if not calendar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Holiday calendar {calendar_id} not found"
        )

    db.delete(calendar)
    db.commit()
    return None


# ---------- Holiday Endpoints ----------

@router.post("/{calendar_id}/holidays", response_model=HolidayRead, status_code=status.HTTP_201_CREATED)
def create_holiday(
    calendar_id: int,
    holiday_in: HolidayCreate,
    db: Session = Depends(get_db)
):
    """Add a holiday to a calendar."""
    calendar = db.query(HolidayCalendar).filter(
        HolidayCalendar.id == calendar_id
    ).first()
    if not calendar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Holiday calendar {calendar_id} not found"
        )

    holiday = Holiday(calendar_id=calendar_id, **holiday_in.model_dump())
    db.add(holiday)
    db.commit()
    db.refresh(holiday)
    return holiday


@router.post("/{calendar_id}/holidays/bulk", response_model=BulkHolidayResponse, status_code=status.HTTP_201_CREATED)
def create_holidays_bulk(
    calendar_id: int,
    bulk_in: BulkHolidayCreate,
    db: Session = Depends(get_db)
):
    """Add multiple holidays to a calendar at once."""
    calendar = db.query(HolidayCalendar).filter(
        HolidayCalendar.id == calendar_id
    ).first()
    if not calendar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Holiday calendar {calendar_id} not found"
        )

    created_holidays = []
    for holiday_data in bulk_in.holidays:
        holiday = Holiday(calendar_id=calendar_id, **holiday_data.model_dump())
        db.add(holiday)
        created_holidays.append(holiday)

    db.commit()
    for holiday in created_holidays:
        db.refresh(holiday)

    return BulkHolidayResponse(
        created_count=len(created_holidays),
        holidays=[HolidayRead.model_validate(h) for h in created_holidays]
    )


@router.get("/{calendar_id}/holidays", response_model=list[HolidayRead])
def list_holidays(
    calendar_id: int,
    year: int | None = None,
    db: Session = Depends(get_db)
):
    """List holidays for a calendar, optionally filtered by year."""
    calendar = db.query(HolidayCalendar).filter(
        HolidayCalendar.id == calendar_id
    ).first()
    if not calendar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Holiday calendar {calendar_id} not found"
        )

    query = db.query(Holiday).filter(Holiday.calendar_id == calendar_id)

    if year is not None:
        from sqlalchemy import extract
        query = query.filter(extract("year", Holiday.holiday_date) == year)

    return query.order_by(Holiday.holiday_date).all()


@router.get("/{calendar_id}/holidays/{holiday_id}", response_model=HolidayRead)
def get_holiday(
    calendar_id: int,
    holiday_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific holiday."""
    holiday = db.query(Holiday).filter(
        Holiday.id == holiday_id,
        Holiday.calendar_id == calendar_id
    ).first()
    if not holiday:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Holiday {holiday_id} not found in calendar {calendar_id}"
        )
    return holiday


@router.patch("/{calendar_id}/holidays/{holiday_id}", response_model=HolidayRead)
def update_holiday(
    calendar_id: int,
    holiday_id: int,
    holiday_in: HolidayUpdate,
    db: Session = Depends(get_db)
):
    """Update a holiday."""
    holiday = db.query(Holiday).filter(
        Holiday.id == holiday_id,
        Holiday.calendar_id == calendar_id
    ).first()
    if not holiday:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Holiday {holiday_id} not found in calendar {calendar_id}"
        )

    update_data = holiday_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(holiday, field, value)

    db.commit()
    db.refresh(holiday)
    return holiday


@router.delete("/{calendar_id}/holidays/{holiday_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_holiday(
    calendar_id: int,
    holiday_id: int,
    db: Session = Depends(get_db)
):
    """Delete a holiday."""
    holiday = db.query(Holiday).filter(
        Holiday.id == holiday_id,
        Holiday.calendar_id == calendar_id
    ).first()
    if not holiday:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Holiday {holiday_id} not found in calendar {calendar_id}"
        )

    db.delete(holiday)
    db.commit()
    return None
