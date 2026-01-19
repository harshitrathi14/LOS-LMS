"""
Prepayment processing service.

Handles:
- Partial prepayment with EMI reduction
- Partial prepayment with tenure reduction
- Full foreclosure
- Prepayment penalty calculation
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import TYPE_CHECKING

from sqlalchemy import and_
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.models.loan_account import LoanAccount

from app.models.prepayment import Prepayment
from app.models.repayment_schedule import RepaymentSchedule
from app.models.payment import Payment
from app.services.interest import calculate_emi

CENT = Decimal("0.01")


def _to_decimal(value: float | Decimal | int | None) -> Decimal:
    """Convert numeric value to Decimal."""
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def calculate_prepayment_amount(
    loan_account: "LoanAccount",
    as_of_date: date,
    db: Session
) -> dict:
    """
    Calculate amount required for full prepayment/foreclosure.

    Args:
        loan_account: Loan account
        as_of_date: Date of prepayment
        db: Database session

    Returns:
        Dictionary with prepayment components
    """
    from app.services.fees import calculate_prepayment_penalty

    principal = _to_decimal(loan_account.principal_outstanding)
    interest = _to_decimal(loan_account.interest_outstanding)
    fees = _to_decimal(loan_account.fees_outstanding)

    # Get any overdue amounts
    overdue_items = db.query(RepaymentSchedule).filter(
        and_(
            RepaymentSchedule.loan_account_id == loan_account.id,
            RepaymentSchedule.status.in_(["pending", "partial"]),
            RepaymentSchedule.due_date < as_of_date
        )
    ).all()

    overdue_principal = Decimal("0")
    overdue_interest = Decimal("0")

    for item in overdue_items:
        overdue_principal += _to_decimal(item.principal_due) - _to_decimal(item.principal_paid or 0)
        overdue_interest += _to_decimal(item.interest_due) - _to_decimal(item.interest_paid or 0)

    # Calculate penalty
    penalty = calculate_prepayment_penalty(loan_account, float(principal), db)

    total = (principal + interest + fees + _to_decimal(penalty)).quantize(CENT)

    return {
        "principal_outstanding": float(principal),
        "interest_outstanding": float(interest),
        "fees_outstanding": float(fees),
        "overdue_principal": float(overdue_principal),
        "overdue_interest": float(overdue_interest),
        "prepayment_penalty": penalty,
        "total_payoff": float(total)
    }


def process_prepayment(
    loan_account: "LoanAccount",
    prepayment_amount: float,
    prepayment_date: date,
    action_type: str,
    payment_id: int | None = None,
    penalty_waived: float = 0,
    processed_by: str = "",
    db: Session = None
) -> Prepayment:
    """
    Process a prepayment on a loan.

    Args:
        loan_account: Loan account
        prepayment_amount: Amount being prepaid
        prepayment_date: Date of prepayment
        action_type: reduce_emi, reduce_tenure, or foreclosure
        payment_id: Associated payment ID
        penalty_waived: Amount of penalty waived
        processed_by: User processing prepayment
        db: Database session

    Returns:
        Created Prepayment record
    """
    from app.services.fees import calculate_prepayment_penalty

    prepay_amount = _to_decimal(prepayment_amount)
    outstanding = _to_decimal(loan_account.principal_outstanding)

    # Calculate penalty
    penalty_rate = None
    penalty_amount = Decimal("0")

    # Only calculate penalty for partial prepayments, not foreclosure
    if action_type != "foreclosure":
        penalty_result = calculate_prepayment_penalty(loan_account, float(prepay_amount), db)
        penalty_amount = _to_decimal(penalty_result)
        # Get penalty rate from product if available
        if hasattr(loan_account, 'application') and loan_account.application:
            product = loan_account.application.product
            if product:
                # Assume 2% default penalty rate
                penalty_rate = 2.0

    net_penalty = max(Decimal("0"), penalty_amount - _to_decimal(penalty_waived))
    principal_reduced = prepay_amount - net_penalty

    # Validate
    if principal_reduced > outstanding:
        raise ValueError(
            f"Prepayment amount {prepay_amount} exceeds outstanding {outstanding}"
        )

    is_foreclosure = action_type == "foreclosure" or principal_reduced >= outstanding

    # Store old values
    old_outstanding = float(outstanding)
    old_emi = None
    old_tenure = loan_account.tenure_months

    # Calculate old EMI
    if loan_account.schedule_type == "emi":
        remaining = db.query(RepaymentSchedule).filter(
            and_(
                RepaymentSchedule.loan_account_id == loan_account.id,
                RepaymentSchedule.status == "pending"
            )
        ).first()
        if remaining:
            old_emi = float(remaining.total_due)

    # Calculate remaining tenure
    remaining_items = db.query(RepaymentSchedule).filter(
        and_(
            RepaymentSchedule.loan_account_id == loan_account.id,
            RepaymentSchedule.status.in_(["pending", "partial"])
        )
    ).count()
    old_remaining_tenure = remaining_items

    # Apply prepayment to principal
    new_outstanding = outstanding - principal_reduced
    loan_account.principal_outstanding = float(new_outstanding)

    new_emi = None
    new_remaining_tenure = None

    if is_foreclosure:
        # Full foreclosure - close the loan
        loan_account.principal_outstanding = 0
        loan_account.status = "closed"
        loan_account.closure_date = prepayment_date
        loan_account.closure_type = "foreclosure"

        # Cancel all remaining schedule items
        db.query(RepaymentSchedule).filter(
            and_(
                RepaymentSchedule.loan_account_id == loan_account.id,
                RepaymentSchedule.status.in_(["pending", "partial"])
            )
        ).update({"status": "cancelled"})

        new_outstanding = Decimal("0")
        new_remaining_tenure = 0

    elif action_type == "reduce_emi":
        # Keep tenure, reduce EMI
        from app.services.schedule import generate_amortization_schedule

        # Cancel remaining schedule
        db.query(RepaymentSchedule).filter(
            and_(
                RepaymentSchedule.loan_account_id == loan_account.id,
                RepaymentSchedule.status == "pending"
            )
        ).update({"status": "cancelled"})

        # Generate new schedule
        new_schedule = generate_amortization_schedule(
            principal=float(new_outstanding),
            annual_rate=float(loan_account.interest_rate),
            tenure_months=old_remaining_tenure,
            start_date=prepayment_date,
            schedule_type=loan_account.schedule_type,
            day_count_convention=loan_account.day_count_convention,
            repayment_frequency=loan_account.repayment_frequency
        )

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

        if new_schedule:
            new_emi = new_schedule[0]["total_payment"]
            loan_account.next_due_date = new_schedule[0]["due_date"]
            loan_account.next_due_amount = new_emi

        new_remaining_tenure = old_remaining_tenure

    elif action_type == "reduce_tenure":
        # Keep EMI, reduce tenure
        if old_emi and old_emi > 0:
            # Calculate new tenure based on remaining principal and current EMI
            from app.services.schedule import generate_amortization_schedule

            # Cancel remaining schedule
            db.query(RepaymentSchedule).filter(
                and_(
                    RepaymentSchedule.loan_account_id == loan_account.id,
                    RepaymentSchedule.status == "pending"
                )
            ).update({"status": "cancelled"})

            # Estimate new tenure
            rate_monthly = _to_decimal(loan_account.interest_rate) / 100 / 12
            if rate_monthly > 0:
                import math
                emi_decimal = _to_decimal(old_emi)
                # n = log(EMI / (EMI - P * r)) / log(1 + r)
                denominator = float(emi_decimal - new_outstanding * rate_monthly)
                if denominator > 0:
                    new_tenure = int(math.ceil(
                        math.log(float(emi_decimal) / denominator) /
                        math.log(1 + float(rate_monthly))
                    ))
                else:
                    new_tenure = old_remaining_tenure
            else:
                new_tenure = int(float(new_outstanding) / float(old_emi))

            new_tenure = max(1, new_tenure)

            # Generate new schedule
            new_schedule = generate_amortization_schedule(
                principal=float(new_outstanding),
                annual_rate=float(loan_account.interest_rate),
                tenure_months=new_tenure,
                start_date=prepayment_date,
                schedule_type=loan_account.schedule_type,
                day_count_convention=loan_account.day_count_convention,
                repayment_frequency=loan_account.repayment_frequency
            )

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

            if new_schedule:
                new_emi = new_schedule[0]["total_payment"]
                loan_account.next_due_date = new_schedule[0]["due_date"]
                loan_account.next_due_amount = new_emi

            new_remaining_tenure = new_tenure
            loan_account.tenure_months = new_tenure

    # Create prepayment record
    prepayment = Prepayment(
        loan_account_id=loan_account.id,
        payment_id=payment_id,
        prepayment_date=prepayment_date,
        prepayment_amount=float(prepay_amount),
        penalty_rate=penalty_rate,
        penalty_amount=float(penalty_amount),
        penalty_waived=float(penalty_waived),
        net_penalty=float(net_penalty),
        principal_reduced=float(principal_reduced),
        interest_paid=0,
        action_type=action_type,
        old_outstanding=old_outstanding,
        old_emi=old_emi,
        old_remaining_tenure=old_remaining_tenure,
        new_outstanding=float(new_outstanding),
        new_emi=new_emi,
        new_remaining_tenure=new_remaining_tenure,
        is_foreclosure=is_foreclosure,
        foreclosure_charges=float(net_penalty) if is_foreclosure else 0,
        status="completed",
        processed_by=processed_by
    )

    db.add(prepayment)
    db.commit()
    db.refresh(prepayment)

    return prepayment


def get_prepayment_options(
    loan_account: "LoanAccount",
    prepayment_amount: float,
    db: Session
) -> dict:
    """
    Calculate impact of different prepayment options.

    Args:
        loan_account: Loan account
        prepayment_amount: Proposed prepayment amount
        db: Database session

    Returns:
        Dictionary comparing reduce_emi vs reduce_tenure options
    """
    from app.services.fees import calculate_prepayment_penalty

    prepay = _to_decimal(prepayment_amount)
    outstanding = _to_decimal(loan_account.principal_outstanding)
    rate = _to_decimal(loan_account.interest_rate)

    # Get current values
    remaining_items = db.query(RepaymentSchedule).filter(
        and_(
            RepaymentSchedule.loan_account_id == loan_account.id,
            RepaymentSchedule.status.in_(["pending", "partial"])
        )
    ).order_by(RepaymentSchedule.due_date).all()

    current_tenure = len(remaining_items)
    current_emi = _to_decimal(remaining_items[0].total_due) if remaining_items else Decimal("0")

    # Calculate penalty
    penalty = _to_decimal(calculate_prepayment_penalty(
        loan_account, float(prepay), db
    ))

    principal_reduced = prepay - penalty
    new_outstanding = outstanding - principal_reduced

    # Option 1: Reduce EMI
    new_emi_reduce_emi = None
    if current_tenure > 0 and loan_account.schedule_type == "emi":
        new_emi_reduce_emi = float(calculate_emi(
            new_outstanding,
            rate,
            current_tenure
        ))

    total_payment_reduce_emi = (new_emi_reduce_emi * current_tenure) if new_emi_reduce_emi else 0

    # Option 2: Reduce Tenure
    new_tenure_reduce_tenure = current_tenure
    if current_emi > 0:
        rate_monthly = rate / 100 / 12
        if rate_monthly > 0:
            import math
            denominator = float(current_emi - new_outstanding * rate_monthly)
            if denominator > 0:
                new_tenure_reduce_tenure = int(math.ceil(
                    math.log(float(current_emi) / denominator) /
                    math.log(1 + float(rate_monthly))
                ))

    total_payment_reduce_tenure = float(current_emi) * new_tenure_reduce_tenure

    return {
        "prepayment_amount": float(prepay),
        "penalty": float(penalty),
        "principal_reduced": float(principal_reduced),
        "new_outstanding": float(new_outstanding),
        "current": {
            "emi": float(current_emi),
            "tenure_remaining": current_tenure,
            "total_remaining_payment": float(current_emi * current_tenure)
        },
        "reduce_emi": {
            "new_emi": round(new_emi_reduce_emi, 2) if new_emi_reduce_emi else None,
            "tenure_remaining": current_tenure,
            "emi_savings": round(float(current_emi) - new_emi_reduce_emi, 2) if new_emi_reduce_emi else 0,
            "total_remaining_payment": round(total_payment_reduce_emi, 2)
        },
        "reduce_tenure": {
            "emi": float(current_emi),
            "new_tenure_remaining": new_tenure_reduce_tenure,
            "tenure_savings": current_tenure - new_tenure_reduce_tenure,
            "total_remaining_payment": round(total_payment_reduce_tenure, 2)
        }
    }


def get_prepayment_history(
    loan_account_id: int,
    db: Session
) -> list[Prepayment]:
    """
    Get prepayment history for a loan account.

    Args:
        loan_account_id: Loan account ID
        db: Database session

    Returns:
        List of Prepayment records
    """
    return db.query(Prepayment).filter(
        Prepayment.loan_account_id == loan_account_id
    ).order_by(Prepayment.prepayment_date.desc()).all()
