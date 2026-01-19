from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.loan_account import LoanAccount
from app.models.payment import Payment
from app.models.payment_allocation import PaymentAllocation
from app.models.repayment_schedule import RepaymentSchedule


def _to_decimal(value: float | Decimal) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def apply_payment(
    db: Session,
    loan_account: LoanAccount,
    payment: Payment,
) -> Decimal:
    remaining = _to_decimal(payment.amount)

    schedules = (
        db.query(RepaymentSchedule)
        .filter(RepaymentSchedule.loan_account_id == loan_account.id)
        .order_by(RepaymentSchedule.due_date, RepaymentSchedule.installment_number)
        .all()
    )

    for schedule in schedules:
        if remaining <= 0:
            break

        due_fees = _to_decimal(schedule.fees_due) - _to_decimal(schedule.fees_paid)
        due_interest = _to_decimal(schedule.interest_due) - _to_decimal(
            schedule.interest_paid
        )
        due_principal = _to_decimal(schedule.principal_due) - _to_decimal(
            schedule.principal_paid
        )

        allocated_fees = min(remaining, max(due_fees, Decimal("0")))
        remaining -= allocated_fees

        allocated_interest = min(remaining, max(due_interest, Decimal("0")))
        remaining -= allocated_interest

        allocated_principal = min(remaining, max(due_principal, Decimal("0")))
        remaining -= allocated_principal

        if allocated_fees > 0:
            schedule.fees_paid = float(
                _to_decimal(schedule.fees_paid) + allocated_fees
            )
        if allocated_interest > 0:
            schedule.interest_paid = float(
                _to_decimal(schedule.interest_paid) + allocated_interest
            )
        if allocated_principal > 0:
            schedule.principal_paid = float(
                _to_decimal(schedule.principal_paid) + allocated_principal
            )

        remaining_total = (
            _to_decimal(schedule.fees_due)
            + _to_decimal(schedule.interest_due)
            + _to_decimal(schedule.principal_due)
        ) - (
            _to_decimal(schedule.fees_paid)
            + _to_decimal(schedule.interest_paid)
            + _to_decimal(schedule.principal_paid)
        )

        if remaining_total <= 0:
            schedule.status = "paid"
        elif (
            schedule.fees_paid
            or schedule.interest_paid
            or schedule.principal_paid
        ):
            schedule.status = "partial"

        if allocated_fees or allocated_interest or allocated_principal:
            allocation = PaymentAllocation(
                payment_id=payment.id,
                schedule_id=schedule.id,
                principal_allocated=float(allocated_principal),
                interest_allocated=float(allocated_interest),
                fees_allocated=float(allocated_fees),
            )
            db.add(allocation)

    payment.unallocated_amount = float(remaining)
    _refresh_account_balances(db, loan_account)
    return remaining


def _refresh_account_balances(db: Session, loan_account: LoanAccount) -> None:
    schedules = (
        db.query(RepaymentSchedule)
        .filter(RepaymentSchedule.loan_account_id == loan_account.id)
        .order_by(RepaymentSchedule.due_date, RepaymentSchedule.installment_number)
        .all()
    )

    principal_outstanding = Decimal("0")
    interest_outstanding = Decimal("0")
    fees_outstanding = Decimal("0")

    next_due_date = None
    next_due_amount = None

    for schedule in schedules:
        principal_remaining = _to_decimal(schedule.principal_due) - _to_decimal(
            schedule.principal_paid
        )
        interest_remaining = _to_decimal(schedule.interest_due) - _to_decimal(
            schedule.interest_paid
        )
        fees_remaining = _to_decimal(schedule.fees_due) - _to_decimal(schedule.fees_paid)

        if principal_remaining > 0:
            principal_outstanding += principal_remaining
        if interest_remaining > 0:
            interest_outstanding += interest_remaining
        if fees_remaining > 0:
            fees_outstanding += fees_remaining

        total_remaining = principal_remaining + interest_remaining + fees_remaining
        if total_remaining > 0 and next_due_date is None:
            next_due_date = schedule.due_date
            next_due_amount = float(total_remaining)

    loan_account.principal_outstanding = float(principal_outstanding)
    loan_account.interest_outstanding = float(interest_outstanding)
    loan_account.fees_outstanding = float(fees_outstanding)
    loan_account.next_due_date = next_due_date
    loan_account.next_due_amount = next_due_amount

    if principal_outstanding == 0 and interest_outstanding == 0 and fees_outstanding == 0:
        loan_account.status = "closed"
    elif loan_account.status == "closed":
        loan_account.status = "active"


def compute_dpd(
    db: Session,
    loan_account_id: int,
    as_of_date: date | None = None,
) -> int:
    if as_of_date is None:
        as_of_date = date.today()

    schedules = (
        db.query(RepaymentSchedule)
        .filter(RepaymentSchedule.loan_account_id == loan_account_id)
        .order_by(RepaymentSchedule.due_date, RepaymentSchedule.installment_number)
        .all()
    )

    for schedule in schedules:
        total_remaining = (
            _to_decimal(schedule.fees_due)
            + _to_decimal(schedule.interest_due)
            + _to_decimal(schedule.principal_due)
        ) - (
            _to_decimal(schedule.fees_paid)
            + _to_decimal(schedule.interest_paid)
            + _to_decimal(schedule.principal_paid)
        )

        if schedule.due_date < as_of_date and total_remaining > 0:
            return (as_of_date - schedule.due_date).days

    return 0


def apply_payment_and_update_dpd(
    db: Session,
    loan_account: LoanAccount,
    payment: Payment,
) -> None:
    apply_payment(db, loan_account, payment)
    loan_account.dpd = compute_dpd(db, loan_account.id)
