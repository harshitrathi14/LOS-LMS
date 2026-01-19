"""
Loan restructuring service.

Handles:
- Rate reduction
- Tenure extension
- Principal haircut
- EMI rescheduling
- Combined restructuring
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import TYPE_CHECKING

from sqlalchemy import and_
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.models.loan_account import LoanAccount

from app.models.restructure import LoanRestructure
from app.models.repayment_schedule import RepaymentSchedule
from app.services.interest import calculate_emi

CENT = Decimal("0.01")


def _to_decimal(value: float | Decimal | int | None) -> Decimal:
    """Convert numeric value to Decimal."""
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def create_restructure_request(
    loan_account: "LoanAccount",
    restructure_type: str,
    new_rate: float | None = None,
    new_tenure: int | None = None,
    principal_waiver: float = 0,
    interest_waiver: float = 0,
    fees_waiver: float = 0,
    reason: str = "",
    requested_by: str = "",
    db: Session = None
) -> LoanRestructure:
    """
    Create a restructure request for approval.

    Args:
        loan_account: Loan account to restructure
        restructure_type: Type of restructure (rate_reduction, tenure_extension,
                         principal_haircut, emi_rescheduling, combination)
        new_rate: New interest rate (if changing)
        new_tenure: New tenure in months (if changing)
        principal_waiver: Amount of principal to waive
        interest_waiver: Amount of interest to waive
        fees_waiver: Amount of fees to waive
        reason: Reason for restructuring
        requested_by: User requesting restructure
        db: Database session

    Returns:
        Created LoanRestructure record
    """
    current_rate = float(loan_account.interest_rate)
    current_tenure = loan_account.tenure_months
    current_principal = float(loan_account.principal_outstanding)

    # Calculate current EMI
    current_emi = None
    if loan_account.schedule_type == "emi" and current_tenure > 0:
        current_emi = float(calculate_emi(
            Decimal(str(current_principal)),
            Decimal(str(current_rate)),
            current_tenure
        ))

    # Determine new values
    final_rate = new_rate if new_rate is not None else current_rate
    final_tenure = new_tenure if new_tenure is not None else current_tenure
    final_principal = current_principal - principal_waiver

    # Calculate new EMI
    new_emi = None
    if loan_account.schedule_type == "emi" and final_tenure > 0:
        new_emi = float(calculate_emi(
            Decimal(str(final_principal)),
            Decimal(str(final_rate)),
            final_tenure
        ))

    restructure = LoanRestructure(
        loan_account_id=loan_account.id,
        restructure_date=date.today(),
        effective_date=date.today(),
        restructure_type=restructure_type,
        original_principal=current_principal,
        original_rate=current_rate,
        original_tenure=current_tenure,
        original_emi=current_emi,
        new_principal=final_principal,
        new_rate=final_rate,
        new_tenure=final_tenure,
        new_emi=new_emi,
        principal_waived=principal_waiver,
        interest_waived=interest_waiver,
        fees_waived=fees_waiver,
        reason=reason,
        requested_by=requested_by,
        status="pending"
    )

    db.add(restructure)
    db.commit()
    db.refresh(restructure)

    return restructure


def approve_restructure(
    restructure_id: int,
    approved_by: str,
    effective_date: date | None = None,
    db: Session = None
) -> LoanRestructure:
    """
    Approve a restructure request.

    Args:
        restructure_id: Restructure request ID
        approved_by: Approver name/ID
        effective_date: Date restructure takes effect (default: today)
        db: Database session

    Returns:
        Updated LoanRestructure record
    """
    restructure = db.query(LoanRestructure).filter(
        LoanRestructure.id == restructure_id
    ).first()

    if not restructure:
        raise ValueError(f"Restructure {restructure_id} not found")

    if restructure.status != "pending":
        raise ValueError(f"Restructure {restructure_id} is not pending")

    restructure.status = "approved"
    restructure.approved_by = approved_by
    restructure.approved_date = date.today()
    if effective_date:
        restructure.effective_date = effective_date

    db.commit()
    db.refresh(restructure)

    return restructure


def apply_restructure(
    restructure_id: int,
    db: Session
) -> "LoanAccount":
    """
    Apply an approved restructure to the loan account.

    This will:
    - Update loan account terms
    - Cancel remaining schedule
    - Generate new schedule
    - Apply any waivers

    Args:
        restructure_id: Approved restructure ID
        db: Database session

    Returns:
        Updated LoanAccount
    """
    from app.models.loan_account import LoanAccount
    from app.services.schedule import generate_amortization_schedule

    restructure = db.query(LoanRestructure).filter(
        LoanRestructure.id == restructure_id
    ).first()

    if not restructure:
        raise ValueError(f"Restructure {restructure_id} not found")

    if restructure.status != "approved":
        raise ValueError(f"Restructure {restructure_id} is not approved")

    loan_account = db.query(LoanAccount).filter(
        LoanAccount.id == restructure.loan_account_id
    ).first()

    # Apply waivers to outstanding
    if restructure.principal_waived > 0:
        loan_account.principal_outstanding = float(
            _to_decimal(loan_account.principal_outstanding) -
            _to_decimal(restructure.principal_waived)
        )

    if restructure.interest_waived > 0:
        loan_account.interest_outstanding = float(
            max(Decimal("0"),
                _to_decimal(loan_account.interest_outstanding) -
                _to_decimal(restructure.interest_waived))
        )

    if restructure.fees_waived > 0:
        loan_account.fees_outstanding = float(
            max(Decimal("0"),
                _to_decimal(loan_account.fees_outstanding) -
                _to_decimal(restructure.fees_waived))
        )

    # Update loan terms
    loan_account.interest_rate = restructure.new_rate
    loan_account.tenure_months = restructure.new_tenure
    loan_account.last_restructure_date = restructure.effective_date
    loan_account.restructure_count = (loan_account.restructure_count or 0) + 1

    # Cancel unpaid schedule items
    db.query(RepaymentSchedule).filter(
        and_(
            RepaymentSchedule.loan_account_id == loan_account.id,
            RepaymentSchedule.status.in_(["pending", "partial"])
        )
    ).update({"status": "cancelled"})

    # Generate new schedule from effective date
    new_schedule = generate_amortization_schedule(
        principal=float(loan_account.principal_outstanding),
        annual_rate=restructure.new_rate,
        tenure_months=restructure.new_tenure,
        start_date=restructure.effective_date,
        schedule_type=loan_account.schedule_type,
        day_count_convention=loan_account.day_count_convention,
        repayment_frequency=loan_account.repayment_frequency
    )

    # Create new schedule items
    for item in new_schedule:
        schedule_item = RepaymentSchedule(
            loan_account_id=loan_account.id,
            installment_number=item["installment"],
            due_date=item["due_date"],
            principal_due=item["principal"],
            interest_due=item["interest"],
            total_due=item["total_payment"],
            opening_balance=item["opening_balance"],
            closing_balance=item["closing_balance"],
            status="pending"
        )
        db.add(schedule_item)

    # Update next due
    if new_schedule:
        loan_account.next_due_date = new_schedule[0]["due_date"]
        loan_account.next_due_amount = new_schedule[0]["total_payment"]

    # Mark restructure as applied
    restructure.status = "applied"

    db.commit()
    db.refresh(loan_account)

    return loan_account


def reject_restructure(
    restructure_id: int,
    rejected_by: str,
    reason: str,
    db: Session
) -> LoanRestructure:
    """
    Reject a restructure request.

    Args:
        restructure_id: Restructure request ID
        rejected_by: Rejector name/ID
        reason: Rejection reason
        db: Database session

    Returns:
        Updated LoanRestructure record
    """
    restructure = db.query(LoanRestructure).filter(
        LoanRestructure.id == restructure_id
    ).first()

    if not restructure:
        raise ValueError(f"Restructure {restructure_id} not found")

    if restructure.status != "pending":
        raise ValueError(f"Restructure {restructure_id} is not pending")

    restructure.status = "rejected"
    restructure.approved_by = rejected_by  # Store who rejected
    restructure.approved_date = date.today()
    restructure.notes = f"Rejected: {reason}"

    db.commit()
    db.refresh(restructure)

    return restructure


def get_restructure_history(
    loan_account_id: int,
    db: Session
) -> list[LoanRestructure]:
    """
    Get restructure history for a loan account.

    Args:
        loan_account_id: Loan account ID
        db: Database session

    Returns:
        List of LoanRestructure records
    """
    return db.query(LoanRestructure).filter(
        LoanRestructure.loan_account_id == loan_account_id
    ).order_by(LoanRestructure.restructure_date.desc()).all()


def calculate_restructure_impact(
    loan_account: "LoanAccount",
    new_rate: float | None = None,
    new_tenure: int | None = None,
    principal_waiver: float = 0
) -> dict:
    """
    Calculate the impact of a proposed restructure.

    Args:
        loan_account: Loan account
        new_rate: Proposed new rate
        new_tenure: Proposed new tenure
        principal_waiver: Proposed principal waiver

    Returns:
        Dictionary with comparison of current vs proposed terms
    """
    current_rate = float(loan_account.interest_rate)
    current_tenure = loan_account.tenure_months
    current_principal = float(loan_account.principal_outstanding)

    final_rate = new_rate if new_rate is not None else current_rate
    final_tenure = new_tenure if new_tenure is not None else current_tenure
    final_principal = current_principal - principal_waiver

    # Current EMI
    current_emi = None
    if loan_account.schedule_type == "emi" and current_tenure > 0:
        current_emi = float(calculate_emi(
            Decimal(str(current_principal)),
            Decimal(str(current_rate)),
            current_tenure
        ))

    # New EMI
    new_emi = None
    if loan_account.schedule_type == "emi" and final_tenure > 0:
        new_emi = float(calculate_emi(
            Decimal(str(final_principal)),
            Decimal(str(final_rate)),
            final_tenure
        ))

    # Total payments
    current_total = (current_emi * current_tenure) if current_emi else 0
    new_total = (new_emi * final_tenure) if new_emi else 0

    return {
        "current": {
            "principal": current_principal,
            "rate": current_rate,
            "tenure": current_tenure,
            "emi": current_emi,
            "total_payments": round(current_total, 2)
        },
        "proposed": {
            "principal": final_principal,
            "rate": final_rate,
            "tenure": final_tenure,
            "emi": round(new_emi, 2) if new_emi else None,
            "total_payments": round(new_total, 2)
        },
        "savings": {
            "principal_waived": principal_waiver,
            "emi_reduction": round(current_emi - new_emi, 2) if current_emi and new_emi else 0,
            "total_payment_reduction": round(current_total - new_total, 2)
        }
    }
