"""
ECL (Expected Credit Loss) service - IFRS 9 / Ind AS 109 compliance.

Handles:
- ECL stage assignment
- Provision calculation
- Stage movement tracking
- ECL upload processing
- Portfolio summary generation
"""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models.ecl import (
    ECLConfiguration,
    ECLMovement,
    ECLPortfolioSummary,
    ECLProvision,
    ECLStaging,
    ECLUpload,
)
from app.models.loan_account import LoanAccount


def get_ecl_stage(
    loan: LoanAccount,
    config: ECLConfiguration,
    as_of_date: date
) -> tuple[int, str]:
    """
    Determine ECL stage for a loan based on DPD and flags.

    Returns (stage, reason)

    Stage 1: Performing (12-month ECL)
    Stage 2: Underperforming - SICR (Lifetime ECL)
    Stage 3: Non-performing - Credit impaired (Lifetime ECL)
    """
    # Stage 3 conditions (most severe)
    if loan.is_written_off and config.stage3_write_off_flag:
        return 3, "write_off"

    if loan.is_npa and config.stage3_npa_flag:
        return 3, "npa"

    if loan.dpd > config.stage2_max_dpd:
        return 3, "dpd"

    if loan.is_fraud:
        return 3, "fraud"

    # Stage 2 conditions
    if loan.is_restructured and config.stage2_restructure_flag:
        return 2, "restructure"

    if loan.dpd > config.stage1_max_dpd:
        return 2, "dpd"

    if loan.sicr_flag:
        return 2, "sicr"

    # Default to Stage 1
    return 1, "performing"


def calculate_ecl(
    ead: Decimal,
    pd: Decimal,
    lgd: Decimal,
    stage: int,
    discount_rate: Optional[Decimal] = None,
    expected_life_months: Optional[int] = None
) -> dict:
    """
    Calculate ECL amount.

    For Stage 1: 12-month ECL = EAD * PD_12m * LGD
    For Stage 2/3: Lifetime ECL (simplified) = EAD * PD_lifetime * LGD

    Returns dict with ecl_12_month, ecl_lifetime, ecl_applied
    """
    pd_decimal = Decimal(str(pd)) / Decimal("100")
    lgd_decimal = Decimal(str(lgd)) / Decimal("100")

    # 12-month ECL (always calculated)
    ecl_12_month = (ead * pd_decimal * lgd_decimal).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    # Lifetime ECL (simplified - actual calculation would use cash flow projection)
    # For simplicity, using PD as lifetime PD for Stage 2/3
    ecl_lifetime = ecl_12_month  # Base case

    if stage in [2, 3] and expected_life_months:
        # Simplified lifetime ECL: scale by expected life
        life_factor = Decimal(str(expected_life_months)) / Decimal("12")
        ecl_lifetime = (ead * pd_decimal * lgd_decimal * life_factor).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    # Stage 3: 100% PD
    if stage == 3:
        ecl_lifetime = (ead * lgd_decimal).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    # Applied ECL based on stage
    ecl_applied = ecl_12_month if stage == 1 else ecl_lifetime

    return {
        "ecl_12_month": ecl_12_month,
        "ecl_lifetime": ecl_lifetime,
        "ecl_applied": ecl_applied
    }


def assign_ecl_stage(
    loan_account_id: int,
    as_of_date: date,
    db: Session,
    config_id: Optional[int] = None
) -> ECLStaging:
    """
    Assign or update ECL stage for a loan.
    """
    loan = db.query(LoanAccount).get(loan_account_id)
    if not loan:
        raise ValueError(f"Loan {loan_account_id} not found")

    # Get configuration
    config = None
    if config_id:
        config = db.query(ECLConfiguration).get(config_id)
    else:
        # Get active config for product
        config = db.query(ECLConfiguration).filter(
            and_(
                ECLConfiguration.is_active == True,
                (ECLConfiguration.product_id == None) |
                (ECLConfiguration.product_id == loan.application.product_id)
            )
        ).first()

    if not config:
        # Use default staging
        config = ECLConfiguration(
            stage1_max_dpd=30,
            stage2_max_dpd=90,
            stage2_restructure_flag=True,
            stage3_write_off_flag=True,
            stage3_npa_flag=True,
            pd_stage1_12m=0.5,
            pd_stage2_lifetime=5.0,
            pd_stage3=100.0,
            lgd_unsecured=65.0
        )

    # Get current stage
    stage, reason = get_ecl_stage(loan, config, as_of_date)

    # Check for existing staging
    existing = db.query(ECLStaging).filter(
        ECLStaging.loan_account_id == loan_account_id
    ).first()

    previous_stage = existing.current_stage if existing else 1

    # Determine PD based on stage
    if stage == 1:
        pd = Decimal(str(config.pd_stage1_12m))
    elif stage == 2:
        pd = Decimal(str(config.pd_stage2_lifetime))
    else:
        pd = Decimal(str(config.pd_stage3))

    lgd = Decimal(str(config.lgd_unsecured))  # Simplified - should check if secured

    # Calculate EAD
    ead = (
        Decimal(str(loan.principal_outstanding)) +
        Decimal(str(loan.interest_outstanding)) +
        Decimal(str(loan.fees_outstanding))
    )

    if existing:
        # Update existing
        existing.current_stage = stage
        existing.stage_effective_date = as_of_date
        existing.stage_reason = reason
        existing.pd_12m = float(pd) if stage == 1 else None
        existing.pd_lifetime = float(pd) if stage > 1 else None
        existing.lgd = float(lgd)
        existing.ead_on_balance = float(ead)
        existing.total_ead = float(ead)
        existing.dpd_at_staging = loan.dpd
        existing.is_restructured = loan.is_restructured
        existing.is_npa = loan.is_npa
        existing.is_written_off = loan.is_written_off
        staging = existing
    else:
        # Create new
        staging = ECLStaging(
            loan_account_id=loan_account_id,
            current_stage=stage,
            stage_effective_date=as_of_date,
            stage_reason=reason,
            pd_12m=float(pd) if stage == 1 else None,
            pd_lifetime=float(pd) if stage > 1 else None,
            lgd=float(lgd),
            ead_on_balance=float(ead),
            ead_off_balance=0,
            total_ead=float(ead),
            dpd_at_staging=loan.dpd,
            is_restructured=loan.is_restructured,
            is_npa=loan.is_npa,
            is_written_off=loan.is_written_off
        )
        db.add(staging)

    # Record stage movement if changed
    if previous_stage != stage:
        movement = ECLMovement(
            loan_account_id=loan_account_id,
            movement_date=as_of_date,
            from_stage=previous_stage,
            to_stage=stage,
            movement_direction="downgrade" if stage > previous_stage else "upgrade",
            movement_reason=reason,
            dpd_before=loan.dpd,  # Should track previous DPD
            dpd_after=loan.dpd,
            exposure_at_movement=float(ead),
            provision_before=float(loan.ecl_provision),
            provision_after=0,  # Will be updated after provision calc
            provision_impact=0,
            is_restructured=loan.is_restructured,
            is_npa=loan.is_npa,
            is_written_off=loan.is_written_off
        )
        db.add(movement)

    # Update loan account
    loan.ecl_stage = stage
    loan.ecl_stage_date = as_of_date

    db.flush()
    return staging


def calculate_provision(
    loan_account_id: int,
    provision_date: date,
    db: Session,
    config_id: Optional[int] = None
) -> ECLProvision:
    """
    Calculate ECL provision for a loan as on a date.
    """
    loan = db.query(LoanAccount).get(loan_account_id)
    if not loan:
        raise ValueError(f"Loan {loan_account_id} not found")

    # Ensure staging is current
    staging = assign_ecl_stage(loan_account_id, provision_date, db, config_id)

    # Get previous provision
    prev_provision = db.query(ECLProvision).filter(
        and_(
            ECLProvision.loan_account_id == loan_account_id,
            ECLProvision.provision_date < provision_date
        )
    ).order_by(ECLProvision.provision_date.desc()).first()

    opening_provision = Decimal(str(prev_provision.closing_provision)) if prev_provision else Decimal("0")

    # Calculate EAD
    principal = Decimal(str(loan.principal_outstanding))
    interest = Decimal(str(loan.interest_outstanding))
    fees = Decimal(str(loan.fees_outstanding))
    total_exposure = principal + interest + fees
    total_ead = total_exposure  # Simplified - no off-balance

    # Get PD and LGD from staging
    pd = Decimal(str(staging.pd_12m or staging.pd_lifetime or 0))
    lgd = Decimal(str(staging.lgd or 65))

    # Calculate ECL
    ecl_result = calculate_ecl(
        ead=total_ead,
        pd=pd,
        lgd=lgd,
        stage=staging.current_stage,
        expected_life_months=staging.expected_life_months
    )

    closing_provision = ecl_result["ecl_applied"]
    provision_charge = max(Decimal("0"), closing_provision - opening_provision)
    provision_release = max(Decimal("0"), opening_provision - closing_provision)

    # Coverage ratio
    coverage = (
        closing_provision / total_exposure * Decimal("100")
        if total_exposure > 0 else Decimal("0")
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    provision = ECLProvision(
        loan_account_id=loan_account_id,
        provision_date=provision_date,
        is_month_end=provision_date.day == 1,  # Simplified check
        ecl_stage=staging.current_stage,
        principal_outstanding=float(principal),
        interest_outstanding=float(interest),
        fees_outstanding=float(fees),
        total_exposure=float(total_exposure),
        off_balance_exposure=0,
        total_ead=float(total_ead),
        pd_applied=float(pd),
        lgd_applied=float(lgd),
        ecl_12_month=float(ecl_result["ecl_12_month"]),
        ecl_lifetime=float(ecl_result["ecl_lifetime"]),
        ecl_applied=float(ecl_result["ecl_applied"]),
        opening_provision=float(opening_provision),
        provision_charge=float(provision_charge),
        provision_release=float(provision_release),
        closing_provision=float(closing_provision),
        provision_coverage=float(coverage),
        dpd=loan.dpd,
        source="calculated"
    )

    db.add(provision)

    # Update loan account
    loan.ecl_provision = float(closing_provision)
    loan.ecl_provision_date = provision_date

    db.flush()
    return provision


def run_monthly_ecl_batch(
    provision_date: date,
    db: Session,
    product_id: Optional[int] = None
) -> dict:
    """
    Run month-end ECL calculation for all active loans.
    """
    query = db.query(LoanAccount).filter(
        LoanAccount.status.in_(["active", "delinquent", "npa"])
    )

    if product_id:
        query = query.join(LoanAccount.application).filter(
            LoanAccount.application.has(product_id=product_id)
        )

    loans = query.all()

    results = {
        "provision_date": provision_date,
        "total_loans": len(loans),
        "processed": 0,
        "errors": 0,
        "stage1_count": 0,
        "stage2_count": 0,
        "stage3_count": 0,
        "total_exposure": Decimal("0"),
        "total_provision": Decimal("0")
    }

    for loan in loans:
        try:
            provision = calculate_provision(loan.id, provision_date, db)
            results["processed"] += 1
            results[f"stage{provision.ecl_stage}_count"] += 1
            results["total_exposure"] += Decimal(str(provision.total_exposure))
            results["total_provision"] += Decimal(str(provision.closing_provision))
        except Exception as e:
            results["errors"] += 1

    # Create portfolio summary
    create_portfolio_summary(provision_date, db)

    db.flush()
    return results


def create_portfolio_summary(provision_date: date, db: Session) -> ECLPortfolioSummary:
    """
    Create portfolio-level ECL summary for reporting.
    """
    # Aggregate from provisions
    provisions = db.query(ECLProvision).filter(
        ECLProvision.provision_date == provision_date
    ).all()

    if not provisions:
        raise ValueError(f"No provisions found for {provision_date}")

    # Get previous summary
    prev_summary = db.query(ECLPortfolioSummary).filter(
        ECLPortfolioSummary.summary_date < provision_date
    ).order_by(ECLPortfolioSummary.summary_date.desc()).first()

    opening_provision = Decimal(str(prev_summary.closing_provision)) if prev_summary else Decimal("0")

    # Calculate stage-wise aggregates
    stage_data = {1: {"count": 0, "exposure": Decimal("0"), "provision": Decimal("0")},
                  2: {"count": 0, "exposure": Decimal("0"), "provision": Decimal("0")},
                  3: {"count": 0, "exposure": Decimal("0"), "provision": Decimal("0")}}

    total_exposure = Decimal("0")
    total_provision = Decimal("0")

    for p in provisions:
        stage = p.ecl_stage
        stage_data[stage]["count"] += 1
        stage_data[stage]["exposure"] += Decimal(str(p.total_exposure))
        stage_data[stage]["provision"] += Decimal(str(p.closing_provision))
        total_exposure += Decimal(str(p.total_exposure))
        total_provision += Decimal(str(p.closing_provision))

    # Get movements
    movements = db.query(ECLMovement).filter(
        ECLMovement.movement_date == provision_date
    ).all()

    stage1_to_2 = sum(1 for m in movements if m.from_stage == 1 and m.to_stage == 2)
    stage2_to_3 = sum(1 for m in movements if m.from_stage == 2 and m.to_stage == 3)
    stage2_to_1 = sum(1 for m in movements if m.from_stage == 2 and m.to_stage == 1)
    stage3_to_2 = sum(1 for m in movements if m.from_stage == 3 and m.to_stage == 2)

    provision_charge = max(Decimal("0"), total_provision - opening_provision)
    provision_release = max(Decimal("0"), opening_provision - total_provision)

    summary = ECLPortfolioSummary(
        summary_date=provision_date,
        is_month_end=True,
        total_loans=len(provisions),
        total_exposure=float(total_exposure),
        total_provision=float(total_provision),
        overall_coverage=float(
            total_provision / total_exposure * 100 if total_exposure > 0 else 0
        ),
        stage1_loans=stage_data[1]["count"],
        stage1_exposure=float(stage_data[1]["exposure"]),
        stage1_provision=float(stage_data[1]["provision"]),
        stage1_coverage=float(
            stage_data[1]["provision"] / stage_data[1]["exposure"] * 100
            if stage_data[1]["exposure"] > 0 else 0
        ),
        stage2_loans=stage_data[2]["count"],
        stage2_exposure=float(stage_data[2]["exposure"]),
        stage2_provision=float(stage_data[2]["provision"]),
        stage2_coverage=float(
            stage_data[2]["provision"] / stage_data[2]["exposure"] * 100
            if stage_data[2]["exposure"] > 0 else 0
        ),
        stage3_loans=stage_data[3]["count"],
        stage3_exposure=float(stage_data[3]["exposure"]),
        stage3_provision=float(stage_data[3]["provision"]),
        stage3_coverage=float(
            stage_data[3]["provision"] / stage_data[3]["exposure"] * 100
            if stage_data[3]["exposure"] > 0 else 0
        ),
        stage1_to_stage2=stage1_to_2,
        stage2_to_stage3=stage2_to_3,
        stage2_to_stage1=stage2_to_1,
        stage3_to_stage2=stage3_to_2,
        opening_provision=float(opening_provision),
        provision_charge=float(provision_charge),
        provision_release=float(provision_release),
        closing_provision=float(total_provision)
    )

    db.add(summary)
    db.flush()
    return summary


def process_ecl_upload(
    upload_id: int,
    provisions_data: List[dict],
    db: Session
) -> ECLUpload:
    """
    Process bulk ECL upload from external source.

    Each item in provisions_data should have:
    - loan_account_id or account_number
    - ecl_stage
    - pd, lgd
    - provision_amount
    """
    upload = db.query(ECLUpload).get(upload_id)
    if not upload:
        raise ValueError(f"Upload {upload_id} not found")

    upload.status = "processing"
    db.flush()

    successful = 0
    failed = 0
    stage_totals = {1: {"exposure": Decimal("0"), "provision": Decimal("0"), "count": 0},
                    2: {"exposure": Decimal("0"), "provision": Decimal("0"), "count": 0},
                    3: {"exposure": Decimal("0"), "provision": Decimal("0"), "count": 0}}

    for item in provisions_data:
        try:
            # Get loan
            loan = None
            if "loan_account_id" in item:
                loan = db.query(LoanAccount).get(item["loan_account_id"])
            elif "account_number" in item:
                loan = db.query(LoanAccount).filter(
                    LoanAccount.account_number == item["account_number"]
                ).first()

            if not loan:
                failed += 1
                continue

            stage = item.get("ecl_stage", 1)
            provision_amount = Decimal(str(item.get("provision_amount", 0)))

            # Get previous provision
            prev = db.query(ECLProvision).filter(
                and_(
                    ECLProvision.loan_account_id == loan.id,
                    ECLProvision.provision_date < upload.provision_date
                )
            ).order_by(ECLProvision.provision_date.desc()).first()

            opening = Decimal(str(prev.closing_provision)) if prev else Decimal("0")

            exposure = (
                Decimal(str(loan.principal_outstanding)) +
                Decimal(str(loan.interest_outstanding)) +
                Decimal(str(loan.fees_outstanding))
            )

            provision = ECLProvision(
                loan_account_id=loan.id,
                provision_date=upload.provision_date,
                is_month_end=True,
                ecl_stage=stage,
                principal_outstanding=float(loan.principal_outstanding),
                interest_outstanding=float(loan.interest_outstanding),
                fees_outstanding=float(loan.fees_outstanding),
                total_exposure=float(exposure),
                total_ead=float(exposure),
                pd_applied=float(item.get("pd", 0)),
                lgd_applied=float(item.get("lgd", 65)),
                ecl_applied=float(provision_amount),
                ecl_12_month=float(provision_amount) if stage == 1 else 0,
                ecl_lifetime=float(provision_amount) if stage > 1 else 0,
                opening_provision=float(opening),
                provision_charge=float(max(Decimal("0"), provision_amount - opening)),
                provision_release=float(max(Decimal("0"), opening - provision_amount)),
                closing_provision=float(provision_amount),
                provision_coverage=float(
                    provision_amount / exposure * 100 if exposure > 0 else 0
                ),
                dpd=loan.dpd,
                source="uploaded",
                upload_id=upload_id
            )

            db.add(provision)

            # Update loan
            loan.ecl_stage = stage
            loan.ecl_provision = float(provision_amount)
            loan.ecl_provision_date = upload.provision_date

            successful += 1
            stage_totals[stage]["count"] += 1
            stage_totals[stage]["exposure"] += exposure
            stage_totals[stage]["provision"] += provision_amount

        except Exception as e:
            failed += 1

    # Update upload record
    upload.successful_records = successful
    upload.failed_records = failed
    upload.total_exposure = float(sum(s["exposure"] for s in stage_totals.values()))
    upload.total_provision = float(sum(s["provision"] for s in stage_totals.values()))
    upload.stage1_count = stage_totals[1]["count"]
    upload.stage1_exposure = float(stage_totals[1]["exposure"])
    upload.stage1_provision = float(stage_totals[1]["provision"])
    upload.stage2_count = stage_totals[2]["count"]
    upload.stage2_exposure = float(stage_totals[2]["exposure"])
    upload.stage2_provision = float(stage_totals[2]["provision"])
    upload.stage3_count = stage_totals[3]["count"]
    upload.stage3_exposure = float(stage_totals[3]["exposure"])
    upload.stage3_provision = float(stage_totals[3]["provision"])
    upload.status = "completed" if failed == 0 else "completed_with_errors"

    db.flush()
    return upload
