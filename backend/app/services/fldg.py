"""
FLDG (First Loss Default Guarantee) service.

Handles:
- FLDG arrangement management
- FLDG utilization on defaults
- FLDG recovery tracking
- Balance management
"""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models.fldg import FLDGArrangement, FLDGRecovery, FLDGUtilization
from app.models.loan_account import LoanAccount
from app.models.loan_participation import LoanParticipation
from app.models.write_off import WriteOff


def create_fldg_arrangement(
    arrangement_code: str,
    name: str,
    originator_id: int,
    lender_id: int,
    fldg_type: str,
    fldg_percent: Optional[float],
    effective_date: date,
    db: Session,
    **kwargs
) -> FLDGArrangement:
    """
    Create a new FLDG arrangement.

    Args:
        arrangement_code: Unique code for the arrangement
        name: Descriptive name
        originator_id: Partner ID of originator (provides FLDG)
        lender_id: Partner ID of lender (protected by FLDG)
        fldg_type: first_loss or second_loss
        fldg_percent: FLDG as % of portfolio
        effective_date: Date arrangement becomes effective
        db: Database session
        **kwargs: Additional fields
    """
    arrangement = FLDGArrangement(
        arrangement_code=arrangement_code,
        name=name,
        originator_id=originator_id,
        lender_id=lender_id,
        fldg_type=fldg_type,
        fldg_percent=fldg_percent,
        effective_date=effective_date,
        effective_fldg_limit=kwargs.get("effective_fldg_limit", Decimal("0")),
        current_fldg_balance=kwargs.get("effective_fldg_limit", Decimal("0")),
        **{k: v for k, v in kwargs.items() if k != "effective_fldg_limit"}
    )
    db.add(arrangement)
    db.flush()
    return arrangement


def calculate_fldg_limit(
    arrangement_id: int,
    portfolio_outstanding: Decimal,
    db: Session
) -> Decimal:
    """
    Calculate effective FLDG limit based on portfolio outstanding.

    Returns the lower of:
    - Percentage-based limit (fldg_percent * portfolio)
    - Absolute limit (fldg_absolute_amount)
    """
    arrangement = db.query(FLDGArrangement).get(arrangement_id)
    if not arrangement:
        raise ValueError(f"FLDG arrangement {arrangement_id} not found")

    limits = []

    if arrangement.fldg_percent:
        percent_limit = (
            portfolio_outstanding *
            Decimal(str(arrangement.fldg_percent)) /
            Decimal("100")
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        limits.append(percent_limit)

    if arrangement.fldg_absolute_amount:
        limits.append(Decimal(str(arrangement.fldg_absolute_amount)))

    if not limits:
        return Decimal("0")

    return min(limits)


def check_fldg_availability(
    arrangement_id: int,
    required_amount: Decimal,
    db: Session
) -> dict:
    """
    Check if FLDG is available for a claim.

    Returns dict with:
    - available: bool
    - balance: current FLDG balance
    - shortfall: amount by which claim exceeds balance
    """
    arrangement = db.query(FLDGArrangement).get(arrangement_id)
    if not arrangement:
        raise ValueError(f"FLDG arrangement {arrangement_id} not found")

    balance = Decimal(str(arrangement.current_fldg_balance))
    required = Decimal(str(required_amount))

    return {
        "available": balance >= required,
        "balance": balance,
        "required": required,
        "shortfall": max(Decimal("0"), required - balance)
    }


def trigger_fldg_utilization(
    arrangement_id: int,
    loan_account_id: int,
    trigger_reason: str,
    db: Session,
    write_off_id: Optional[int] = None
) -> FLDGUtilization:
    """
    Trigger FLDG utilization for a defaulted loan.

    Args:
        arrangement_id: FLDG arrangement ID
        loan_account_id: Loan account that defaulted
        trigger_reason: npa, write_off, dpd_threshold
        db: Database session
        write_off_id: Optional write-off ID if triggered by write-off
    """
    arrangement = db.query(FLDGArrangement).get(arrangement_id)
    loan = db.query(LoanAccount).get(loan_account_id)

    if not arrangement or not loan:
        raise ValueError("Invalid arrangement or loan")

    # Check if already utilized for this loan
    existing = db.query(FLDGUtilization).filter(
        and_(
            FLDGUtilization.arrangement_id == arrangement_id,
            FLDGUtilization.loan_account_id == loan_account_id,
            FLDGUtilization.status.in_(["pending", "approved", "settled"])
        )
    ).first()

    if existing:
        raise ValueError(f"FLDG already utilized for loan {loan_account_id}")

    # Get participation to determine partner's share
    participation = db.query(LoanParticipation).filter(
        and_(
            LoanParticipation.loan_account_id == loan_account_id,
            LoanParticipation.fldg_arrangement_id == arrangement_id
        )
    ).first()

    # Calculate claim amounts
    share_percent = Decimal(str(participation.share_percent)) if participation else Decimal("100")

    principal_claim = (
        Decimal(str(loan.principal_outstanding)) *
        share_percent / Decimal("100")
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    interest_claim = Decimal("0")
    fees_claim = Decimal("0")

    if arrangement.covers_interest:
        interest_claim = (
            Decimal(str(loan.interest_outstanding)) *
            share_percent / Decimal("100")
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if arrangement.covers_fees:
        fees_claim = (
            Decimal(str(loan.fees_outstanding)) *
            share_percent / Decimal("100")
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    total_claim = principal_claim + interest_claim + fees_claim

    # For second loss, check if first loss threshold is met
    if arrangement.fldg_type == "second_loss":
        if total_claim <= Decimal(str(arrangement.first_loss_threshold)):
            # First loss threshold not met, no second loss utilization
            raise ValueError("First loss threshold not met for second loss utilization")
        # Reduce claim by first loss threshold
        total_claim = total_claim - Decimal(str(arrangement.first_loss_threshold))

    balance_before = Decimal(str(arrangement.current_fldg_balance))
    approved_amount = min(total_claim, balance_before)
    balance_after = balance_before - approved_amount

    utilization = FLDGUtilization(
        arrangement_id=arrangement_id,
        loan_account_id=loan_account_id,
        utilization_date=date.today(),
        trigger_reason=trigger_reason,
        principal_claimed=principal_claim,
        interest_claimed=interest_claim,
        fees_claimed=fees_claim,
        total_claimed=total_claim,
        principal_approved=min(principal_claim, approved_amount),
        interest_approved=min(interest_claim, max(Decimal("0"), approved_amount - principal_claim)),
        fees_approved=min(fees_claim, max(Decimal("0"), approved_amount - principal_claim - interest_claim)),
        total_approved=approved_amount,
        write_off_id=write_off_id,
        dpd_at_utilization=loan.dpd,
        fldg_balance_before=balance_before,
        fldg_balance_after=balance_after,
        status="pending"
    )

    db.add(utilization)
    db.flush()

    return utilization


def approve_fldg_utilization(
    utilization_id: int,
    approved_by: str,
    db: Session,
    approved_amount: Optional[Decimal] = None
) -> FLDGUtilization:
    """
    Approve FLDG utilization and update balances.
    """
    utilization = db.query(FLDGUtilization).get(utilization_id)
    if not utilization:
        raise ValueError(f"Utilization {utilization_id} not found")

    if utilization.status != "pending":
        raise ValueError(f"Utilization is not pending: {utilization.status}")

    arrangement = db.query(FLDGArrangement).get(utilization.arrangement_id)

    # Use provided amount or claimed amount
    final_amount = approved_amount if approved_amount else utilization.total_claimed
    final_amount = min(Decimal(str(final_amount)), Decimal(str(arrangement.current_fldg_balance)))

    # Update utilization
    utilization.total_approved = final_amount
    utilization.fldg_balance_after = (
        Decimal(str(arrangement.current_fldg_balance)) - final_amount
    )
    utilization.status = "approved"
    utilization.approved_by = approved_by
    utilization.approved_at = func.now()

    # Update arrangement balance
    arrangement.current_fldg_balance = float(utilization.fldg_balance_after)
    arrangement.total_utilized = float(
        Decimal(str(arrangement.total_utilized)) + final_amount
    )

    # Update participation write-off tracking
    participation = db.query(LoanParticipation).filter(
        and_(
            LoanParticipation.loan_account_id == utilization.loan_account_id,
            LoanParticipation.fldg_arrangement_id == utilization.arrangement_id
        )
    ).first()

    if participation:
        participation.fldg_utilized = float(
            Decimal(str(participation.fldg_utilized or 0)) + final_amount
        )
        # Net write-off = Total write-off - FLDG utilized
        participation.net_write_off = float(
            Decimal(str(participation.write_off_amount or 0)) -
            Decimal(str(participation.fldg_utilized or 0))
        )

    db.flush()
    return utilization


def record_fldg_recovery(
    utilization_id: int,
    recovery_date: date,
    principal_recovered: Decimal,
    interest_recovered: Decimal,
    recovery_source: str,
    db: Session,
    write_off_recovery_id: Optional[int] = None
) -> FLDGRecovery:
    """
    Record recovery against FLDG utilization.

    When amounts are recovered from a written-off loan, portion may be
    returned to the FLDG pool.
    """
    utilization = db.query(FLDGUtilization).get(utilization_id)
    if not utilization:
        raise ValueError(f"Utilization {utilization_id} not found")

    total_recovered = principal_recovered + interest_recovered

    # Calculate amount to return to FLDG
    # Generally, recoveries first go to FLDG to replenish the pool
    amount_to_fldg = min(
        total_recovered,
        Decimal(str(utilization.total_approved)) -
        sum(Decimal(str(r.amount_returned_to_fldg)) for r in utilization.recoveries)
    )

    recovery = FLDGRecovery(
        utilization_id=utilization_id,
        recovery_date=recovery_date,
        principal_recovered=float(principal_recovered),
        interest_recovered=float(interest_recovered),
        total_recovered=float(total_recovered),
        amount_returned_to_fldg=float(amount_to_fldg),
        recovery_source=recovery_source,
        write_off_recovery_id=write_off_recovery_id
    )

    db.add(recovery)

    # Update arrangement balance
    arrangement = db.query(FLDGArrangement).get(utilization.arrangement_id)
    arrangement.current_fldg_balance = float(
        Decimal(str(arrangement.current_fldg_balance)) + amount_to_fldg
    )
    arrangement.total_recovered = float(
        Decimal(str(arrangement.total_recovered)) + amount_to_fldg
    )

    # Update utilization status if fully recovered
    total_fldg_recovered = sum(
        Decimal(str(r.amount_returned_to_fldg))
        for r in utilization.recoveries
    ) + amount_to_fldg

    if total_fldg_recovered >= Decimal(str(utilization.total_approved)):
        utilization.status = "recovered"

    db.flush()
    return recovery


def get_fldg_summary(arrangement_id: int, db: Session) -> dict:
    """
    Get summary of FLDG arrangement status.
    """
    arrangement = db.query(FLDGArrangement).get(arrangement_id)
    if not arrangement:
        raise ValueError(f"Arrangement {arrangement_id} not found")

    # Get utilization summary
    utilizations = db.query(FLDGUtilization).filter(
        FLDGUtilization.arrangement_id == arrangement_id
    ).all()

    pending_claims = sum(
        Decimal(str(u.total_claimed))
        for u in utilizations if u.status == "pending"
    )

    approved_claims = sum(
        Decimal(str(u.total_approved))
        for u in utilizations if u.status in ["approved", "settled", "recovered"]
    )

    total_recoveries = sum(
        Decimal(str(r.amount_returned_to_fldg))
        for u in utilizations
        for r in u.recoveries
    )

    return {
        "arrangement_code": arrangement.arrangement_code,
        "fldg_type": arrangement.fldg_type,
        "effective_limit": Decimal(str(arrangement.effective_fldg_limit)),
        "current_balance": Decimal(str(arrangement.current_fldg_balance)),
        "total_utilized": Decimal(str(arrangement.total_utilized)),
        "total_recovered": Decimal(str(arrangement.total_recovered)),
        "pending_claims": pending_claims,
        "approved_claims": approved_claims,
        "utilization_count": len(utilizations),
        "utilization_rate": (
            Decimal(str(arrangement.total_utilized)) /
            Decimal(str(arrangement.effective_fldg_limit)) * 100
            if arrangement.effective_fldg_limit else Decimal("0")
        ),
        "status": arrangement.status
    }


def check_top_up_required(arrangement_id: int, db: Session) -> dict:
    """
    Check if FLDG top-up is required based on threshold.
    """
    arrangement = db.query(FLDGArrangement).get(arrangement_id)
    if not arrangement:
        raise ValueError(f"Arrangement {arrangement_id} not found")

    if not arrangement.requires_top_up:
        return {"required": False, "reason": "Top-up not required for this arrangement"}

    current_balance = Decimal(str(arrangement.current_fldg_balance))
    effective_limit = Decimal(str(arrangement.effective_fldg_limit))
    threshold_percent = Decimal(str(arrangement.top_up_threshold_percent))

    threshold_amount = effective_limit * threshold_percent / Decimal("100")

    if current_balance < threshold_amount:
        top_up_amount = effective_limit - current_balance
        return {
            "required": True,
            "current_balance": current_balance,
            "threshold": threshold_amount,
            "top_up_amount": top_up_amount,
            "reason": f"Balance {current_balance} below threshold {threshold_amount}"
        }

    return {
        "required": False,
        "current_balance": current_balance,
        "threshold": threshold_amount,
        "reason": "Balance above threshold"
    }
