"""
Servicer Income service.

Handles:
- Servicer fee calculation
- Excess spread calculation and tracking
- Income distribution
- Withholding from collections
"""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models.servicer_income import (
    ExcessSpreadTracking,
    ServicerArrangement,
    ServicerIncomeAccrual,
    ServicerIncomeDistribution,
    WithholdingTracker,
)
from app.models.loan_account import LoanAccount
from app.models.loan_participation import LoanParticipation
from app.models.payment import Payment


def create_servicer_arrangement(
    arrangement_code: str,
    name: str,
    servicer_id: int,
    lender_id: int,
    servicer_fee_rate: float,
    effective_date: date,
    db: Session,
    **kwargs
) -> ServicerArrangement:
    """
    Create a new servicer arrangement.
    """
    arrangement = ServicerArrangement(
        arrangement_code=arrangement_code,
        name=name,
        servicer_id=servicer_id,
        lender_id=lender_id,
        servicer_fee_rate=servicer_fee_rate,
        effective_date=effective_date,
        **kwargs
    )
    db.add(arrangement)
    db.flush()
    return arrangement


def calculate_servicer_fee(
    arrangement_id: int,
    period_start: date,
    period_end: date,
    db: Session
) -> dict:
    """
    Calculate servicer fee for a period.

    Fee = Outstanding Principal * Rate * (Days / 365)
    """
    arrangement = db.query(ServicerArrangement).get(arrangement_id)
    if not arrangement:
        raise ValueError(f"Arrangement {arrangement_id} not found")

    # Get portfolio outstanding (loans linked to this arrangement)
    participations = db.query(LoanParticipation).filter(
        LoanParticipation.servicer_arrangement_id == arrangement_id
    ).all()

    total_outstanding = Decimal("0")
    for p in participations:
        loan = db.query(LoanAccount).get(p.loan_account_id)
        if loan and loan.status in ["active", "delinquent"]:
            total_outstanding += Decimal(str(loan.principal_outstanding))

    days = (period_end - period_start).days + 1
    rate = Decimal(str(arrangement.servicer_fee_rate))

    # Fee calculation
    if arrangement.servicer_fee_calculation == "outstanding_principal":
        fee_base = total_outstanding
    else:
        fee_base = total_outstanding  # Simplified - could be original principal

    servicer_fee = (
        fee_base * rate / Decimal("100") * Decimal(str(days)) / Decimal("365")
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Check minimum fee
    if arrangement.min_servicer_fee_monthly:
        min_fee = Decimal(str(arrangement.min_servicer_fee_monthly))
        servicer_fee = max(servicer_fee, min_fee)

    # GST on servicer fee (18%)
    gst = (servicer_fee * Decimal("18") / Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    return {
        "period_start": period_start,
        "period_end": period_end,
        "portfolio_outstanding": total_outstanding,
        "servicer_fee_rate": rate,
        "days": days,
        "servicer_fee": servicer_fee,
        "gst": gst,
        "total_servicer_fee": servicer_fee + gst
    }


def calculate_excess_spread(
    loan_account_id: int,
    participation_id: int,
    period_start: date,
    period_end: date,
    db: Session
) -> dict:
    """
    Calculate excess interest spread for a loan.

    Excess Spread = (Borrower Rate - Lender Yield) * Outstanding * Days / 365
    """
    loan = db.query(LoanAccount).get(loan_account_id)
    participation = db.query(LoanParticipation).get(participation_id)

    if not loan or not participation:
        raise ValueError("Invalid loan or participation")

    borrower_rate = Decimal(str(loan.interest_rate))
    lender_yield = Decimal(str(participation.interest_rate or borrower_rate))

    excess_rate = borrower_rate - lender_yield

    if excess_rate <= 0:
        return {
            "borrower_rate": borrower_rate,
            "lender_yield": lender_yield,
            "excess_spread_rate": Decimal("0"),
            "excess_spread_amount": Decimal("0"),
            "servicer_share": Decimal("0"),
            "lender_share": Decimal("0")
        }

    days = (period_end - period_start).days + 1
    outstanding = Decimal(str(loan.principal_outstanding))

    excess_amount = (
        outstanding * excess_rate / Decimal("100") * Decimal(str(days)) / Decimal("365")
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Get sharing arrangement
    arrangement = None
    if participation.servicer_arrangement_id:
        arrangement = db.query(ServicerArrangement).get(participation.servicer_arrangement_id)

    servicer_share_pct = Decimal("100")  # Default all to servicer
    if arrangement and arrangement.excess_spread_servicer_share:
        servicer_share_pct = Decimal(str(arrangement.excess_spread_servicer_share))

    servicer_share = (
        excess_amount * servicer_share_pct / Decimal("100")
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    lender_share = excess_amount - servicer_share

    return {
        "borrower_rate": borrower_rate,
        "lender_yield": lender_yield,
        "excess_spread_rate": excess_rate,
        "principal_outstanding": outstanding,
        "days": days,
        "excess_spread_amount": excess_amount,
        "servicer_share_percent": servicer_share_pct,
        "servicer_share": servicer_share,
        "lender_share": lender_share
    }


def track_excess_spread(
    loan_account_id: int,
    participation_id: int,
    tracking_date: date,
    period_start: date,
    period_end: date,
    db: Session
) -> ExcessSpreadTracking:
    """
    Record excess spread tracking entry for a loan.
    """
    spread_result = calculate_excess_spread(
        loan_account_id, participation_id, period_start, period_end, db
    )

    # Get cumulative
    prev = db.query(ExcessSpreadTracking).filter(
        and_(
            ExcessSpreadTracking.loan_account_id == loan_account_id,
            ExcessSpreadTracking.participation_id == participation_id,
            ExcessSpreadTracking.tracking_date < tracking_date
        )
    ).order_by(ExcessSpreadTracking.tracking_date.desc()).first()

    cumulative = Decimal(str(prev.cumulative_excess_spread)) if prev else Decimal("0")
    cumulative += spread_result["servicer_share"]

    tracking = ExcessSpreadTracking(
        loan_account_id=loan_account_id,
        participation_id=participation_id,
        tracking_date=tracking_date,
        period_start=period_start,
        period_end=period_end,
        borrower_interest_rate=float(spread_result["borrower_rate"]),
        lender_yield_rate=float(spread_result["lender_yield"]),
        excess_spread_rate=float(spread_result["excess_spread_rate"]),
        principal_outstanding=float(spread_result.get("principal_outstanding", 0)),
        average_principal=float(spread_result.get("principal_outstanding", 0)),
        gross_excess_spread=float(spread_result["excess_spread_amount"]),
        servicer_share_percent=float(spread_result["servicer_share_percent"]),
        servicer_share_amount=float(spread_result["servicer_share"]),
        lender_share_amount=float(spread_result["lender_share"]),
        cumulative_excess_spread=float(cumulative)
    )

    db.add(tracking)

    # Update participation
    participation = db.query(LoanParticipation).get(participation_id)
    participation.cumulative_excess_spread = float(cumulative)

    db.flush()
    return tracking


def accrue_servicer_income(
    arrangement_id: int,
    accrual_date: date,
    period_start: date,
    period_end: date,
    db: Session
) -> ServicerIncomeAccrual:
    """
    Create income accrual entry for a servicer arrangement.
    """
    arrangement = db.query(ServicerArrangement).get(arrangement_id)
    if not arrangement:
        raise ValueError(f"Arrangement {arrangement_id} not found")

    # Get portfolio data
    participations = db.query(LoanParticipation).filter(
        LoanParticipation.servicer_arrangement_id == arrangement_id
    ).all()

    portfolio_outstanding = Decimal("0")
    portfolio_original = Decimal("0")
    total_loans = len(participations)
    active_loans = 0
    principal_collected = Decimal("0")
    interest_collected = Decimal("0")
    fees_collected = Decimal("0")

    total_excess_spread = Decimal("0")

    for p in participations:
        loan = db.query(LoanAccount).get(p.loan_account_id)
        if loan:
            portfolio_outstanding += Decimal(str(loan.principal_outstanding))
            portfolio_original += Decimal(str(loan.principal_amount))
            if loan.status in ["active", "delinquent"]:
                active_loans += 1

            # Get collections in period
            collections = db.query(Payment).filter(
                and_(
                    Payment.loan_account_id == loan.id,
                    Payment.payment_date >= period_start,
                    Payment.payment_date <= period_end,
                    Payment.status == "completed"
                )
            ).all()

            for c in collections:
                principal_collected += Decimal(str(c.principal_amount or 0))
                interest_collected += Decimal(str(c.interest_amount or 0))
                fees_collected += Decimal(str(c.fee_amount or 0))

            # Calculate excess spread for loan
            spread = calculate_excess_spread(
                loan.id, p.id, period_start, period_end, db
            )
            total_excess_spread += spread["servicer_share"]

    # Calculate servicer fee
    fee_result = calculate_servicer_fee(arrangement_id, period_start, period_end, db)

    # Calculate lender's interest income
    lender_yield = Decimal(str(arrangement.lender_yield_rate or 0))
    days = (period_end - period_start).days + 1
    lender_interest = (
        portfolio_outstanding * lender_yield / Decimal("100") * Decimal(str(days)) / Decimal("365")
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # TDS on interest (10%)
    tds = (lender_interest * Decimal("10") / Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    total_servicer_income = fee_result["servicer_fee"] + total_excess_spread
    total_lender_income = lender_interest

    accrual = ServicerIncomeAccrual(
        arrangement_id=arrangement_id,
        accrual_date=accrual_date,
        period_start=period_start,
        period_end=period_end,
        is_month_end=accrual_date.day == 1,
        portfolio_outstanding=float(portfolio_outstanding),
        portfolio_original=float(portfolio_original),
        total_loans=total_loans,
        active_loans=active_loans,
        principal_collected=float(principal_collected),
        interest_collected=float(interest_collected),
        fees_collected=float(fees_collected),
        total_collected=float(principal_collected + interest_collected + fees_collected),
        servicer_fee_base=float(fee_result["portfolio_outstanding"]),
        servicer_fee_rate_applied=float(arrangement.servicer_fee_rate),
        servicer_fee_accrued=float(fee_result["servicer_fee"]),
        weighted_avg_borrower_rate=None,  # Would need to calculate
        lender_yield_rate=float(lender_yield),
        excess_spread_rate=None,
        excess_spread_amount=float(total_excess_spread),
        servicer_excess_spread_share=float(total_excess_spread),
        lender_excess_spread_share=0,
        gst_on_servicer_fee=float(fee_result["gst"]),
        tds_on_interest=float(tds),
        total_servicer_income=float(total_servicer_income),
        total_lender_income=float(total_lender_income),
        net_servicer_income=float(total_servicer_income + fee_result["gst"]),
        net_lender_income=float(total_lender_income - tds)
    )

    db.add(accrual)
    db.flush()
    return accrual


def withhold_from_collection(
    arrangement_id: int,
    payment_id: int,
    loan_account_id: int,
    db: Session
) -> WithholdingTracker:
    """
    Calculate and record withholding from a collection.
    """
    arrangement = db.query(ServicerArrangement).get(arrangement_id)
    payment = db.query(Payment).get(payment_id)
    loan = db.query(LoanAccount).get(loan_account_id)

    if not arrangement or not payment or not loan:
        raise ValueError("Invalid arrangement, payment, or loan")

    if not arrangement.withhold_servicer_fee:
        raise ValueError("Withholding not enabled for this arrangement")

    total_collection = Decimal(str(payment.amount))
    principal = Decimal(str(payment.principal_amount or 0))
    interest = Decimal(str(payment.interest_amount or 0))
    fees = Decimal(str(payment.fee_amount or 0))

    # Get participation for share calculation
    participation = db.query(LoanParticipation).filter(
        and_(
            LoanParticipation.loan_account_id == loan_account_id,
            LoanParticipation.servicer_arrangement_id == arrangement_id
        )
    ).first()

    lender_share_pct = Decimal(str(participation.share_percent)) if participation else Decimal("100")

    # Calculate lender's share of collection
    lender_principal = (principal * lender_share_pct / Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    lender_interest = (interest * lender_share_pct / Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    lender_fees = (fees * lender_share_pct / Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    # Calculate servicer fee on collection (if applicable)
    days = 30  # Simplified - assume monthly
    servicer_fee_on_collection = (
        lender_principal *
        Decimal(str(arrangement.servicer_fee_rate)) /
        Decimal("100") *
        Decimal(str(days)) /
        Decimal("365")
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Calculate excess spread
    borrower_rate = Decimal(str(loan.interest_rate))
    lender_yield = Decimal(str(participation.interest_rate)) if participation else borrower_rate
    excess_rate = max(Decimal("0"), borrower_rate - lender_yield)

    excess_spread_withheld = (
        lender_interest * excess_rate / borrower_rate
        if borrower_rate > 0 else Decimal("0")
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # GST on servicer fee
    gst = (servicer_fee_on_collection * Decimal("18") / Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    total_withheld = servicer_fee_on_collection + excess_spread_withheld + gst
    net_to_lender = (lender_principal + lender_interest + lender_fees) - total_withheld

    tracker = WithholdingTracker(
        arrangement_id=arrangement_id,
        collection_date=payment.payment_date,
        payment_id=payment_id,
        loan_account_id=loan_account_id,
        total_collection=float(total_collection),
        principal_collected=float(principal),
        interest_collected=float(interest),
        fees_collected=float(fees),
        servicer_fee_withheld=float(servicer_fee_on_collection),
        excess_spread_withheld=float(excess_spread_withheld),
        gst_withheld=float(gst),
        total_withheld=float(total_withheld),
        net_to_lender=float(net_to_lender),
        lender_principal_share=float(lender_principal),
        lender_interest_share=float(lender_interest - excess_spread_withheld),
        lender_fee_share=float(lender_fees)
    )

    db.add(tracker)
    db.flush()
    return tracker


def create_income_distribution(
    arrangement_id: int,
    distribution_date: date,
    period_start: date,
    period_end: date,
    recipient_type: str,
    recipient_partner_id: int,
    db: Session
) -> ServicerIncomeDistribution:
    """
    Create income distribution record for settlement.
    """
    arrangement = db.query(ServicerArrangement).get(arrangement_id)
    if not arrangement:
        raise ValueError(f"Arrangement {arrangement_id} not found")

    # Get accruals for period
    accruals = db.query(ServicerIncomeAccrual).filter(
        and_(
            ServicerIncomeAccrual.arrangement_id == arrangement_id,
            ServicerIncomeAccrual.accrual_date >= period_start,
            ServicerIncomeAccrual.accrual_date <= period_end
        )
    ).all()

    if recipient_type == "servicer":
        servicer_fee = sum(Decimal(str(a.servicer_fee_accrued)) for a in accruals)
        excess_spread = sum(Decimal(str(a.servicer_excess_spread_share)) for a in accruals)
        performance_fee = sum(Decimal(str(a.performance_fee_earned or 0)) for a in accruals)
        gst = sum(Decimal(str(a.gst_on_servicer_fee)) for a in accruals)
        gross = servicer_fee + excess_spread + performance_fee
        net = gross  # GST is collected, not deducted
    else:  # lender
        servicer_fee = Decimal("0")
        excess_spread = sum(Decimal(str(a.lender_excess_spread_share)) for a in accruals)
        performance_fee = Decimal("0")
        gst = Decimal("0")
        tds = sum(Decimal(str(a.tds_on_interest)) for a in accruals)
        gross = sum(Decimal(str(a.total_lender_income)) for a in accruals)
        net = gross - tds

    distribution = ServicerIncomeDistribution(
        arrangement_id=arrangement_id,
        distribution_date=distribution_date,
        period_start=period_start,
        period_end=period_end,
        recipient_type=recipient_type,
        recipient_partner_id=recipient_partner_id,
        servicer_fee_amount=float(servicer_fee),
        excess_spread_amount=float(excess_spread),
        performance_fee_amount=float(performance_fee),
        gross_amount=float(gross),
        gst_deducted=float(gst) if recipient_type == "servicer" else 0,
        tds_deducted=float(tds) if recipient_type == "lender" else 0,
        total_deductions=float(gst if recipient_type == "servicer" else tds),
        net_amount=float(net)
    )

    db.add(distribution)
    db.flush()
    return distribution
