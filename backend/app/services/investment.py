"""Investment service for NCDs, CPs, Bonds, and other fixed income instruments."""
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any, List
import math

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.investment import (
    Investment,
    InvestmentProduct,
    InvestmentIssuer,
    InvestmentCouponSchedule,
    InvestmentAccrual,
    InvestmentTransaction,
    InvestmentValuation,
    InvestmentPortfolioSummary,
)


def round_decimal(value: Decimal, places: int = 2) -> Decimal:
    """Round decimal to specified places using HALF_UP."""
    return value.quantize(Decimal(10) ** -places, rounding=ROUND_HALF_UP)


def get_day_count_fraction(
    start_date: date,
    end_date: date,
    convention: str = "ACT/365",
) -> Decimal:
    """
    Calculate year fraction based on day count convention.

    Supported conventions:
    - ACT/365: Actual days / 365
    - ACT/360: Actual days / 360
    - 30/360: (360*(Y2-Y1) + 30*(M2-M1) + (D2-D1)) / 360
    - ACT/ACT: Actual days / actual days in year
    """
    actual_days = (end_date - start_date).days

    if convention == "ACT/365":
        return Decimal(actual_days) / Decimal("365")
    elif convention == "ACT/360":
        return Decimal(actual_days) / Decimal("360")
    elif convention == "30/360":
        d1 = min(start_date.day, 30)
        d2 = min(end_date.day, 30) if d1 == 30 else end_date.day
        days_30_360 = 360 * (end_date.year - start_date.year) + 30 * (end_date.month - start_date.month) + (d2 - d1)
        return Decimal(days_30_360) / Decimal("360")
    elif convention == "ACT/ACT":
        # Simplified: use 365 or 366 based on year
        year = start_date.year
        days_in_year = 366 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 365
        return Decimal(actual_days) / Decimal(days_in_year)
    else:
        return Decimal(actual_days) / Decimal("365")


def calculate_ytm(
    price: Decimal,
    face_value: Decimal,
    coupon_rate: Decimal,
    years_to_maturity: Decimal,
    coupon_frequency: int = 2,  # semi-annual default
    tolerance: Decimal = Decimal("0.0001"),
    max_iterations: int = 100,
) -> Decimal:
    """
    Calculate Yield to Maturity using Newton-Raphson method.

    Args:
        price: Current price
        face_value: Face value
        coupon_rate: Annual coupon rate (percentage)
        years_to_maturity: Years to maturity
        coupon_frequency: Number of coupon payments per year
        tolerance: Convergence tolerance
        max_iterations: Maximum iterations

    Returns:
        YTM as percentage
    """
    if price <= 0 or face_value <= 0 or years_to_maturity <= 0:
        return Decimal("0")

    # Convert to float for calculation
    P = float(price)
    F = float(face_value)
    C = float(coupon_rate) / 100 * F / coupon_frequency
    n = int(float(years_to_maturity) * coupon_frequency)

    if n == 0:
        return coupon_rate

    # Initial guess using approximate formula
    ytm = ((C + (F - P) / n) / ((F + P) / 2)) * coupon_frequency

    for _ in range(max_iterations):
        # Calculate bond price at current YTM
        r = ytm / coupon_frequency
        if r == 0:
            pv = C * n + F
        else:
            pv = C * (1 - (1 + r) ** (-n)) / r + F * (1 + r) ** (-n)

        # Calculate derivative
        if r == 0:
            dpv = -C * n * (n + 1) / 2 - F * n
        else:
            dpv = -C * n * (1 + r) ** (-(n + 1)) / r
            dpv += C * (1 - (1 + r) ** (-n)) / (r ** 2)
            dpv -= C * (1 + r) ** (-(n + 1)) / r
            dpv += F * (-n) * (1 + r) ** (-(n + 1))
        dpv = dpv / coupon_frequency

        # Newton-Raphson update
        diff = (pv - P)
        if abs(diff) < float(tolerance):
            break

        if dpv != 0:
            ytm = ytm - diff / dpv

    return round_decimal(Decimal(str(ytm * 100)), 4)


def calculate_modified_duration(
    ytm: Decimal,
    years_to_maturity: Decimal,
    coupon_rate: Decimal,
    coupon_frequency: int = 2,
) -> Decimal:
    """
    Calculate modified duration of a bond.

    Modified Duration = Macaulay Duration / (1 + YTM/frequency)
    """
    if ytm <= 0 or years_to_maturity <= 0:
        return Decimal("0")

    # Simplified Macaulay Duration approximation
    y = float(ytm) / 100
    c = float(coupon_rate) / 100
    n = float(years_to_maturity)
    freq = coupon_frequency

    if y == c:
        mac_dur = (1 + y/freq) / (y/freq) * (1 - 1 / ((1 + y/freq) ** (n * freq)))
    else:
        # General formula
        r = y / freq
        periods = int(n * freq)
        if r == 0:
            mac_dur = n
        else:
            mac_dur = (1 + r) / r - (1 + r + periods * (c/freq - r)) / (c/freq * ((1 + r) ** periods - 1) + r)

    mod_dur = mac_dur / (1 + y / freq)
    return round_decimal(Decimal(str(mod_dur)), 4)


def create_investment(
    db: Session,
    product_id: int,
    issuer_id: int,
    isin: Optional[str],
    security_name: str,
    instrument_type: str,
    face_value_per_unit: Decimal,
    units: Decimal,
    purchase_date: date,
    purchase_price_per_unit: Decimal,
    coupon_rate: Decimal,
    coupon_type: str,
    coupon_frequency: str,
    issue_date: date,
    maturity_date: date,
    acquisition_type: str = "primary",
    classification: str = "HTM",
    holder_partner_id: Optional[int] = None,
    benchmark_rate_id: Optional[int] = None,
    spread_over_benchmark: Optional[Decimal] = None,
) -> Investment:
    """
    Create a new investment record.

    Args:
        db: Database session
        product_id: Investment product ID
        issuer_id: Issuer ID
        isin: ISIN code (optional)
        security_name: Name of security
        instrument_type: Type (ncd, cp, bond, gsec, etc.)
        face_value_per_unit: Face value per unit
        units: Number of units purchased
        purchase_date: Purchase date
        purchase_price_per_unit: Price paid per unit
        coupon_rate: Annual coupon rate
        coupon_type: fixed, floating, zero_coupon
        coupon_frequency: monthly, quarterly, semi_annual, annual
        issue_date: Issue date of instrument
        maturity_date: Maturity date
        acquisition_type: primary, secondary, private_placement
        classification: HTM, AFS, HFT
        holder_partner_id: Entity holding the investment
        benchmark_rate_id: For floating rate instruments
        spread_over_benchmark: Spread over benchmark

    Returns:
        Created Investment
    """
    # Calculate derived values
    total_face_value = face_value_per_unit * units
    total_purchase_cost = purchase_price_per_unit * units
    purchase_premium_discount = total_purchase_cost - total_face_value

    # Tenure
    original_tenure_days = (maturity_date - issue_date).days
    remaining_tenure_days = (maturity_date - purchase_date).days

    # Calculate purchase yield (YTM at purchase)
    years_to_maturity = Decimal(remaining_tenure_days) / Decimal("365")
    freq_map = {"monthly": 12, "quarterly": 4, "semi_annual": 2, "annual": 1, "at_maturity": 1, "none": 1}
    freq = freq_map.get(coupon_frequency, 2)

    purchase_yield = calculate_ytm(
        purchase_price_per_unit, face_value_per_unit, coupon_rate, years_to_maturity, freq
    )

    # Generate investment code
    investment_code = f"INV{purchase_date.strftime('%Y%m%d')}{issuer_id}{instrument_type[:3].upper()}"

    investment = Investment(
        investment_code=investment_code,
        isin=isin,
        security_name=security_name,
        product_id=product_id,
        issuer_id=issuer_id,
        holder_partner_id=holder_partner_id,
        instrument_type=instrument_type,
        face_value_per_unit=face_value_per_unit,
        units_held=units,
        original_units=units,
        total_face_value=total_face_value,
        purchase_date=purchase_date,
        purchase_price_per_unit=purchase_price_per_unit,
        purchase_yield=purchase_yield,
        total_purchase_cost=total_purchase_cost,
        purchase_premium_discount=purchase_premium_discount,
        acquisition_type=acquisition_type,
        coupon_rate=coupon_rate,
        coupon_type=coupon_type,
        coupon_frequency=coupon_frequency,
        benchmark_rate_id=benchmark_rate_id,
        spread_over_benchmark=spread_over_benchmark,
        current_effective_rate=coupon_rate,
        issue_date=issue_date,
        maturity_date=maturity_date,
        original_tenure_days=original_tenure_days,
        remaining_tenure_days=remaining_tenure_days,
        amortized_cost=total_purchase_cost,
        accrued_interest=Decimal("0"),
        classification=classification,
        status="active",
    )

    db.add(investment)
    db.commit()
    db.refresh(investment)

    # Generate coupon schedule
    generate_coupon_schedule(db, investment.id)

    return investment


def generate_coupon_schedule(
    db: Session,
    investment_id: int,
) -> List[InvestmentCouponSchedule]:
    """Generate coupon payment schedule for an investment."""
    investment = db.query(Investment).filter(Investment.id == investment_id).first()
    if not investment:
        raise ValueError(f"Investment {investment_id} not found")

    if investment.coupon_type == "zero_coupon":
        return []  # No coupons for zero coupon instruments

    # Frequency mapping
    freq_months = {
        "monthly": 1,
        "quarterly": 3,
        "semi_annual": 6,
        "annual": 12,
        "at_maturity": 0,  # Special handling
    }

    months = freq_months.get(investment.coupon_frequency, 6)
    schedules = []

    if months == 0:  # At maturity
        # Single coupon at maturity
        days = (investment.maturity_date - investment.issue_date).days
        coupon_amount = round_decimal(
            investment.total_face_value * investment.coupon_rate / Decimal("100") * Decimal(days) / Decimal("365")
        )
        tds_amount = round_decimal(coupon_amount * Decimal("0.10"))

        schedule = InvestmentCouponSchedule(
            investment_id=investment_id,
            coupon_number=1,
            period_start_date=investment.issue_date,
            period_end_date=investment.maturity_date,
            coupon_date=investment.maturity_date,
            coupon_rate=investment.coupon_rate,
            face_value=investment.total_face_value,
            days_in_period=days,
            coupon_amount=coupon_amount,
            tds_rate=Decimal("10"),
            tds_amount=tds_amount,
            net_coupon=coupon_amount - tds_amount,
            status="scheduled",
        )
        db.add(schedule)
        schedules.append(schedule)
    else:
        # Regular periodic coupons
        current_date = investment.issue_date
        coupon_number = 0

        while current_date < investment.maturity_date:
            period_start = current_date

            # Calculate next coupon date
            next_month = current_date.month + months
            next_year = current_date.year + (next_month - 1) // 12
            next_month = ((next_month - 1) % 12) + 1
            try:
                next_date = date(next_year, next_month, current_date.day)
            except ValueError:
                # Handle end of month
                if next_month == 2:
                    next_date = date(next_year, 3, 1) - timedelta(days=1)
                else:
                    next_date = date(next_year, next_month + 1, 1) - timedelta(days=1)

            # Don't go past maturity
            if next_date > investment.maturity_date:
                next_date = investment.maturity_date

            period_end = next_date
            coupon_number += 1

            # Calculate coupon
            days = (period_end - period_start).days
            year_fraction = get_day_count_fraction(period_start, period_end, "ACT/365")
            coupon_amount = round_decimal(
                investment.total_face_value * investment.coupon_rate / Decimal("100") * year_fraction
            )
            tds_amount = round_decimal(coupon_amount * Decimal("0.10"))

            schedule = InvestmentCouponSchedule(
                investment_id=investment_id,
                coupon_number=coupon_number,
                period_start_date=period_start,
                period_end_date=period_end,
                coupon_date=period_end,
                coupon_rate=investment.coupon_rate,
                face_value=investment.total_face_value,
                days_in_period=days,
                coupon_amount=coupon_amount,
                tds_rate=Decimal("10"),
                tds_amount=tds_amount,
                net_coupon=coupon_amount - tds_amount,
                status="scheduled",
            )
            db.add(schedule)
            schedules.append(schedule)

            current_date = next_date
            if current_date >= investment.maturity_date:
                break

    db.commit()

    # Update next coupon date on investment
    if schedules:
        investment.next_coupon_date = schedules[0].coupon_date
        db.commit()

    return schedules


def accrue_interest(
    db: Session,
    investment_id: int,
    accrual_date: date,
) -> InvestmentAccrual:
    """
    Accrue interest for an investment up to a specific date.

    Also handles premium/discount amortization for HTM investments.
    """
    investment = db.query(Investment).filter(Investment.id == investment_id).first()
    if not investment:
        raise ValueError(f"Investment {investment_id} not found")

    if investment.status != "active":
        raise ValueError(f"Investment status is {investment.status}, cannot accrue")

    if investment.coupon_type == "zero_coupon":
        # Zero coupon: accrue implied interest (discount amortization)
        return _accrue_zero_coupon(db, investment, accrual_date)

    # Determine period
    period_start = investment.last_accrual_date or investment.purchase_date
    period_end = accrual_date

    if period_end <= period_start:
        raise ValueError("Accrual date must be after last accrual date")

    days_accrued = (period_end - period_start).days
    year_fraction = get_day_count_fraction(period_start, period_end, "ACT/365")

    # Calculate interest accrued
    interest_accrued = round_decimal(
        investment.total_face_value * investment.coupon_rate / Decimal("100") * year_fraction, 4
    )

    # Premium/discount amortization (straight-line for simplicity)
    remaining_days = (investment.maturity_date - period_start).days
    if remaining_days > 0:
        daily_amortization = investment.purchase_premium_discount / Decimal(remaining_days)
        premium_discount_amortized = round_decimal(daily_amortization * Decimal(days_accrued), 4)
    else:
        premium_discount_amortized = Decimal("0")

    # Net interest income
    # Premium: reduces income, Discount: increases income
    net_interest_income = interest_accrued - premium_discount_amortized

    # Create accrual record
    accrual = InvestmentAccrual(
        investment_id=investment_id,
        accrual_date=accrual_date,
        period_start=period_start,
        period_end=period_end,
        face_value=investment.total_face_value,
        coupon_rate=investment.coupon_rate,
        day_count_convention="ACT/365",
        days_accrued=days_accrued,
        interest_accrued=interest_accrued,
        cumulative_accrued=investment.accrued_interest + interest_accrued,
        premium_discount_amortized=premium_discount_amortized,
        cumulative_amortization=(investment.total_purchase_cost - investment.amortized_cost) + premium_discount_amortized,
        net_interest_income=net_interest_income,
    )
    db.add(accrual)

    # Update investment
    investment.accrued_interest = investment.accrued_interest + interest_accrued
    investment.amortized_cost = investment.amortized_cost - premium_discount_amortized
    investment.last_accrual_date = accrual_date
    investment.remaining_tenure_days = (investment.maturity_date - accrual_date).days

    db.commit()
    db.refresh(accrual)

    return accrual


def _accrue_zero_coupon(
    db: Session,
    investment: Investment,
    accrual_date: date,
) -> InvestmentAccrual:
    """Accrue interest for zero coupon instruments (discount amortization)."""
    period_start = investment.last_accrual_date or investment.purchase_date
    period_end = accrual_date
    days_accrued = (period_end - period_start).days

    # For zero coupon, the "yield" is the discount amortized
    remaining_days = (investment.maturity_date - period_start).days
    if remaining_days > 0:
        # Use effective interest method approximation
        total_discount = investment.total_face_value - investment.total_purchase_cost
        daily_rate = total_discount / Decimal(remaining_days)
        interest_accrued = round_decimal(daily_rate * Decimal(days_accrued), 4)
    else:
        interest_accrued = Decimal("0")

    accrual = InvestmentAccrual(
        investment_id=investment.id,
        accrual_date=accrual_date,
        period_start=period_start,
        period_end=period_end,
        face_value=investment.total_face_value,
        coupon_rate=Decimal("0"),
        day_count_convention="ACT/365",
        days_accrued=days_accrued,
        interest_accrued=interest_accrued,
        cumulative_accrued=investment.accrued_interest + interest_accrued,
        premium_discount_amortized=interest_accrued,  # For zero coupon, it's the same
        cumulative_amortization=(investment.amortized_cost - investment.total_purchase_cost) + interest_accrued,
        net_interest_income=interest_accrued,
    )
    db.add(accrual)

    # Update investment
    investment.accrued_interest = investment.accrued_interest + interest_accrued
    investment.amortized_cost = investment.amortized_cost + interest_accrued
    investment.last_accrual_date = accrual_date

    db.commit()
    db.refresh(accrual)

    return accrual


def receive_coupon(
    db: Session,
    investment_id: int,
    coupon_schedule_id: int,
    received_date: date,
    received_amount: Decimal,
    tds_deducted: Decimal,
) -> InvestmentCouponSchedule:
    """Record receipt of a coupon payment."""
    schedule = db.query(InvestmentCouponSchedule).filter(
        InvestmentCouponSchedule.id == coupon_schedule_id,
        InvestmentCouponSchedule.investment_id == investment_id,
    ).first()

    if not schedule:
        raise ValueError(f"Coupon schedule {coupon_schedule_id} not found")

    investment = db.query(Investment).filter(Investment.id == investment_id).first()

    # Update schedule
    schedule.status = "received"
    schedule.received_date = received_date
    schedule.received_amount = received_amount

    # Update investment totals
    investment.total_coupon_received = (investment.total_coupon_received or Decimal("0")) + received_amount
    investment.total_tds_deducted = (investment.total_tds_deducted or Decimal("0")) + tds_deducted

    # Reset accrued interest for this coupon period
    investment.accrued_interest = Decimal("0")

    # Update next coupon date
    next_schedule = db.query(InvestmentCouponSchedule).filter(
        InvestmentCouponSchedule.investment_id == investment_id,
        InvestmentCouponSchedule.status == "scheduled",
        InvestmentCouponSchedule.coupon_date > received_date,
    ).order_by(InvestmentCouponSchedule.coupon_date).first()

    investment.last_coupon_date = received_date
    investment.next_coupon_date = next_schedule.coupon_date if next_schedule else None

    # Create transaction record
    transaction = InvestmentTransaction(
        investment_id=investment_id,
        transaction_code=f"CPN{investment_id}{received_date.strftime('%Y%m%d')}",
        transaction_type="coupon",
        transaction_date=received_date,
        value_date=received_date,
        units=investment.units_held,
        price_per_unit=Decimal("0"),
        face_value=investment.total_face_value,
        consideration=Decimal("0"),
        accrued_interest=Decimal("0"),
        total_amount=received_amount + tds_deducted,
        tds_amount=tds_deducted,
        net_amount=received_amount,
        settlement_status="completed",
        settlement_date=received_date,
    )
    db.add(transaction)

    db.commit()
    db.refresh(schedule)

    return schedule


def mature_investment(
    db: Session,
    investment_id: int,
    maturity_date: date,
    redemption_amount: Decimal,
    tds_deducted: Decimal = Decimal("0"),
) -> Investment:
    """Process maturity of an investment."""
    investment = db.query(Investment).filter(Investment.id == investment_id).first()
    if not investment:
        raise ValueError(f"Investment {investment_id} not found")

    # Update investment status
    investment.status = "matured"
    investment.closure_date = maturity_date
    investment.closure_type = "maturity"
    investment.total_principal_received = redemption_amount
    investment.total_tds_deducted = (investment.total_tds_deducted or Decimal("0")) + tds_deducted

    # Create maturity transaction
    transaction = InvestmentTransaction(
        investment_id=investment_id,
        transaction_code=f"MAT{investment_id}{maturity_date.strftime('%Y%m%d')}",
        transaction_type="maturity",
        transaction_date=maturity_date,
        value_date=maturity_date,
        units=investment.units_held,
        price_per_unit=investment.face_value_per_unit,
        face_value=investment.total_face_value,
        consideration=redemption_amount,
        accrued_interest=investment.accrued_interest,
        total_amount=redemption_amount,
        book_value=investment.amortized_cost,
        gain_loss=redemption_amount - investment.amortized_cost,
        tds_amount=tds_deducted,
        net_amount=redemption_amount - tds_deducted,
        settlement_status="completed",
        settlement_date=maturity_date,
    )
    db.add(transaction)

    # Update issuer exposure
    issuer = db.query(InvestmentIssuer).filter(InvestmentIssuer.id == investment.issuer_id).first()
    if issuer:
        issuer.current_exposure = max(Decimal("0"), issuer.current_exposure - investment.total_face_value)

    db.commit()
    db.refresh(investment)

    return investment


def mark_to_market(
    db: Session,
    investment_id: int,
    valuation_date: date,
    market_price: Decimal,
    price_source: str = "market",
) -> InvestmentValuation:
    """
    Mark an investment to market.

    Creates valuation record and updates investment's current market value.
    """
    investment = db.query(Investment).filter(Investment.id == investment_id).first()
    if not investment:
        raise ValueError(f"Investment {investment_id} not found")

    # Calculate market value
    market_value = investment.units_held * market_price
    book_value = investment.amortized_cost + investment.accrued_interest

    # Calculate market yield
    remaining_days = (investment.maturity_date - valuation_date).days
    years_to_maturity = Decimal(remaining_days) / Decimal("365") if remaining_days > 0 else Decimal("0")

    freq_map = {"monthly": 12, "quarterly": 4, "semi_annual": 2, "annual": 1, "at_maturity": 1}
    freq = freq_map.get(investment.coupon_frequency, 2)

    market_yield = calculate_ytm(
        market_price, investment.face_value_per_unit, investment.coupon_rate, years_to_maturity, freq
    )

    # Calculate duration
    mod_duration = calculate_modified_duration(
        market_yield, years_to_maturity, investment.coupon_rate, freq
    )

    # MTM gain/loss
    mtm_gain_loss = market_value - book_value

    # Get previous cumulative MTM
    prev_valuation = db.query(InvestmentValuation).filter(
        InvestmentValuation.investment_id == investment_id,
        InvestmentValuation.valuation_date < valuation_date,
    ).order_by(InvestmentValuation.valuation_date.desc()).first()

    cumulative_mtm = mtm_gain_loss
    if prev_valuation:
        cumulative_mtm = prev_valuation.cumulative_mtm + mtm_gain_loss

    valuation = InvestmentValuation(
        investment_id=investment_id,
        valuation_date=valuation_date,
        valuation_type="daily",
        face_value=investment.total_face_value,
        amortized_cost=investment.amortized_cost,
        accrued_interest=investment.accrued_interest,
        book_value=book_value,
        market_price=market_price,
        market_value=market_value,
        price_source=price_source,
        book_yield=investment.purchase_yield,
        market_yield=market_yield,
        mtm_gain_loss=mtm_gain_loss,
        cumulative_mtm=cumulative_mtm,
        modified_duration=mod_duration,
    )
    db.add(valuation)

    # Update investment
    investment.current_market_price = market_price
    investment.current_ytm = market_yield
    investment.current_market_value = market_value
    investment.last_valuation_date = valuation_date

    db.commit()
    db.refresh(valuation)

    return valuation


def get_portfolio_summary(
    db: Session,
    as_of_date: date,
    holder_partner_id: Optional[int] = None,
    instrument_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Get investment portfolio summary."""
    query = db.query(Investment).filter(
        Investment.status == "active",
        Investment.purchase_date <= as_of_date,
    )

    if holder_partner_id:
        query = query.filter(Investment.holder_partner_id == holder_partner_id)

    if instrument_type:
        query = query.filter(Investment.instrument_type == instrument_type)

    investments = query.all()

    summary = {
        "as_of_date": as_of_date,
        "total_investments": len(investments),
        "total_face_value": Decimal("0"),
        "total_book_value": Decimal("0"),
        "total_market_value": Decimal("0"),
        "total_accrued_interest": Decimal("0"),
        "weighted_avg_coupon": Decimal("0"),
        "weighted_avg_ytm": Decimal("0"),
        "by_instrument_type": {},
        "by_rating": {},
        "maturity_profile": {
            "0_30_days": Decimal("0"),
            "31_90_days": Decimal("0"),
            "91_180_days": Decimal("0"),
            "181_365_days": Decimal("0"),
            "1_3_years": Decimal("0"),
            "3_plus_years": Decimal("0"),
        },
    }

    total_coupon_weighted = Decimal("0")
    total_ytm_weighted = Decimal("0")

    for inv in investments:
        book_value = inv.amortized_cost + inv.accrued_interest
        market_value = inv.current_market_value or book_value

        summary["total_face_value"] += inv.total_face_value
        summary["total_book_value"] += book_value
        summary["total_market_value"] += market_value
        summary["total_accrued_interest"] += inv.accrued_interest

        total_coupon_weighted += inv.coupon_rate * inv.total_face_value
        total_ytm_weighted += (inv.current_ytm or inv.purchase_yield) * inv.total_face_value

        # By instrument type
        itype = inv.instrument_type
        if itype not in summary["by_instrument_type"]:
            summary["by_instrument_type"][itype] = {"count": 0, "face_value": Decimal("0")}
        summary["by_instrument_type"][itype]["count"] += 1
        summary["by_instrument_type"][itype]["face_value"] += inv.total_face_value

        # Maturity profile
        days_to_maturity = (inv.maturity_date - as_of_date).days
        if days_to_maturity <= 30:
            summary["maturity_profile"]["0_30_days"] += inv.total_face_value
        elif days_to_maturity <= 90:
            summary["maturity_profile"]["31_90_days"] += inv.total_face_value
        elif days_to_maturity <= 180:
            summary["maturity_profile"]["91_180_days"] += inv.total_face_value
        elif days_to_maturity <= 365:
            summary["maturity_profile"]["181_365_days"] += inv.total_face_value
        elif days_to_maturity <= 1095:
            summary["maturity_profile"]["1_3_years"] += inv.total_face_value
        else:
            summary["maturity_profile"]["3_plus_years"] += inv.total_face_value

    # Calculate weighted averages
    if summary["total_face_value"] > 0:
        summary["weighted_avg_coupon"] = round_decimal(
            total_coupon_weighted / summary["total_face_value"], 4
        )
        summary["weighted_avg_ytm"] = round_decimal(
            total_ytm_weighted / summary["total_face_value"], 4
        )

    return summary


def update_floating_rate(
    db: Session,
    investment_id: int,
    new_benchmark_rate: Decimal,
    effective_date: date,
) -> Investment:
    """Update floating rate investment with new benchmark rate."""
    investment = db.query(Investment).filter(Investment.id == investment_id).first()
    if not investment:
        raise ValueError(f"Investment {investment_id} not found")

    if investment.coupon_type != "floating":
        raise ValueError("Investment is not floating rate")

    # Calculate new effective rate
    spread = investment.spread_over_benchmark or Decimal("0")
    new_rate = new_benchmark_rate + spread

    investment.current_effective_rate = new_rate
    investment.next_reset_date = effective_date

    # Update future coupon schedules
    future_schedules = db.query(InvestmentCouponSchedule).filter(
        InvestmentCouponSchedule.investment_id == investment_id,
        InvestmentCouponSchedule.status == "scheduled",
        InvestmentCouponSchedule.coupon_date >= effective_date,
    ).all()

    for schedule in future_schedules:
        year_fraction = get_day_count_fraction(
            schedule.period_start_date, schedule.period_end_date, "ACT/365"
        )
        schedule.coupon_rate = new_rate
        schedule.coupon_amount = round_decimal(
            schedule.face_value * new_rate / Decimal("100") * year_fraction
        )
        schedule.tds_amount = round_decimal(schedule.coupon_amount * Decimal("0.10"))
        schedule.net_coupon = schedule.coupon_amount - schedule.tds_amount

    db.commit()
    db.refresh(investment)

    return investment
