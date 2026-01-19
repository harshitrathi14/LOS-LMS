"""
Securitization service.

Handles:
- Pool creation and management
- Loan inclusion/removal
- Investor management
- Cash flow distribution
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import and_, func as sql_func
from sqlalchemy.orm import Session

from app.models.securitization import (
    SecuritizationPool,
    PoolLoan,
    Investor,
    PoolInvestment,
    InvestorCashFlow
)
from app.models.loan_account import LoanAccount

CENT = Decimal("0.01")


def _to_decimal(value: float | Decimal | int | None) -> Decimal:
    """Convert numeric value to Decimal."""
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def create_pool(
    pool_code: str,
    name: str,
    pool_type: str,
    cutoff_date: date,
    product_id: int | None = None,
    servicer_name: str | None = None,
    servicer_fee_rate: float = 0,
    trustee_name: str | None = None,
    trustee_fee_rate: float = 0,
    db: Session = None
) -> SecuritizationPool:
    """
    Create a new securitization pool.

    Args:
        pool_code: Unique pool identifier
        name: Pool name
        pool_type: ptc or da
        cutoff_date: Pool cutoff date
        product_id: Optional product filter
        servicer_name: Servicer name
        servicer_fee_rate: Servicer fee as %
        trustee_name: Trustee name
        trustee_fee_rate: Trustee fee as %
        db: Database session

    Returns:
        Created SecuritizationPool
    """
    pool = SecuritizationPool(
        pool_code=pool_code,
        name=name,
        pool_type=pool_type,
        cutoff_date=cutoff_date,
        product_id=product_id,
        servicer_name=servicer_name,
        servicer_fee_rate=servicer_fee_rate,
        trustee_name=trustee_name,
        trustee_fee_rate=trustee_fee_rate,
        status="draft"
    )

    db.add(pool)
    db.commit()
    db.refresh(pool)

    return pool


def add_loan_to_pool(
    pool_id: int,
    loan_account_id: int,
    db: Session
) -> PoolLoan:
    """
    Add a loan to a securitization pool.

    Args:
        pool_id: Pool ID
        loan_account_id: Loan account ID
        db: Database session

    Returns:
        Created PoolLoan
    """
    pool = db.query(SecuritizationPool).filter(
        SecuritizationPool.id == pool_id
    ).first()

    if not pool:
        raise ValueError(f"Pool {pool_id} not found")

    if pool.status not in ["draft", "active"]:
        raise ValueError(f"Pool {pool_id} is not accepting loans")

    loan = db.query(LoanAccount).filter(
        LoanAccount.id == loan_account_id
    ).first()

    if not loan:
        raise ValueError(f"Loan account {loan_account_id} not found")

    if loan.status != "active":
        raise ValueError(f"Loan account {loan_account_id} is not active")

    # Check if already in a pool
    existing = db.query(PoolLoan).filter(
        and_(
            PoolLoan.loan_account_id == loan_account_id,
            PoolLoan.status == "active"
        )
    ).first()

    if existing:
        raise ValueError(
            f"Loan {loan_account_id} is already in pool {existing.pool_id}"
        )

    pool_loan = PoolLoan(
        pool_id=pool_id,
        loan_account_id=loan_account_id,
        inclusion_date=pool.cutoff_date,
        principal_at_inclusion=float(loan.principal_outstanding),
        rate_at_inclusion=float(loan.interest_rate),
        tenure_at_inclusion=loan.tenure_months,
        current_principal=float(loan.principal_outstanding),
        dpd_at_inclusion=loan.dpd,
        current_dpd=loan.dpd,
        status="active"
    )

    db.add(pool_loan)

    # Update pool statistics
    _update_pool_statistics(pool_id, db)

    db.commit()
    db.refresh(pool_loan)

    return pool_loan


def remove_loan_from_pool(
    pool_loan_id: int,
    removal_reason: str,
    db: Session
) -> PoolLoan:
    """
    Remove a loan from a pool.

    Args:
        pool_loan_id: Pool loan ID
        removal_reason: Reason for removal
        db: Database session

    Returns:
        Updated PoolLoan
    """
    pool_loan = db.query(PoolLoan).filter(
        PoolLoan.id == pool_loan_id
    ).first()

    if not pool_loan:
        raise ValueError(f"Pool loan {pool_loan_id} not found")

    pool_loan.status = "removed"
    pool_loan.removal_date = date.today()
    pool_loan.removal_reason = removal_reason

    # Update pool statistics
    _update_pool_statistics(pool_loan.pool_id, db)

    db.commit()
    db.refresh(pool_loan)

    return pool_loan


def _update_pool_statistics(pool_id: int, db: Session) -> None:
    """Update pool aggregate statistics."""
    pool = db.query(SecuritizationPool).filter(
        SecuritizationPool.id == pool_id
    ).first()

    if not pool:
        return

    # Get active loans
    active_loans = db.query(PoolLoan).filter(
        and_(
            PoolLoan.pool_id == pool_id,
            PoolLoan.status == "active"
        )
    ).all()

    if not active_loans:
        pool.total_loans = 0
        pool.total_principal = 0
        pool.current_principal = 0
        pool.weighted_avg_rate = None
        pool.weighted_avg_tenure = None
        return

    total_principal = sum(_to_decimal(l.principal_at_inclusion) for l in active_loans)
    current_principal = sum(_to_decimal(l.current_principal) for l in active_loans)

    # Weighted average rate
    weighted_rate = sum(
        _to_decimal(l.principal_at_inclusion) * _to_decimal(l.rate_at_inclusion)
        for l in active_loans
    ) / total_principal if total_principal > 0 else Decimal("0")

    # Weighted average tenure
    weighted_tenure = sum(
        _to_decimal(l.principal_at_inclusion) * l.tenure_at_inclusion
        for l in active_loans
    ) / total_principal if total_principal > 0 else Decimal("0")

    pool.total_loans = len(active_loans)
    pool.total_principal = float(total_principal)
    pool.current_principal = float(current_principal)
    pool.weighted_avg_rate = float(weighted_rate.quantize(Decimal("0.0001")))
    pool.weighted_avg_tenure = int(weighted_tenure)


def activate_pool(
    pool_id: int,
    settlement_date: date,
    db: Session
) -> SecuritizationPool:
    """
    Activate a pool for trading.

    Args:
        pool_id: Pool ID
        settlement_date: Settlement date
        db: Database session

    Returns:
        Updated SecuritizationPool
    """
    pool = db.query(SecuritizationPool).filter(
        SecuritizationPool.id == pool_id
    ).first()

    if not pool:
        raise ValueError(f"Pool {pool_id} not found")

    if pool.status != "draft":
        raise ValueError(f"Pool {pool_id} is not in draft status")

    if pool.total_loans == 0:
        raise ValueError(f"Pool {pool_id} has no loans")

    pool.status = "active"
    pool.settlement_date = settlement_date

    db.commit()
    db.refresh(pool)

    return pool


def create_investor(
    name: str,
    investor_type: str,
    external_code: str | None = None,
    contact_email: str | None = None,
    bank_account_number: str | None = None,
    bank_ifsc: str | None = None,
    db: Session = None
) -> Investor:
    """
    Create a new investor.

    Args:
        name: Investor name
        investor_type: Type (bank, nbfc, mutual_fund, insurance)
        external_code: External identifier
        contact_email: Contact email
        bank_account_number: Bank account for payouts
        bank_ifsc: Bank IFSC code
        db: Database session

    Returns:
        Created Investor
    """
    investor = Investor(
        name=name,
        investor_type=investor_type,
        external_code=external_code,
        contact_email=contact_email,
        bank_account_number=bank_account_number,
        bank_ifsc=bank_ifsc,
        is_active=True
    )

    db.add(investor)
    db.commit()
    db.refresh(investor)

    return investor


def add_investment(
    pool_id: int,
    investor_id: int,
    investment_amount: float,
    expected_yield: float,
    investment_date: date,
    tranche: str = "senior",
    db: Session = None
) -> PoolInvestment:
    """
    Add an investment to a pool.

    Args:
        pool_id: Pool ID
        investor_id: Investor ID
        investment_amount: Investment amount
        expected_yield: Expected annual yield %
        investment_date: Date of investment
        tranche: senior, mezzanine, or junior
        db: Database session

    Returns:
        Created PoolInvestment
    """
    pool = db.query(SecuritizationPool).filter(
        SecuritizationPool.id == pool_id
    ).first()

    if not pool:
        raise ValueError(f"Pool {pool_id} not found")

    investor = db.query(Investor).filter(
        Investor.id == investor_id
    ).first()

    if not investor:
        raise ValueError(f"Investor {investor_id} not found")

    # Calculate investment percent
    investment_percent = 0
    if pool.total_principal > 0:
        investment_percent = float(
            (_to_decimal(investment_amount) / _to_decimal(pool.total_principal) * 100)
            .quantize(Decimal("0.0001"))
        )

    investment = PoolInvestment(
        pool_id=pool_id,
        investor_id=investor_id,
        investment_amount=investment_amount,
        investment_percent=investment_percent,
        expected_yield=expected_yield,
        investment_date=investment_date,
        tranche=tranche,
        current_principal=investment_amount,
        status="active"
    )

    db.add(investment)
    db.commit()
    db.refresh(investment)

    return investment


def distribute_cash_flow(
    pool_id: int,
    cash_flow_date: date,
    total_principal: float,
    total_interest: float,
    total_prepayment: float = 0,
    db: Session = None
) -> list[InvestorCashFlow]:
    """
    Distribute cash flows to investors pro-rata.

    Args:
        pool_id: Pool ID
        cash_flow_date: Date of distribution
        total_principal: Total principal collected
        total_interest: Total interest collected
        total_prepayment: Total prepayment amount
        db: Database session

    Returns:
        List of created InvestorCashFlow records
    """
    pool = db.query(SecuritizationPool).filter(
        SecuritizationPool.id == pool_id
    ).first()

    if not pool:
        raise ValueError(f"Pool {pool_id} not found")

    investments = db.query(PoolInvestment).filter(
        and_(
            PoolInvestment.pool_id == pool_id,
            PoolInvestment.status == "active"
        )
    ).all()

    if not investments:
        return []

    # Calculate servicer and trustee fees
    total_collection = (
        _to_decimal(total_principal) +
        _to_decimal(total_interest) +
        _to_decimal(total_prepayment)
    )

    servicer_fee = (total_collection * _to_decimal(pool.servicer_fee_rate) / 100).quantize(CENT)
    trustee_fee = (total_collection * _to_decimal(pool.trustee_fee_rate) / 100).quantize(CENT)

    distributable = total_collection - servicer_fee - trustee_fee

    cash_flows = []

    # Distribute pro-rata to investors
    for investment in investments:
        share = _to_decimal(investment.investment_percent) / 100

        # Principal distribution
        if total_principal > 0:
            principal_share = (_to_decimal(total_principal) * share).quantize(CENT)
            cf_principal = InvestorCashFlow(
                investment_id=investment.id,
                cash_flow_date=cash_flow_date,
                cash_flow_type="principal",
                amount=float(principal_share),
                tax_deducted=0,
                net_amount=float(principal_share),
                payment_status="pending"
            )
            db.add(cf_principal)
            cash_flows.append(cf_principal)

            # Update investment principal
            investment.current_principal = float(
                _to_decimal(investment.current_principal) - principal_share
            )

        # Interest distribution
        if total_interest > 0:
            interest_share = (_to_decimal(total_interest) * share).quantize(CENT)
            # TDS on interest (typically 10%)
            tds = (interest_share * Decimal("0.10")).quantize(CENT)

            cf_interest = InvestorCashFlow(
                investment_id=investment.id,
                cash_flow_date=cash_flow_date,
                cash_flow_type="interest",
                amount=float(interest_share),
                tax_deducted=float(tds),
                net_amount=float(interest_share - tds),
                payment_status="pending"
            )
            db.add(cf_interest)
            cash_flows.append(cf_interest)

        # Prepayment distribution
        if total_prepayment > 0:
            prepay_share = (_to_decimal(total_prepayment) * share).quantize(CENT)
            cf_prepay = InvestorCashFlow(
                investment_id=investment.id,
                cash_flow_date=cash_flow_date,
                cash_flow_type="prepayment",
                amount=float(prepay_share),
                tax_deducted=0,
                net_amount=float(prepay_share),
                payment_status="pending"
            )
            db.add(cf_prepay)
            cash_flows.append(cf_prepay)

            investment.current_principal = float(
                _to_decimal(investment.current_principal) - prepay_share
            )

        # Update total distributions
        total_cf = sum(_to_decimal(cf.net_amount) for cf in cash_flows if cf.investment_id == investment.id)
        investment.total_distributions = float(
            _to_decimal(investment.total_distributions) + total_cf
        )

        # Check if fully redeemed
        if _to_decimal(investment.current_principal) <= Decimal("0.01"):
            investment.status = "fully_redeemed"

    # Update pool statistics
    pool.cumulative_collections = float(
        _to_decimal(pool.cumulative_collections) + total_collection
    )
    pool.cumulative_prepayments = float(
        _to_decimal(pool.cumulative_prepayments) + _to_decimal(total_prepayment)
    )

    db.commit()

    for cf in cash_flows:
        db.refresh(cf)

    return cash_flows


def get_pool_performance(
    pool_id: int,
    db: Session
) -> dict:
    """
    Get pool performance metrics.

    Args:
        pool_id: Pool ID
        db: Database session

    Returns:
        Performance metrics dictionary
    """
    pool = db.query(SecuritizationPool).filter(
        SecuritizationPool.id == pool_id
    ).first()

    if not pool:
        raise ValueError(f"Pool {pool_id} not found")

    # Get loan statistics
    loan_stats = db.query(
        sql_func.count(PoolLoan.id).label("total"),
        sql_func.sum(PoolLoan.current_principal).label("current_principal"),
        sql_func.avg(PoolLoan.current_dpd).label("avg_dpd")
    ).filter(
        and_(
            PoolLoan.pool_id == pool_id,
            PoolLoan.status == "active"
        )
    ).first()

    # Delinquency buckets
    delinquent_30 = db.query(sql_func.count(PoolLoan.id)).filter(
        and_(
            PoolLoan.pool_id == pool_id,
            PoolLoan.status == "active",
            PoolLoan.current_dpd.between(1, 30)
        )
    ).scalar() or 0

    delinquent_60 = db.query(sql_func.count(PoolLoan.id)).filter(
        and_(
            PoolLoan.pool_id == pool_id,
            PoolLoan.status == "active",
            PoolLoan.current_dpd.between(31, 60)
        )
    ).scalar() or 0

    delinquent_90_plus = db.query(sql_func.count(PoolLoan.id)).filter(
        and_(
            PoolLoan.pool_id == pool_id,
            PoolLoan.status == "active",
            PoolLoan.current_dpd >= 61
        )
    ).scalar() or 0

    # Investment summary
    investments = db.query(
        sql_func.count(PoolInvestment.id).label("count"),
        sql_func.sum(PoolInvestment.investment_amount).label("total_invested"),
        sql_func.sum(PoolInvestment.current_principal).label("outstanding"),
        sql_func.sum(PoolInvestment.total_distributions).label("distributed")
    ).filter(
        PoolInvestment.pool_id == pool_id
    ).first()

    return {
        "pool_id": pool_id,
        "pool_code": pool.pool_code,
        "status": pool.status,
        "cutoff_date": pool.cutoff_date.isoformat() if pool.cutoff_date else None,
        "total_loans": loan_stats.total or 0,
        "original_principal": float(pool.total_principal),
        "current_principal": float(loan_stats.current_principal or 0),
        "cumulative_collections": float(pool.cumulative_collections),
        "cumulative_prepayments": float(pool.cumulative_prepayments),
        "avg_dpd": float(loan_stats.avg_dpd or 0),
        "delinquency": {
            "1_30_dpd": delinquent_30,
            "31_60_dpd": delinquent_60,
            "61_plus_dpd": delinquent_90_plus
        },
        "investors": {
            "count": investments.count or 0,
            "total_invested": float(investments.total_invested or 0),
            "outstanding": float(investments.outstanding or 0),
            "distributed": float(investments.distributed or 0)
        }
    }


def get_investor_statement(
    investor_id: int,
    pool_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = None
) -> dict:
    """
    Get investor statement with cash flows.

    Args:
        investor_id: Investor ID
        pool_id: Optional pool filter
        start_date: Optional start date filter
        end_date: Optional end date filter
        db: Database session

    Returns:
        Investor statement dictionary
    """
    investor = db.query(Investor).filter(
        Investor.id == investor_id
    ).first()

    if not investor:
        raise ValueError(f"Investor {investor_id} not found")

    # Get investments
    inv_query = db.query(PoolInvestment).filter(
        PoolInvestment.investor_id == investor_id
    )

    if pool_id:
        inv_query = inv_query.filter(PoolInvestment.pool_id == pool_id)

    investments = inv_query.all()

    investment_details = []
    total_invested = Decimal("0")
    total_outstanding = Decimal("0")
    total_distributed = Decimal("0")

    for inv in investments:
        # Get cash flows
        cf_query = db.query(InvestorCashFlow).filter(
            InvestorCashFlow.investment_id == inv.id
        )

        if start_date:
            cf_query = cf_query.filter(InvestorCashFlow.cash_flow_date >= start_date)
        if end_date:
            cf_query = cf_query.filter(InvestorCashFlow.cash_flow_date <= end_date)

        cash_flows = cf_query.order_by(InvestorCashFlow.cash_flow_date).all()

        investment_details.append({
            "pool_id": inv.pool_id,
            "investment_amount": float(inv.investment_amount),
            "current_principal": float(inv.current_principal),
            "expected_yield": float(inv.expected_yield),
            "tranche": inv.tranche,
            "status": inv.status,
            "cash_flows": [
                {
                    "date": cf.cash_flow_date.isoformat(),
                    "type": cf.cash_flow_type,
                    "amount": float(cf.amount),
                    "tax_deducted": float(cf.tax_deducted),
                    "net_amount": float(cf.net_amount),
                    "status": cf.payment_status
                }
                for cf in cash_flows
            ]
        })

        total_invested += _to_decimal(inv.investment_amount)
        total_outstanding += _to_decimal(inv.current_principal)
        total_distributed += _to_decimal(inv.total_distributions)

    return {
        "investor_id": investor_id,
        "investor_name": investor.name,
        "total_invested": float(total_invested),
        "total_outstanding": float(total_outstanding),
        "total_distributed": float(total_distributed),
        "investments": investment_details
    }
