"""
Supply chain finance service.

Handles:
- Invoice financing
- Credit limit management
- Payment matching
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.supply_chain import Counterparty, Invoice, CreditLimit

CENT = Decimal("0.01")


def _to_decimal(value: float | Decimal | int | None) -> Decimal:
    """Convert numeric value to Decimal."""
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def create_counterparty(
    counterparty_type: str,
    name: str,
    registration_number: str,
    tax_id: str | None = None,
    credit_limit: float = 0,
    borrower_id: int | None = None,
    db: Session = None
) -> Counterparty:
    """
    Create a new counterparty.

    Args:
        counterparty_type: buyer, supplier, or anchor
        name: Company name
        registration_number: Company registration number
        tax_id: Tax identification number
        credit_limit: Initial credit limit
        borrower_id: Optional linked borrower
        db: Database session

    Returns:
        Created Counterparty
    """
    counterparty = Counterparty(
        counterparty_type=counterparty_type,
        name=name,
        registration_number=registration_number,
        tax_id=tax_id,
        credit_limit=credit_limit,
        credit_limit_available=credit_limit,
        borrower_id=borrower_id,
        status="active"
    )

    db.add(counterparty)
    db.commit()
    db.refresh(counterparty)

    return counterparty


def set_credit_limit(
    counterparty_id: int,
    limit_amount: float,
    limit_type: str = "overall",
    effective_date: date = None,
    expiry_date: date = None,
    product_id: int | None = None,
    approved_by: str | None = None,
    db: Session = None
) -> CreditLimit:
    """
    Set or update credit limit for a counterparty.

    Args:
        counterparty_id: Counterparty ID
        limit_amount: Credit limit amount
        limit_type: Type of limit
        effective_date: Start date
        expiry_date: End date
        product_id: For product-specific limits
        approved_by: Approver
        db: Database session

    Returns:
        Created CreditLimit
    """
    from datetime import datetime

    counterparty = db.query(Counterparty).filter(
        Counterparty.id == counterparty_id
    ).first()

    if not counterparty:
        raise ValueError(f"Counterparty {counterparty_id} not found")

    # Expire existing limits of same type
    db.query(CreditLimit).filter(
        and_(
            CreditLimit.counterparty_id == counterparty_id,
            CreditLimit.limit_type == limit_type,
            CreditLimit.status == "active"
        )
    ).update({"status": "expired"})

    credit_limit = CreditLimit(
        counterparty_id=counterparty_id,
        limit_type=limit_type,
        product_id=product_id,
        limit_amount=limit_amount,
        utilized_amount=0,
        available_amount=limit_amount,
        effective_date=effective_date or date.today(),
        expiry_date=expiry_date,
        approved_by=approved_by,
        approved_at=datetime.utcnow() if approved_by else None,
        status="active"
    )

    db.add(credit_limit)

    # Update counterparty overall limit
    if limit_type == "overall":
        counterparty.credit_limit = limit_amount
        counterparty.credit_limit_available = limit_amount - float(counterparty.credit_limit_utilized)

    db.commit()
    db.refresh(credit_limit)

    return credit_limit


def create_invoice(
    invoice_number: str,
    buyer_id: int,
    supplier_id: int,
    invoice_date: date,
    due_date: date,
    invoice_amount: float,
    tax_amount: float = 0,
    currency: str = "INR",
    advance_rate: float = 80,
    db: Session = None
) -> Invoice:
    """
    Create a new invoice for financing.

    Args:
        invoice_number: Invoice number
        buyer_id: Buyer counterparty ID
        supplier_id: Supplier counterparty ID
        invoice_date: Invoice date
        due_date: Payment due date
        invoice_amount: Invoice amount
        tax_amount: Tax amount
        currency: Currency code
        advance_rate: Advance percentage for financing
        db: Database session

    Returns:
        Created Invoice
    """
    total_amount = _to_decimal(invoice_amount) + _to_decimal(tax_amount)

    invoice = Invoice(
        invoice_number=invoice_number,
        buyer_id=buyer_id,
        supplier_id=supplier_id,
        invoice_date=invoice_date,
        due_date=due_date,
        invoice_amount=invoice_amount,
        tax_amount=tax_amount,
        total_amount=float(total_amount),
        currency=currency,
        advance_rate=advance_rate,
        status="pending"
    )

    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    return invoice


def accept_invoice(
    invoice_id: int,
    acceptance_date: date,
    db: Session
) -> Invoice:
    """
    Mark invoice as accepted by buyer.

    Args:
        invoice_id: Invoice ID
        acceptance_date: Date of acceptance
        db: Database session

    Returns:
        Updated Invoice
    """
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id
    ).first()

    if not invoice:
        raise ValueError(f"Invoice {invoice_id} not found")

    if invoice.status != "pending":
        raise ValueError(f"Invoice {invoice_id} is not pending")

    invoice.acceptance_date = acceptance_date
    invoice.status = "accepted"

    db.commit()
    db.refresh(invoice)

    return invoice


def finance_invoice(
    invoice_id: int,
    loan_account_id: int,
    financing_date: date,
    financed_amount: float | None = None,
    db: Session = None
) -> Invoice:
    """
    Finance an invoice by linking to a loan account.

    Args:
        invoice_id: Invoice ID
        loan_account_id: Loan account created for financing
        financing_date: Date of financing
        financed_amount: Amount financed (default: advance_rate * total)
        db: Database session

    Returns:
        Updated Invoice
    """
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id
    ).first()

    if not invoice:
        raise ValueError(f"Invoice {invoice_id} not found")

    if invoice.status not in ["pending", "accepted"]:
        raise ValueError(f"Invoice {invoice_id} cannot be financed")

    # Calculate financed amount
    if financed_amount is None:
        financed_amount = float(
            (_to_decimal(invoice.total_amount) *
             _to_decimal(invoice.advance_rate) / 100).quantize(CENT)
        )

    # Check buyer's credit limit
    buyer = invoice.buyer
    limit_required = _to_decimal(financed_amount)

    if _to_decimal(buyer.credit_limit_available) < limit_required:
        raise ValueError(
            f"Insufficient credit limit. Required: {limit_required}, "
            f"Available: {buyer.credit_limit_available}"
        )

    # Update invoice
    invoice.loan_account_id = loan_account_id
    invoice.financing_date = financing_date
    invoice.financed_amount = financed_amount
    invoice.status = "financed"

    # Update buyer's credit utilization
    buyer.credit_limit_utilized = float(
        _to_decimal(buyer.credit_limit_utilized) + limit_required
    )
    buyer.credit_limit_available = float(
        _to_decimal(buyer.credit_limit) - _to_decimal(buyer.credit_limit_utilized)
    )

    db.commit()
    db.refresh(invoice)

    return invoice


def record_invoice_payment(
    invoice_id: int,
    payment_amount: float,
    payment_date: date,
    db: Session
) -> Invoice:
    """
    Record payment received for an invoice.

    Args:
        invoice_id: Invoice ID
        payment_amount: Amount received
        payment_date: Date of payment
        db: Database session

    Returns:
        Updated Invoice
    """
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id
    ).first()

    if not invoice:
        raise ValueError(f"Invoice {invoice_id} not found")

    if invoice.status not in ["financed", "partially_paid"]:
        raise ValueError(f"Invoice {invoice_id} is not financed")

    total_paid = _to_decimal(invoice.paid_amount) + _to_decimal(payment_amount)
    invoice.paid_amount = float(total_paid)
    invoice.payment_date = payment_date

    total_amount = _to_decimal(invoice.total_amount)

    if total_paid >= total_amount:
        invoice.status = "paid"
        # Release credit limit
        buyer = invoice.buyer
        financed = _to_decimal(invoice.financed_amount)
        buyer.credit_limit_utilized = float(
            max(Decimal("0"), _to_decimal(buyer.credit_limit_utilized) - financed)
        )
        buyer.credit_limit_available = float(
            _to_decimal(buyer.credit_limit) - _to_decimal(buyer.credit_limit_utilized)
        )
    else:
        invoice.status = "partially_paid"

    db.commit()
    db.refresh(invoice)

    return invoice


def record_dilution(
    invoice_id: int,
    dilution_amount: float,
    reason: str,
    db: Session
) -> Invoice:
    """
    Record dilution (reduction) on an invoice.

    Args:
        invoice_id: Invoice ID
        dilution_amount: Amount of dilution
        reason: Reason for dilution
        db: Database session

    Returns:
        Updated Invoice
    """
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id
    ).first()

    if not invoice:
        raise ValueError(f"Invoice {invoice_id} not found")

    invoice.dilution_amount = float(
        _to_decimal(invoice.dilution_amount) + _to_decimal(dilution_amount)
    )
    invoice.dilution_reason = reason

    db.commit()
    db.refresh(invoice)

    return invoice


def get_counterparty_exposure(
    counterparty_id: int,
    db: Session
) -> dict:
    """
    Get total exposure for a counterparty.

    Args:
        counterparty_id: Counterparty ID
        db: Database session

    Returns:
        Exposure summary
    """
    counterparty = db.query(Counterparty).filter(
        Counterparty.id == counterparty_id
    ).first()

    if not counterparty:
        raise ValueError(f"Counterparty {counterparty_id} not found")

    # Get financed invoices
    if counterparty.counterparty_type == "buyer":
        invoices = db.query(Invoice).filter(
            and_(
                Invoice.buyer_id == counterparty_id,
                Invoice.status.in_(["financed", "partially_paid"])
            )
        ).all()
    else:
        invoices = db.query(Invoice).filter(
            and_(
                Invoice.supplier_id == counterparty_id,
                Invoice.status.in_(["financed", "partially_paid"])
            )
        ).all()

    total_financed = sum(_to_decimal(i.financed_amount) for i in invoices)
    total_outstanding = sum(
        _to_decimal(i.financed_amount) - _to_decimal(i.paid_amount)
        for i in invoices
    )

    return {
        "counterparty_id": counterparty_id,
        "counterparty_name": counterparty.name,
        "counterparty_type": counterparty.counterparty_type,
        "credit_limit": float(counterparty.credit_limit),
        "credit_utilized": float(counterparty.credit_limit_utilized),
        "credit_available": float(counterparty.credit_limit_available),
        "active_invoices": len(invoices),
        "total_financed": float(total_financed),
        "total_outstanding": float(total_outstanding)
    }


def get_overdue_invoices(
    as_of_date: date,
    db: Session,
    buyer_id: int | None = None,
    supplier_id: int | None = None
) -> list[dict]:
    """
    Get overdue invoices.

    Args:
        as_of_date: Date to check against
        db: Database session
        buyer_id: Optional buyer filter
        supplier_id: Optional supplier filter

    Returns:
        List of overdue invoice summaries
    """
    query = db.query(Invoice).filter(
        and_(
            Invoice.status.in_(["financed", "partially_paid"]),
            Invoice.due_date < as_of_date
        )
    )

    if buyer_id:
        query = query.filter(Invoice.buyer_id == buyer_id)
    if supplier_id:
        query = query.filter(Invoice.supplier_id == supplier_id)

    invoices = query.all()

    return [
        {
            "invoice_id": i.id,
            "invoice_number": i.invoice_number,
            "buyer_id": i.buyer_id,
            "supplier_id": i.supplier_id,
            "total_amount": float(i.total_amount),
            "financed_amount": float(i.financed_amount),
            "paid_amount": float(i.paid_amount),
            "outstanding": float(_to_decimal(i.financed_amount) - _to_decimal(i.paid_amount)),
            "due_date": i.due_date,
            "days_overdue": (as_of_date - i.due_date).days
        }
        for i in invoices
    ]
