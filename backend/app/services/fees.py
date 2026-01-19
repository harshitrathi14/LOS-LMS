"""
Fee calculation and management service.

Handles:
- Fee calculation (processing, late, prepayment penalty)
- Fee posting to loan accounts
- Fee waiver processing
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import TYPE_CHECKING

from sqlalchemy import and_
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.models.loan_account import LoanAccount

from app.models.fee import FeeType, ProductFee, FeeCharge

CENT = Decimal("0.01")


def _to_decimal(value: float | Decimal | int | None) -> Decimal:
    """Convert numeric value to Decimal."""
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def get_fee_type_by_code(code: str, db: Session) -> FeeType | None:
    """Get a fee type by its code."""
    return db.query(FeeType).filter(FeeType.code == code).first()


def get_product_fee(
    product_id: int,
    fee_type_code: str,
    db: Session
) -> ProductFee | None:
    """Get the fee configuration for a product and fee type."""
    fee_type = get_fee_type_by_code(fee_type_code, db)
    if not fee_type:
        return None

    return db.query(ProductFee).filter(
        and_(
            ProductFee.product_id == product_id,
            ProductFee.fee_type_id == fee_type.id,
            ProductFee.is_active == True
        )
    ).first()


def calculate_fee_amount(
    product_fee: ProductFee,
    base_amount: Decimal,
    apply_limits: bool = True
) -> Decimal:
    """
    Calculate fee amount based on configuration.

    Args:
        product_fee: Fee configuration
        base_amount: Amount to calculate percentage on (e.g., principal)
        apply_limits: Whether to apply min/max limits

    Returns:
        Calculated fee amount
    """
    fee_type = product_fee.fee_type

    if fee_type.calculation_type == "flat":
        amount = _to_decimal(product_fee.flat_amount or 0)

    elif fee_type.calculation_type == "percentage":
        percentage = _to_decimal(product_fee.percentage_value or 0)
        amount = (base_amount * percentage / Decimal("100")).quantize(CENT, rounding=ROUND_HALF_UP)

    else:
        # Default to flat if unknown
        amount = _to_decimal(product_fee.flat_amount or 0)

    # Apply min/max limits
    if apply_limits:
        if product_fee.min_amount is not None:
            min_amt = _to_decimal(product_fee.min_amount)
            amount = max(amount, min_amt)
        if product_fee.max_amount is not None:
            max_amt = _to_decimal(product_fee.max_amount)
            amount = min(amount, max_amt)

    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_processing_fee(
    loan_account: "LoanAccount",
    db: Session
) -> Decimal:
    """
    Calculate processing fee for a loan account.

    Args:
        loan_account: Loan account
        db: Database session

    Returns:
        Processing fee amount
    """
    product_fee = get_product_fee(
        loan_account.application.product_id,
        "processing_fee",
        db
    )

    if not product_fee:
        # Fallback to product rate if no fee configuration
        from app.models.loan_product import LoanProduct
        product = db.query(LoanProduct).filter(
            LoanProduct.id == loan_account.application.product_id
        ).first()
        if product and product.processing_fee_rate:
            principal = _to_decimal(loan_account.principal_amount)
            rate = _to_decimal(product.processing_fee_rate)
            return (principal * rate / Decimal("100")).quantize(CENT, rounding=ROUND_HALF_UP)
        return Decimal("0")

    principal = _to_decimal(loan_account.principal_amount)
    return calculate_fee_amount(product_fee, principal)


def calculate_late_fee(
    loan_account: "LoanAccount",
    overdue_days: int,
    overdue_amount: Decimal,
    db: Session
) -> Decimal:
    """
    Calculate late fee based on overdue days and amount.

    Args:
        loan_account: Loan account
        overdue_days: Days past due
        overdue_amount: Overdue payment amount
        db: Database session

    Returns:
        Late fee amount (0 if within grace period)
    """
    product_fee = get_product_fee(
        loan_account.application.product_id,
        "late_fee",
        db
    )

    if not product_fee:
        # Fallback to product penalty rate
        from app.models.loan_product import LoanProduct
        product = db.query(LoanProduct).filter(
            LoanProduct.id == loan_account.application.product_id
        ).first()
        if product and product.penalty_rate:
            # Check grace period
            grace_days = product.grace_days or 0
            if overdue_days <= grace_days:
                return Decimal("0")
            rate = _to_decimal(product.penalty_rate)
            return (overdue_amount * rate / Decimal("100")).quantize(CENT, rounding=ROUND_HALF_UP)
        return Decimal("0")

    # Check grace period
    if overdue_days <= product_fee.grace_days:
        return Decimal("0")

    return calculate_fee_amount(product_fee, overdue_amount)


def calculate_prepayment_penalty(
    loan_account: "LoanAccount",
    prepay_amount: Decimal,
    db: Session
) -> Decimal:
    """
    Calculate prepayment penalty.

    Args:
        loan_account: Loan account
        prepay_amount: Amount being prepaid
        db: Database session

    Returns:
        Prepayment penalty amount
    """
    product_fee = get_product_fee(
        loan_account.application.product_id,
        "prepayment_penalty",
        db
    )

    if not product_fee:
        # Fallback to product prepayment penalty rate
        from app.models.loan_product import LoanProduct
        product = db.query(LoanProduct).filter(
            LoanProduct.id == loan_account.application.product_id
        ).first()
        if product and product.prepayment_penalty_rate:
            rate = _to_decimal(product.prepayment_penalty_rate)
            return (prepay_amount * rate / Decimal("100")).quantize(CENT, rounding=ROUND_HALF_UP)
        return Decimal("0")

    return calculate_fee_amount(product_fee, prepay_amount)


def charge_fee(
    loan_account_id: int,
    fee_type_id: int,
    amount: Decimal,
    charge_date: date,
    db: Session,
    schedule_id: int | None = None,
    reference_type: str | None = None,
    reference_id: int | None = None,
    notes: str | None = None
) -> FeeCharge:
    """
    Create a fee charge for a loan account.

    Args:
        loan_account_id: Loan account ID
        fee_type_id: Fee type ID
        amount: Fee amount
        charge_date: Date of charge
        db: Database session
        schedule_id: Optional related schedule item
        reference_type: Optional reference type
        reference_id: Optional reference ID
        notes: Optional notes

    Returns:
        Created FeeCharge record
    """
    fee_type = db.query(FeeType).filter(FeeType.id == fee_type_id).first()
    if not fee_type:
        raise ValueError(f"Fee type {fee_type_id} not found")

    # Calculate tax if applicable
    tax_amount = Decimal("0")
    if fee_type.taxable and fee_type.tax_rate:
        tax_rate = _to_decimal(fee_type.tax_rate)
        tax_amount = (amount * tax_rate / Decimal("100")).quantize(CENT, rounding=ROUND_HALF_UP)

    total_amount = (amount + tax_amount).quantize(CENT)

    fee_charge = FeeCharge(
        loan_account_id=loan_account_id,
        fee_type_id=fee_type_id,
        schedule_id=schedule_id,
        charge_date=charge_date,
        due_date=charge_date,
        amount=float(amount),
        tax_amount=float(tax_amount),
        total_amount=float(total_amount),
        outstanding_amount=float(total_amount),
        status="pending",
        reference_type=reference_type,
        reference_id=reference_id,
        notes=notes
    )

    db.add(fee_charge)
    db.commit()
    db.refresh(fee_charge)

    # Update loan account fees outstanding
    from app.models.loan_account import LoanAccount
    account = db.query(LoanAccount).filter(LoanAccount.id == loan_account_id).first()
    if account:
        account.fees_outstanding = float(
            _to_decimal(account.fees_outstanding or 0) + total_amount
        )
        db.commit()

    return fee_charge


def waive_fee(
    fee_charge_id: int,
    waive_amount: Decimal,
    waived_by: str,
    reason: str,
    db: Session
) -> FeeCharge:
    """
    Waive (partially or fully) a fee charge.

    Args:
        fee_charge_id: Fee charge ID
        waive_amount: Amount to waive
        waived_by: Who is waiving the fee
        reason: Reason for waiver
        db: Database session

    Returns:
        Updated FeeCharge record
    """
    from datetime import datetime

    fee_charge = db.query(FeeCharge).filter(FeeCharge.id == fee_charge_id).first()
    if not fee_charge:
        raise ValueError(f"Fee charge {fee_charge_id} not found")

    outstanding = _to_decimal(fee_charge.outstanding_amount)
    waive_amount = min(waive_amount, outstanding)

    fee_charge.waived_amount = float(_to_decimal(fee_charge.waived_amount or 0) + waive_amount)
    fee_charge.outstanding_amount = float(outstanding - waive_amount)
    fee_charge.waived_by = waived_by
    fee_charge.waived_at = datetime.now()
    fee_charge.waiver_reason = reason

    # Update status
    if _to_decimal(fee_charge.outstanding_amount) <= 0:
        fee_charge.status = "waived"
    elif _to_decimal(fee_charge.paid_amount) > 0:
        fee_charge.status = "partial"

    db.commit()
    db.refresh(fee_charge)

    # Update loan account fees outstanding
    from app.models.loan_account import LoanAccount
    account = db.query(LoanAccount).filter(LoanAccount.id == fee_charge.loan_account_id).first()
    if account:
        account.fees_outstanding = float(
            _to_decimal(account.fees_outstanding or 0) - waive_amount
        )
        db.commit()

    return fee_charge


def get_outstanding_fees(
    loan_account_id: int,
    db: Session
) -> list[FeeCharge]:
    """Get all outstanding fee charges for a loan account."""
    return db.query(FeeCharge).filter(
        and_(
            FeeCharge.loan_account_id == loan_account_id,
            FeeCharge.status.in_(["pending", "partial"])
        )
    ).order_by(FeeCharge.charge_date).all()


def get_fees_by_type(
    loan_account_id: int,
    fee_type_code: str,
    db: Session
) -> list[FeeCharge]:
    """Get all fees of a specific type for a loan account."""
    fee_type = get_fee_type_by_code(fee_type_code, db)
    if not fee_type:
        return []

    return db.query(FeeCharge).filter(
        and_(
            FeeCharge.loan_account_id == loan_account_id,
            FeeCharge.fee_type_id == fee_type.id
        )
    ).order_by(FeeCharge.charge_date).all()


def allocate_payment_to_fees(
    loan_account_id: int,
    payment_amount: Decimal,
    db: Session
) -> tuple[Decimal, list[dict]]:
    """
    Allocate payment amount to outstanding fees.

    Fees are paid in order of waterfall priority, then by charge date.

    Args:
        loan_account_id: Loan account ID
        payment_amount: Amount available for fee payment
        db: Database session

    Returns:
        Tuple of (remaining amount, list of allocations)
    """
    if payment_amount <= 0:
        return Decimal("0"), []

    # Get outstanding fees ordered by priority and date
    fees = db.query(FeeCharge).join(FeeType).filter(
        and_(
            FeeCharge.loan_account_id == loan_account_id,
            FeeCharge.status.in_(["pending", "partial"])
        )
    ).order_by(FeeType.waterfall_priority, FeeCharge.charge_date).all()

    remaining = payment_amount
    allocations = []

    for fee in fees:
        if remaining <= 0:
            break

        outstanding = _to_decimal(fee.outstanding_amount)
        allocation = min(remaining, outstanding)

        if allocation > 0:
            fee.paid_amount = float(_to_decimal(fee.paid_amount or 0) + allocation)
            fee.outstanding_amount = float(outstanding - allocation)

            if _to_decimal(fee.outstanding_amount) <= 0:
                fee.status = "paid"
            else:
                fee.status = "partial"

            allocations.append({
                "fee_charge_id": fee.id,
                "fee_type_id": fee.fee_type_id,
                "amount": float(allocation)
            })

            remaining -= allocation

    db.commit()

    # Update loan account fees outstanding
    from app.models.loan_account import LoanAccount
    account = db.query(LoanAccount).filter(LoanAccount.id == loan_account_id).first()
    if account and allocations:
        total_paid = sum(_to_decimal(a["amount"]) for a in allocations)
        account.fees_outstanding = float(
            max(_to_decimal(account.fees_outstanding or 0) - total_paid, Decimal("0"))
        )
        db.commit()

    return remaining.quantize(CENT), allocations
