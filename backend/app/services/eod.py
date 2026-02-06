"""
End-of-day (EOD) orchestration service.

Runs daily accrual and delinquency/NPA batches in one workflow.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.services.accrual import run_daily_accrual_batch
from app.services.delinquency import run_daily_delinquency_batch


def run_end_of_day_batch(
    as_of_date: date,
    db: Session,
    run_accruals: bool = True,
    run_delinquency: bool = True
) -> dict:
    """
    Run end-of-day processing steps for a specific date.
    """
    results = {
        "as_of_date": as_of_date,
        "accrual": None,
        "delinquency": None,
    }

    if run_accruals:
        results["accrual"] = run_daily_accrual_batch(as_of_date, db)

    if run_delinquency:
        results["delinquency"] = run_daily_delinquency_batch(as_of_date, db)

    return results
