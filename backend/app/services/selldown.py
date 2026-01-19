"""Selldown service for loan/investment transfers and sales."""
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any, List

from sqlalchemy.orm import Session

from app.models.selldown import (
    SelldownBuyer,
    SelldownTransaction,
    SelldownSettlement,
    SelldownCollectionSplit,
    SelldownPortfolioSummary,
)
from app.models.loan_account import LoanAccount
from app.models.loan_participation import LoanParticipation


def round_decimal(value: Decimal, places: int = 2) -> Decimal:
    """Round decimal to specified places using HALF_UP."""
    return value.quantize(Decimal(10) ** -places, rounding=ROUND_HALF_UP)


def calculate_sale_yield(
    sale_price: Decimal,
    face_value: Decimal,
    coupon_rate: Decimal,
    remaining_tenure_days: int,
    day_count_basis: int = 365,
) -> Decimal:
    """
    Calculate implied yield at sale price (simplified YTM approximation).

    For more accurate YTM, use Newton-Raphson or similar iterative method.
    """
    if sale_price <= 0 or remaining_tenure_days <= 0:
        return Decimal("0")

    years_to_maturity = Decimal(remaining_tenure_days) / Decimal(day_count_basis)

    if years_to_maturity == 0:
        return coupon_rate

    # Simplified YTM approximation
    # YTM ≈ (Coupon + (Face - Price) / Years) / ((Face + Price) / 2)
    annual_coupon = face_value * coupon_rate / Decimal("100")
    capital_gain_per_year = (face_value - sale_price) / years_to_maturity
    average_price = (face_value + sale_price) / Decimal("2")

    if average_price == 0:
        return Decimal("0")

    ytm = ((annual_coupon + capital_gain_per_year) / average_price) * Decimal("100")
    return round_decimal(ytm, 4)


def calculate_gain_loss(
    sale_price: Decimal,
    book_value: Decimal,
) -> Dict[str, Decimal]:
    """Calculate gain/loss on sale."""
    gain_loss = sale_price - book_value
    gain_loss_percent = Decimal("0")

    if book_value > 0:
        gain_loss_percent = (gain_loss / book_value) * Decimal("100")

    return {
        "gain_loss": round_decimal(gain_loss),
        "gain_loss_percent": round_decimal(gain_loss_percent, 4),
    }


def initiate_loan_selldown(
    db: Session,
    loan_account_id: int,
    buyer_id: int,
    selldown_percent: Decimal,
    sale_price: Decimal,
    transaction_date: date,
    value_date: date,
    servicing_retained: bool = True,
    servicer_fee_rate: Optional[Decimal] = None,
    seller_partner_id: Optional[int] = None,
    initiated_by: Optional[str] = None,
    remarks: Optional[str] = None,
) -> SelldownTransaction:
    """
    Initiate a selldown transaction for a loan.

    Args:
        db: Database session
        loan_account_id: ID of loan being sold
        buyer_id: ID of buyer
        selldown_percent: Percentage being sold (100 for full, <100 for partial)
        sale_price: Total sale consideration
        transaction_date: Date of transaction
        value_date: Settlement date
        servicing_retained: Whether seller continues servicing
        servicer_fee_rate: Annual servicing fee rate if retained
        seller_partner_id: Partner ID of seller (for co-lending scenarios)
        initiated_by: User initiating the transaction
        remarks: Additional remarks

    Returns:
        Created SelldownTransaction
    """
    # Get loan details
    loan = db.query(LoanAccount).filter(LoanAccount.id == loan_account_id).first()
    if not loan:
        raise ValueError(f"Loan account {loan_account_id} not found")

    # Calculate outstanding amounts
    outstanding_principal = loan.principal_outstanding or Decimal("0")
    accrued_interest = loan.interest_outstanding or Decimal("0")
    outstanding_fees = loan.fees_outstanding or Decimal("0")
    total_outstanding = outstanding_principal + accrued_interest + outstanding_fees

    # Calculate selldown amounts
    selldown_principal = round_decimal(outstanding_principal * selldown_percent / Decimal("100"))
    selldown_interest = round_decimal(accrued_interest * selldown_percent / Decimal("100"))
    selldown_fees = round_decimal(outstanding_fees * selldown_percent / Decimal("100"))

    # Calculate price percentage
    book_value = selldown_principal + selldown_interest
    price_percent = Decimal("100")
    if book_value > 0:
        price_percent = round_decimal((sale_price / book_value) * Decimal("100"), 4)

    # Calculate premium/discount
    premium_discount = sale_price - book_value

    # Calculate gain/loss
    gl_result = calculate_gain_loss(sale_price, book_value)

    # Calculate yields
    original_yield = loan.interest_rate or Decimal("0")
    remaining_days = (loan.maturity_date - transaction_date).days if loan.maturity_date else 0
    sale_yield = calculate_sale_yield(
        sale_price, selldown_principal, original_yield, remaining_days
    )
    yield_spread = original_yield - sale_yield

    # Determine transaction type
    transaction_type = "full_selldown" if selldown_percent >= Decimal("100") else "partial_selldown"

    # Generate transaction code
    transaction_code = f"SD{loan_account_id}{transaction_date.strftime('%Y%m%d')}{buyer_id}"

    # Create transaction
    transaction = SelldownTransaction(
        transaction_code=transaction_code,
        transaction_type=transaction_type,
        asset_type="loan",
        loan_account_id=loan_account_id,
        buyer_id=buyer_id,
        seller_partner_id=seller_partner_id,
        transaction_date=transaction_date,
        value_date=value_date,
        original_principal=loan.principal_amount,
        outstanding_principal=outstanding_principal,
        accrued_interest=accrued_interest,
        outstanding_fees=outstanding_fees,
        total_outstanding=total_outstanding,
        selldown_percent=selldown_percent,
        selldown_principal=selldown_principal,
        selldown_interest=selldown_interest,
        selldown_fees=selldown_fees,
        sale_price=sale_price,
        price_percent=price_percent,
        premium_discount=premium_discount,
        original_yield=original_yield,
        sale_yield=sale_yield,
        yield_spread=yield_spread,
        book_value=book_value,
        gain_loss=gl_result["gain_loss"],
        gain_loss_percent=gl_result["gain_loss_percent"],
        retained_percent=Decimal("100") - selldown_percent,
        retained_principal=outstanding_principal - selldown_principal,
        servicing_retained=servicing_retained,
        servicer_fee_rate=servicer_fee_rate,
        status="initiated",
        initiated_by=initiated_by,
        remarks=remarks,
    )

    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    return transaction


def initiate_investment_selldown(
    db: Session,
    investment_id: int,
    buyer_id: int,
    units_to_sell: Decimal,
    sale_price_per_unit: Decimal,
    transaction_date: date,
    value_date: date,
    seller_partner_id: Optional[int] = None,
    initiated_by: Optional[str] = None,
    remarks: Optional[str] = None,
) -> SelldownTransaction:
    """
    Initiate a selldown transaction for an investment (NCD, CP, Bond, etc.).

    Args:
        db: Database session
        investment_id: ID of investment being sold
        buyer_id: ID of buyer
        units_to_sell: Number of units to sell
        sale_price_per_unit: Price per unit
        transaction_date: Date of transaction
        value_date: Settlement date
        seller_partner_id: Partner ID of seller
        initiated_by: User initiating the transaction
        remarks: Additional remarks

    Returns:
        Created SelldownTransaction
    """
    from app.models.investment import Investment

    # Get investment details
    investment = db.query(Investment).filter(Investment.id == investment_id).first()
    if not investment:
        raise ValueError(f"Investment {investment_id} not found")

    if units_to_sell > investment.units_held:
        raise ValueError(f"Cannot sell {units_to_sell} units, only {investment.units_held} held")

    # Calculate amounts
    face_value_sold = units_to_sell * investment.face_value_per_unit
    sale_price = units_to_sell * sale_price_per_unit
    book_value_per_unit = investment.amortized_cost / investment.units_held if investment.units_held > 0 else Decimal("0")
    book_value = units_to_sell * book_value_per_unit

    # Accrued interest
    accrued_per_unit = investment.accrued_interest / investment.units_held if investment.units_held > 0 else Decimal("0")
    accrued_interest = units_to_sell * accrued_per_unit

    # Selldown percentage
    selldown_percent = (units_to_sell / investment.original_units) * Decimal("100")

    # Price percentage
    price_percent = Decimal("100")
    if book_value > 0:
        price_percent = round_decimal((sale_price / book_value) * Decimal("100"), 4)

    # Premium/discount
    premium_discount = sale_price - book_value

    # Gain/loss
    gl_result = calculate_gain_loss(sale_price, book_value)

    # Yields
    original_yield = investment.purchase_yield or investment.coupon_rate
    remaining_days = (investment.maturity_date - transaction_date).days if investment.maturity_date else 0
    sale_yield = calculate_sale_yield(
        sale_price_per_unit, investment.face_value_per_unit, investment.coupon_rate, remaining_days
    )

    # Transaction type
    transaction_type = "full_selldown" if units_to_sell >= investment.units_held else "partial_selldown"

    # Generate transaction code
    transaction_code = f"SDI{investment_id}{transaction_date.strftime('%Y%m%d')}{buyer_id}"

    # Create transaction
    transaction = SelldownTransaction(
        transaction_code=transaction_code,
        transaction_type=transaction_type,
        asset_type="investment",
        investment_id=investment_id,
        buyer_id=buyer_id,
        seller_partner_id=seller_partner_id,
        transaction_date=transaction_date,
        value_date=value_date,
        original_principal=investment.total_face_value,
        outstanding_principal=face_value_sold,
        accrued_interest=round_decimal(accrued_interest),
        outstanding_fees=Decimal("0"),
        total_outstanding=face_value_sold + accrued_interest,
        selldown_percent=round_decimal(selldown_percent, 4),
        selldown_principal=round_decimal(face_value_sold),
        selldown_interest=round_decimal(accrued_interest),
        selldown_fees=Decimal("0"),
        sale_price=round_decimal(sale_price),
        price_percent=price_percent,
        premium_discount=round_decimal(premium_discount),
        original_yield=original_yield,
        sale_yield=sale_yield,
        yield_spread=original_yield - sale_yield if sale_yield else Decimal("0"),
        book_value=round_decimal(book_value),
        gain_loss=gl_result["gain_loss"],
        gain_loss_percent=gl_result["gain_loss_percent"],
        retained_percent=Decimal("100") - selldown_percent,
        retained_principal=investment.total_face_value - face_value_sold,
        servicing_retained=False,
        status="initiated",
        initiated_by=initiated_by,
        remarks=remarks,
    )

    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    return transaction


def approve_selldown(
    db: Session,
    transaction_id: int,
    approved_by: str,
) -> SelldownTransaction:
    """Approve a selldown transaction."""
    transaction = db.query(SelldownTransaction).filter(
        SelldownTransaction.id == transaction_id
    ).first()

    if not transaction:
        raise ValueError(f"Transaction {transaction_id} not found")

    if transaction.status != "initiated":
        raise ValueError(f"Transaction status is {transaction.status}, cannot approve")

    transaction.status = "approved"
    transaction.approved_by = approved_by
    transaction.approved_at = datetime.utcnow()

    db.commit()
    db.refresh(transaction)

    return transaction


def settle_selldown(
    db: Session,
    transaction_id: int,
    settlement_reference: str,
    settlement_bank_reference: Optional[str] = None,
) -> SelldownTransaction:
    """
    Settle a selldown transaction and update underlying asset.

    This will:
    1. Update transaction status to settled
    2. Update loan/investment records
    3. Update buyer exposure
    4. Create settlement records
    """
    transaction = db.query(SelldownTransaction).filter(
        SelldownTransaction.id == transaction_id
    ).first()

    if not transaction:
        raise ValueError(f"Transaction {transaction_id} not found")

    if transaction.status != "approved":
        raise ValueError(f"Transaction status is {transaction.status}, must be approved first")

    # Update transaction
    transaction.status = "settled"
    transaction.settled_at = datetime.utcnow()
    transaction.settlement_reference = settlement_reference
    transaction.settlement_bank_reference = settlement_bank_reference

    # Update buyer exposure
    buyer = db.query(SelldownBuyer).filter(SelldownBuyer.id == transaction.buyer_id).first()
    if buyer:
        buyer.current_exposure = (buyer.current_exposure or Decimal("0")) + transaction.selldown_principal

    # Update underlying asset
    if transaction.asset_type == "loan" and transaction.loan_account_id:
        _update_loan_after_selldown(db, transaction)
    elif transaction.asset_type == "investment" and transaction.investment_id:
        _update_investment_after_selldown(db, transaction)

    # Create settlement record
    settlement = SelldownSettlement(
        selldown_transaction_id=transaction.id,
        settlement_date=transaction.value_date,
        settlement_type="principal",
        gross_amount=transaction.sale_price,
        tds_amount=Decimal("0"),
        gst_amount=Decimal("0"),
        other_deductions=Decimal("0"),
        net_amount=transaction.sale_price,
        payment_direction="buyer_to_seller",
        payment_reference=settlement_reference,
        status="completed",
    )
    db.add(settlement)

    db.commit()
    db.refresh(transaction)

    return transaction


def _update_loan_after_selldown(db: Session, transaction: SelldownTransaction):
    """Update loan account after selldown settlement."""
    loan = db.query(LoanAccount).filter(
        LoanAccount.id == transaction.loan_account_id
    ).first()

    if not loan:
        return

    if transaction.transaction_type == "full_selldown":
        # Full selldown - mark loan as sold
        loan.status = "sold"
        loan.closure_date = transaction.value_date
    else:
        # Partial selldown - reduce outstanding
        # The loan continues but with reduced exposure
        pass  # Participation tracking handles this


def _update_investment_after_selldown(db: Session, transaction: SelldownTransaction):
    """Update investment after selldown settlement."""
    from app.models.investment import Investment, InvestmentTransaction

    investment = db.query(Investment).filter(
        Investment.id == transaction.investment_id
    ).first()

    if not investment:
        return

    # Calculate units sold
    units_sold = transaction.selldown_principal / investment.face_value_per_unit if investment.face_value_per_unit > 0 else Decimal("0")

    # Update investment
    investment.sold_units = (investment.sold_units or Decimal("0")) + units_sold
    investment.units_held = investment.units_held - units_sold
    investment.total_face_value = investment.units_held * investment.face_value_per_unit

    # Adjust amortized cost proportionally
    if investment.original_units > 0:
        cost_per_unit = investment.amortized_cost / (investment.units_held + units_sold)
        investment.amortized_cost = investment.units_held * cost_per_unit

    # Adjust accrued interest proportionally
    if investment.units_held > 0:
        investment.accrued_interest = investment.accrued_interest * (investment.units_held / (investment.units_held + units_sold))
    else:
        investment.accrued_interest = Decimal("0")

    # Update status if fully sold
    if investment.units_held <= 0:
        investment.status = "sold"
        investment.closure_date = transaction.value_date
        investment.closure_type = "sale"

    # Create investment transaction record
    inv_transaction = InvestmentTransaction(
        investment_id=investment.id,
        transaction_code=f"INV{transaction.transaction_code}",
        transaction_type="sale" if transaction.transaction_type == "full_selldown" else "partial_sale",
        transaction_date=transaction.transaction_date,
        value_date=transaction.value_date,
        units=units_sold,
        price_per_unit=transaction.sale_price / units_sold if units_sold > 0 else Decimal("0"),
        face_value=transaction.selldown_principal,
        consideration=transaction.sale_price,
        accrued_interest=transaction.selldown_interest,
        total_amount=transaction.sale_price + transaction.selldown_interest,
        book_value=transaction.book_value,
        gain_loss=transaction.gain_loss,
        settlement_status="completed",
        settlement_date=transaction.value_date,
        settlement_reference=transaction.settlement_reference,
    )
    db.add(inv_transaction)


def split_collection_for_selldown(
    db: Session,
    transaction_id: int,
    collection_date: date,
    principal_collected: Decimal,
    interest_collected: Decimal,
    fees_collected: Decimal = Decimal("0"),
    collection_reference: Optional[str] = None,
) -> SelldownCollectionSplit:
    """
    Split a collection between seller and buyer based on selldown arrangement.

    Used when servicing is retained by seller post-selldown.
    """
    transaction = db.query(SelldownTransaction).filter(
        SelldownTransaction.id == transaction_id
    ).first()

    if not transaction:
        raise ValueError(f"Transaction {transaction_id} not found")

    if transaction.status != "settled":
        raise ValueError("Transaction must be settled before collection split")

    total_collection = principal_collected + interest_collected + fees_collected

    # Calculate buyer's share based on selldown percentage
    buyer_share_pct = transaction.selldown_percent / Decimal("100")
    seller_share_pct = transaction.retained_percent / Decimal("100")

    buyer_principal = round_decimal(principal_collected * buyer_share_pct)
    buyer_interest = round_decimal(interest_collected * buyer_share_pct)
    buyer_fees = round_decimal(fees_collected * buyer_share_pct)
    buyer_total = buyer_principal + buyer_interest + buyer_fees

    seller_principal = principal_collected - buyer_principal
    seller_interest = interest_collected - buyer_interest
    seller_fees = fees_collected - buyer_fees
    seller_total = seller_principal + seller_interest + seller_fees

    # Calculate servicer fee if applicable
    servicer_fee = Decimal("0")
    servicer_fee_gst = Decimal("0")

    if transaction.servicing_retained and transaction.servicer_fee_rate:
        # Servicer fee on buyer's share (typically annual rate, prorated)
        # Simplified: calculated on interest component
        servicer_fee = round_decimal(buyer_interest * transaction.servicer_fee_rate / Decimal("100"))
        servicer_fee_gst = round_decimal(servicer_fee * Decimal("0.18"))  # 18% GST

    net_to_buyer = buyer_total - servicer_fee - servicer_fee_gst

    # Create split record
    split = SelldownCollectionSplit(
        selldown_transaction_id=transaction_id,
        collection_date=collection_date,
        collection_reference=collection_reference,
        total_principal_collected=principal_collected,
        total_interest_collected=interest_collected,
        total_fees_collected=fees_collected,
        total_collection=total_collection,
        buyer_principal_share=buyer_principal,
        buyer_interest_share=buyer_interest,
        buyer_fees_share=buyer_fees,
        buyer_total_share=buyer_total,
        seller_principal_share=seller_principal,
        seller_interest_share=seller_interest,
        seller_fees_share=seller_fees,
        seller_total_share=seller_total,
        servicer_fee_amount=servicer_fee,
        servicer_fee_gst=servicer_fee_gst,
        net_to_buyer=net_to_buyer,
        remittance_status="pending",
    )

    db.add(split)
    db.commit()
    db.refresh(split)

    return split


def get_selldown_portfolio_summary(
    db: Session,
    buyer_id: int,
    as_of_date: date,
) -> Dict[str, Any]:
    """Get portfolio summary for a buyer."""
    transactions = db.query(SelldownTransaction).filter(
        SelldownTransaction.buyer_id == buyer_id,
        SelldownTransaction.status == "settled",
        SelldownTransaction.transaction_date <= as_of_date,
    ).all()

    summary = {
        "buyer_id": buyer_id,
        "as_of_date": as_of_date,
        "total_transactions": len(transactions),
        "total_loans_sold": 0,
        "total_investments_sold": 0,
        "total_principal": Decimal("0"),
        "total_consideration_paid": Decimal("0"),
        "total_gain_loss": Decimal("0"),
        "by_asset_type": {},
    }

    for txn in transactions:
        if txn.asset_type == "loan":
            summary["total_loans_sold"] += 1
        else:
            summary["total_investments_sold"] += 1

        summary["total_principal"] += txn.selldown_principal
        summary["total_consideration_paid"] += txn.sale_price
        summary["total_gain_loss"] += txn.gain_loss

        # Group by asset type
        if txn.asset_type not in summary["by_asset_type"]:
            summary["by_asset_type"][txn.asset_type] = {
                "count": 0,
                "principal": Decimal("0"),
                "consideration": Decimal("0"),
            }
        summary["by_asset_type"][txn.asset_type]["count"] += 1
        summary["by_asset_type"][txn.asset_type]["principal"] += txn.selldown_principal
        summary["by_asset_type"][txn.asset_type]["consideration"] += txn.sale_price

    return summary


def cancel_selldown(
    db: Session,
    transaction_id: int,
    cancellation_reason: str,
) -> SelldownTransaction:
    """Cancel a selldown transaction (only if not yet settled)."""
    transaction = db.query(SelldownTransaction).filter(
        SelldownTransaction.id == transaction_id
    ).first()

    if not transaction:
        raise ValueError(f"Transaction {transaction_id} not found")

    if transaction.status == "settled":
        raise ValueError("Cannot cancel a settled transaction")

    transaction.status = "cancelled"
    transaction.cancellation_reason = cancellation_reason

    db.commit()
    db.refresh(transaction)

    return transaction
