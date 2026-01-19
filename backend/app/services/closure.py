"""
Loan closure and write-off service.

Handles:
- Normal loan closure
- One-time settlement (OTS)
- Write-off processing
- Recovery tracking
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import TYPE_CHECKING

from sqlalchemy import and_
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.models.loan_account import LoanAccount

from app.models.write_off import WriteOff, WriteOffRecovery
from app.models.repayment_schedule import RepaymentSchedule

CENT = Decimal("0.01")


def _to_decimal(value: float | Decimal | int | None) -> Decimal:
    """Convert numeric value to Decimal."""
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def close_loan_normal(
    loan_account: "LoanAccount",
    closure_date: date,
    db: Session
) -> "LoanAccount":
    """
    Close a loan that has been fully repaid.

    Args:
        loan_account: Loan account to close
        closure_date: Date of closure
        db: Database session

    Returns:
        Updated LoanAccount
    """
    # Verify loan is fully paid
    principal = _to_decimal(loan_account.principal_outstanding)
    interest = _to_decimal(loan_account.interest_outstanding)
    fees = _to_decimal(loan_account.fees_outstanding)

    if principal > Decimal("0.01"):
        raise ValueError(
            f"Loan has outstanding principal: {principal}"
        )

    if interest > Decimal("0.01"):
        raise ValueError(
            f"Loan has outstanding interest: {interest}"
        )

    # Check for unpaid schedule items
    unpaid = db.query(RepaymentSchedule).filter(
        and_(
            RepaymentSchedule.loan_account_id == loan_account.id,
            RepaymentSchedule.status.in_(["pending", "partial"])
        )
    ).count()

    if unpaid > 0:
        raise ValueError(f"Loan has {unpaid} unpaid installments")

    # Close the loan
    loan_account.status = "closed"
    loan_account.closure_date = closure_date
    loan_account.closure_type = "normal"
    loan_account.principal_outstanding = 0
    loan_account.interest_outstanding = 0
    loan_account.fees_outstanding = float(fees) if fees > 0 else 0

    db.commit()
    db.refresh(loan_account)

    return loan_account


def close_loan_settlement(
    loan_account: "LoanAccount",
    settlement_amount: float,
    settlement_date: date,
    approved_by: str,
    reason: str,
    db: Session
) -> "LoanAccount":
    """
    Close a loan via one-time settlement (OTS).

    The borrower pays a negotiated amount less than the total outstanding.

    Args:
        loan_account: Loan account to settle
        settlement_amount: Negotiated settlement amount
        settlement_date: Date of settlement
        approved_by: Approver of settlement
        reason: Reason for settlement
        db: Database session

    Returns:
        Updated LoanAccount
    """
    principal = _to_decimal(loan_account.principal_outstanding)
    interest = _to_decimal(loan_account.interest_outstanding)
    fees = _to_decimal(loan_account.fees_outstanding)
    total_outstanding = principal + interest + fees

    settlement = _to_decimal(settlement_amount)

    if settlement >= total_outstanding:
        raise ValueError(
            f"Settlement amount {settlement} >= outstanding {total_outstanding}. "
            "Use normal closure instead."
        )

    # Cancel remaining schedule items
    db.query(RepaymentSchedule).filter(
        and_(
            RepaymentSchedule.loan_account_id == loan_account.id,
            RepaymentSchedule.status.in_(["pending", "partial"])
        )
    ).update({"status": "settled"})

    # Close the loan
    loan_account.status = "closed"
    loan_account.closure_date = settlement_date
    loan_account.closure_type = "settlement"
    loan_account.settlement_amount = float(settlement)
    loan_account.principal_outstanding = 0
    loan_account.interest_outstanding = 0
    loan_account.fees_outstanding = 0

    db.commit()
    db.refresh(loan_account)

    return loan_account


def write_off_loan(
    loan_account: "LoanAccount",
    write_off_date: date,
    reason: str,
    approved_by: str,
    write_off_type: str = "full",
    db: Session = None
) -> WriteOff:
    """
    Write off a delinquent loan.

    Args:
        loan_account: Loan account to write off
        write_off_date: Date of write-off
        reason: Reason for write-off
        approved_by: Approver
        write_off_type: full, partial, or technical
        db: Database session

    Returns:
        Created WriteOff record
    """
    # Check if already written off
    existing = db.query(WriteOff).filter(
        WriteOff.loan_account_id == loan_account.id
    ).first()

    if existing:
        raise ValueError(
            f"Loan {loan_account.account_number} is already written off"
        )

    principal = _to_decimal(loan_account.principal_outstanding)
    interest = _to_decimal(loan_account.interest_outstanding)
    fees = _to_decimal(loan_account.fees_outstanding)
    total = principal + interest + fees

    # Create write-off record
    write_off = WriteOff(
        loan_account_id=loan_account.id,
        write_off_date=write_off_date,
        principal_written_off=float(principal),
        interest_written_off=float(interest),
        fees_written_off=float(fees),
        penalties_written_off=0,
        total_written_off=float(total),
        dpd_at_write_off=loan_account.dpd,
        write_off_type=write_off_type,
        reason=reason,
        approved_by=approved_by,
        approval_date=date.today(),
        recovery_status="pending"
    )

    db.add(write_off)

    # Cancel remaining schedule items
    db.query(RepaymentSchedule).filter(
        and_(
            RepaymentSchedule.loan_account_id == loan_account.id,
            RepaymentSchedule.status.in_(["pending", "partial"])
        )
    ).update({"status": "written_off"})

    # Update loan status
    loan_account.status = "written_off"
    loan_account.closure_date = write_off_date
    loan_account.closure_type = "write_off"

    db.commit()
    db.refresh(write_off)

    return write_off


def record_recovery(
    write_off_id: int,
    recovery_date: date,
    amount: float,
    recovery_source: str,
    payment_id: int | None = None,
    agency_commission_percent: float | None = None,
    notes: str = "",
    db: Session = None
) -> WriteOffRecovery:
    """
    Record a recovery payment against a written-off loan.

    Args:
        write_off_id: Write-off ID
        recovery_date: Date of recovery
        amount: Recovery amount
        recovery_source: Source (borrower, guarantor, collateral, agency)
        payment_id: Associated payment ID
        agency_commission_percent: Commission percent for agency recoveries
        notes: Notes
        db: Database session

    Returns:
        Created WriteOffRecovery record
    """
    write_off = db.query(WriteOff).filter(
        WriteOff.id == write_off_id
    ).first()

    if not write_off:
        raise ValueError(f"Write-off {write_off_id} not found")

    recovery_amount = _to_decimal(amount)

    # Calculate agency commission if applicable
    agency_commission = Decimal("0")
    if agency_commission_percent and recovery_source == "agency":
        agency_commission = (recovery_amount * _to_decimal(agency_commission_percent) / 100).quantize(CENT)

    net_recovery = recovery_amount - agency_commission

    # Allocate recovery to principal, interest, fees
    remaining = net_recovery
    principal_recovered = Decimal("0")
    interest_recovered = Decimal("0")
    fees_recovered = Decimal("0")

    # First allocate to fees
    fees_remaining = _to_decimal(write_off.fees_written_off) - _to_decimal(write_off.recovered_fees)
    if remaining > 0 and fees_remaining > 0:
        fees_recovered = min(remaining, fees_remaining)
        remaining -= fees_recovered

    # Then to interest
    interest_remaining = _to_decimal(write_off.interest_written_off) - _to_decimal(write_off.recovered_interest)
    if remaining > 0 and interest_remaining > 0:
        interest_recovered = min(remaining, interest_remaining)
        remaining -= interest_recovered

    # Then to principal
    principal_remaining = _to_decimal(write_off.principal_written_off) - _to_decimal(write_off.recovered_principal)
    if remaining > 0 and principal_remaining > 0:
        principal_recovered = min(remaining, principal_remaining)

    # Create recovery record
    recovery = WriteOffRecovery(
        write_off_id=write_off_id,
        payment_id=payment_id,
        recovery_date=recovery_date,
        amount=float(recovery_amount),
        principal_recovered=float(principal_recovered),
        interest_recovered=float(interest_recovered),
        fees_recovered=float(fees_recovered),
        recovery_source=recovery_source,
        agency_commission=float(agency_commission),
        net_recovery=float(net_recovery),
        notes=notes
    )

    db.add(recovery)

    # Update write-off totals
    write_off.recovered_principal = float(
        _to_decimal(write_off.recovered_principal) + principal_recovered
    )
    write_off.recovered_interest = float(
        _to_decimal(write_off.recovered_interest) + interest_recovered
    )
    write_off.recovered_fees = float(
        _to_decimal(write_off.recovered_fees) + fees_recovered
    )
    write_off.total_recovered = float(
        _to_decimal(write_off.total_recovered) + net_recovery
    )
    write_off.last_recovery_date = recovery_date

    # Update recovery status
    total_written_off = _to_decimal(write_off.total_written_off)
    total_recovered = _to_decimal(write_off.total_recovered)

    if total_recovered >= total_written_off:
        write_off.recovery_status = "complete"
    elif total_recovered > 0:
        write_off.recovery_status = "partial"
    else:
        write_off.recovery_status = "in_progress"

    db.commit()
    db.refresh(recovery)

    return recovery


def assign_to_collection_agency(
    write_off_id: int,
    agency_name: str,
    fee_percent: float,
    db: Session
) -> WriteOff:
    """
    Assign a written-off loan to a collection agency.

    Args:
        write_off_id: Write-off ID
        agency_name: Collection agency name
        fee_percent: Agency fee percentage
        db: Database session

    Returns:
        Updated WriteOff record
    """
    write_off = db.query(WriteOff).filter(
        WriteOff.id == write_off_id
    ).first()

    if not write_off:
        raise ValueError(f"Write-off {write_off_id} not found")

    write_off.assigned_to_agency = agency_name
    write_off.agency_fee_percent = fee_percent
    write_off.recovery_status = "in_progress"

    db.commit()
    db.refresh(write_off)

    return write_off


def get_write_off_summary(
    db: Session,
    start_date: date | None = None,
    end_date: date | None = None
) -> dict:
    """
    Get write-off summary statistics.

    Args:
        db: Database session
        start_date: Optional start date filter
        end_date: Optional end date filter

    Returns:
        Summary dictionary
    """
    from sqlalchemy import func as sql_func

    query = db.query(
        sql_func.count(WriteOff.id).label("count"),
        sql_func.sum(WriteOff.total_written_off).label("total_written_off"),
        sql_func.sum(WriteOff.total_recovered).label("total_recovered")
    )

    if start_date:
        query = query.filter(WriteOff.write_off_date >= start_date)
    if end_date:
        query = query.filter(WriteOff.write_off_date <= end_date)

    result = query.first()

    total_written_off = float(result.total_written_off or 0)
    total_recovered = float(result.total_recovered or 0)
    recovery_rate = (total_recovered / total_written_off * 100) if total_written_off > 0 else 0

    # By recovery status
    status_query = db.query(
        WriteOff.recovery_status,
        sql_func.count(WriteOff.id).label("count"),
        sql_func.sum(WriteOff.total_written_off).label("amount")
    )
    if start_date:
        status_query = status_query.filter(WriteOff.write_off_date >= start_date)
    if end_date:
        status_query = status_query.filter(WriteOff.write_off_date <= end_date)

    status_results = status_query.group_by(WriteOff.recovery_status).all()

    by_status = {}
    for row in status_results:
        by_status[row.recovery_status] = {
            "count": row.count,
            "amount": float(row.amount or 0)
        }

    return {
        "total_accounts": result.count or 0,
        "total_written_off": total_written_off,
        "total_recovered": total_recovered,
        "recovery_rate_percent": round(recovery_rate, 2),
        "net_loss": round(total_written_off - total_recovered, 2),
        "by_recovery_status": by_status
    }


def get_recovery_history(
    write_off_id: int,
    db: Session
) -> list[WriteOffRecovery]:
    """
    Get recovery history for a write-off.

    Args:
        write_off_id: Write-off ID
        db: Database session

    Returns:
        List of WriteOffRecovery records
    """
    return db.query(WriteOffRecovery).filter(
        WriteOffRecovery.write_off_id == write_off_id
    ).order_by(WriteOffRecovery.recovery_date.desc()).all()


def can_close_loan(loan_account: "LoanAccount", db: Session) -> dict:
    """
    Check if a loan can be closed and return closure options.

    Args:
        loan_account: Loan account
        db: Database session

    Returns:
        Dictionary with closure eligibility and options
    """
    principal = _to_decimal(loan_account.principal_outstanding)
    interest = _to_decimal(loan_account.interest_outstanding)
    fees = _to_decimal(loan_account.fees_outstanding)
    total = principal + interest + fees

    unpaid_count = db.query(RepaymentSchedule).filter(
        and_(
            RepaymentSchedule.loan_account_id == loan_account.id,
            RepaymentSchedule.status.in_(["pending", "partial"])
        )
    ).count()

    can_normal_close = principal <= Decimal("0.01") and unpaid_count == 0
    can_foreclose = principal > 0
    can_settle = total > 0 and loan_account.dpd >= 90
    can_write_off = total > 0 and loan_account.dpd >= 180

    return {
        "status": loan_account.status,
        "principal_outstanding": float(principal),
        "interest_outstanding": float(interest),
        "fees_outstanding": float(fees),
        "total_outstanding": float(total),
        "unpaid_installments": unpaid_count,
        "dpd": loan_account.dpd,
        "options": {
            "normal_closure": {
                "eligible": can_normal_close,
                "reason": "Loan is fully paid" if can_normal_close else "Outstanding balance exists"
            },
            "foreclosure": {
                "eligible": can_foreclose,
                "reason": "Pay full outstanding to close" if can_foreclose else "No outstanding"
            },
            "settlement": {
                "eligible": can_settle,
                "reason": "90+ DPD allows OTS" if can_settle else "Below 90 DPD or no outstanding"
            },
            "write_off": {
                "eligible": can_write_off,
                "reason": "180+ DPD allows write-off" if can_write_off else "Below 180 DPD"
            }
        }
    }
