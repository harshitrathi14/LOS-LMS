"""
ECL (Expected Credit Loss) models - IFRS 9 / Ind AS 109 compliance.

ECL staging is used for provisioning under IFRS 9:
- Stage 1: Performing loans (12-month ECL)
- Stage 2: Underperforming loans (Lifetime ECL - SICR)
- Stage 3: Non-performing/Credit-impaired (Lifetime ECL)

ECLConfiguration: Master configuration for ECL parameters
ECLStaging: Loan-level ECL stage assignment
ECLProvision: Month-end provision calculations
ECLUpload: Bulk ECL upload tracking
ECLMovement: Stage movement tracking
"""

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ECLConfiguration(Base):
    """
    Master configuration for ECL calculation parameters.

    Stores PD, LGD, EAD parameters and staging criteria.
    """
    __tablename__ = "ecl_configurations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Configuration identification
    config_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)

    # Product scope
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("loan_products.id"),
        nullable=True
    )  # Null means applies to all products

    # Staging criteria - DPD based
    stage1_max_dpd: Mapped[int] = mapped_column(Integer, default=30)  # 0-30 DPD
    stage2_max_dpd: Mapped[int] = mapped_column(Integer, default=90)  # 31-90 DPD
    # Stage 3: DPD > stage2_max_dpd

    # Staging criteria - qualitative
    stage2_restructure_flag: Mapped[bool] = mapped_column(Boolean, default=True)
    stage3_write_off_flag: Mapped[bool] = mapped_column(Boolean, default=True)
    stage3_npa_flag: Mapped[bool] = mapped_column(Boolean, default=True)

    # SICR (Significant Increase in Credit Risk) thresholds
    sicr_rating_downgrade_notches: Mapped[int | None] = mapped_column(Integer)
    sicr_pd_increase_threshold: Mapped[float | None] = mapped_column(Numeric(8, 4))

    # PD (Probability of Default) parameters - can be overridden by upload
    pd_stage1_12m: Mapped[float] = mapped_column(Numeric(8, 4), default=0.5)  # 0.5%
    pd_stage2_lifetime: Mapped[float] = mapped_column(Numeric(8, 4), default=5.0)  # 5%
    pd_stage3: Mapped[float] = mapped_column(Numeric(8, 4), default=100.0)  # 100%

    # LGD (Loss Given Default) parameters
    lgd_secured: Mapped[float] = mapped_column(Numeric(8, 4), default=35.0)  # 35%
    lgd_unsecured: Mapped[float] = mapped_column(Numeric(8, 4), default=65.0)  # 65%

    # EAD (Exposure at Default) - typically outstanding + undrawn
    include_undrawn_in_ead: Mapped[bool] = mapped_column(Boolean, default=False)
    ccf_undrawn: Mapped[float] = mapped_column(Numeric(8, 4), default=75.0)  # Credit conversion factor

    # Discounting
    use_effective_interest_rate: Mapped[bool] = mapped_column(Boolean, default=True)
    discount_rate_override: Mapped[float | None] = mapped_column(Numeric(8, 4))

    # Status: active, inactive
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    effective_date: Mapped[Date] = mapped_column(Date)
    expiry_date: Mapped[Date | None] = mapped_column(Date)

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    product = relationship("LoanProduct")


class ECLStaging(Base):
    """
    Loan-level ECL stage assignment.

    Tracks current stage and parameters for each loan.
    """
    __tablename__ = "ecl_staging"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    loan_account_id: Mapped[int] = mapped_column(
        ForeignKey("loan_accounts.id"),
        index=True
    )

    # Current stage: 1, 2, 3
    current_stage: Mapped[int] = mapped_column(Integer, index=True)
    stage_effective_date: Mapped[Date] = mapped_column(Date)

    # Stage assignment reason
    stage_reason: Mapped[str] = mapped_column(String(50))  # dpd, sicr, restructure, npa, manual

    # Risk parameters (can be from upload or calculation)
    pd_12m: Mapped[float | None] = mapped_column(Numeric(8, 4))  # 12-month PD
    pd_lifetime: Mapped[float | None] = mapped_column(Numeric(8, 4))  # Lifetime PD
    lgd: Mapped[float | None] = mapped_column(Numeric(8, 4))

    # EAD components
    ead_on_balance: Mapped[float] = mapped_column(Numeric(18, 2))
    ead_off_balance: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    total_ead: Mapped[float] = mapped_column(Numeric(18, 2))

    # Expected life (for lifetime ECL)
    expected_life_months: Mapped[int | None] = mapped_column(Integer)

    # DPD at staging
    dpd_at_staging: Mapped[int] = mapped_column(Integer)

    # Credit rating (if applicable)
    internal_rating: Mapped[str | None] = mapped_column(String(20))
    external_rating: Mapped[str | None] = mapped_column(String(20))

    # Flags affecting staging
    is_restructured: Mapped[bool] = mapped_column(Boolean, default=False)
    is_npa: Mapped[bool] = mapped_column(Boolean, default=False)
    is_written_off: Mapped[bool] = mapped_column(Boolean, default=False)
    is_fraud: Mapped[bool] = mapped_column(Boolean, default=False)

    # SICR indicators
    sicr_triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    sicr_reason: Mapped[str | None] = mapped_column(String(100))

    # Override
    is_manual_override: Mapped[bool] = mapped_column(Boolean, default=False)
    override_reason: Mapped[str | None] = mapped_column(Text)
    override_by: Mapped[str | None] = mapped_column(String(100))

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    loan_account = relationship("LoanAccount")


class ECLProvision(Base):
    """
    Month-end ECL provision calculation.

    Stores the provision amount as on a specific date (typically month-end).
    """
    __tablename__ = "ecl_provisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    loan_account_id: Mapped[int] = mapped_column(
        ForeignKey("loan_accounts.id"),
        index=True
    )

    # Provision date (month-end)
    provision_date: Mapped[Date] = mapped_column(Date, index=True)
    is_month_end: Mapped[bool] = mapped_column(Boolean, default=True)

    # Stage at provision date
    ecl_stage: Mapped[int] = mapped_column(Integer, index=True)

    # Exposure amounts
    principal_outstanding: Mapped[float] = mapped_column(Numeric(18, 2))
    interest_outstanding: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    fees_outstanding: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    total_exposure: Mapped[float] = mapped_column(Numeric(18, 2))

    # Off-balance exposure (undrawn, guarantees)
    off_balance_exposure: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    total_ead: Mapped[float] = mapped_column(Numeric(18, 2))

    # Risk parameters used
    pd_applied: Mapped[float] = mapped_column(Numeric(8, 4))
    lgd_applied: Mapped[float] = mapped_column(Numeric(8, 4))
    discount_rate: Mapped[float | None] = mapped_column(Numeric(8, 4))

    # ECL calculation
    # For Stage 1: 12-month ECL = EAD * PD_12m * LGD
    # For Stage 2/3: Lifetime ECL = sum(EAD * PD_t * LGD * DF)
    ecl_12_month: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    ecl_lifetime: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    ecl_applied: Mapped[float] = mapped_column(Numeric(18, 2))  # 12m for Stage 1, Lifetime for 2/3

    # Provision amounts
    opening_provision: Mapped[float] = mapped_column(Numeric(18, 2))
    provision_charge: Mapped[float] = mapped_column(Numeric(18, 2))  # P&L impact
    provision_release: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    write_off_utilized: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    recovery_adjustment: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    closing_provision: Mapped[float] = mapped_column(Numeric(18, 2))

    # Coverage ratio
    provision_coverage: Mapped[float] = mapped_column(Numeric(8, 4))  # Provision / Exposure %

    # DPD at provision date
    dpd: Mapped[int] = mapped_column(Integer)

    # Flags
    is_secured: Mapped[bool] = mapped_column(Boolean, default=False)
    collateral_value: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    # Source: calculated, uploaded, manual
    source: Mapped[str] = mapped_column(String(20), default="calculated")
    upload_id: Mapped[int | None] = mapped_column(
        ForeignKey("ecl_uploads.id"),
        nullable=True
    )

    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    loan_account = relationship("LoanAccount")


class ECLUpload(Base):
    """
    Bulk ECL upload tracking.

    Used when ECL is calculated externally and uploaded.
    """
    __tablename__ = "ecl_uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Upload identification
    upload_reference: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    upload_date: Mapped[Date] = mapped_column(Date, index=True)
    provision_date: Mapped[Date] = mapped_column(Date, index=True)  # As-on date for provisions

    # Upload scope
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("loan_products.id"),
        nullable=True
    )

    # Upload statistics
    total_records: Mapped[int] = mapped_column(Integer)
    successful_records: Mapped[int] = mapped_column(Integer, default=0)
    failed_records: Mapped[int] = mapped_column(Integer, default=0)

    # Portfolio totals from upload
    total_exposure: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    total_provision: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    # Stage-wise totals
    stage1_exposure: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    stage1_provision: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    stage1_count: Mapped[int] = mapped_column(Integer, default=0)

    stage2_exposure: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    stage2_provision: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    stage2_count: Mapped[int] = mapped_column(Integer, default=0)

    stage3_exposure: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    stage3_provision: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    stage3_count: Mapped[int] = mapped_column(Integer, default=0)

    # File details
    file_name: Mapped[str | None] = mapped_column(String(255))
    file_path: Mapped[str | None] = mapped_column(String(500))

    # Status: pending, processing, completed, failed
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    error_message: Mapped[str | None] = mapped_column(Text)

    # Approval
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    approved_by: Mapped[str | None] = mapped_column(String(100))
    approved_at: Mapped[DateTime | None] = mapped_column(DateTime)

    uploaded_by: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    product = relationship("LoanProduct")
    provisions: Mapped[list["ECLProvision"]] = relationship(
        "ECLProvision",
        backref="upload"
    )


class ECLMovement(Base):
    """
    Track stage movements for ECL reporting.

    Records when loans move between stages.
    """
    __tablename__ = "ecl_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    loan_account_id: Mapped[int] = mapped_column(
        ForeignKey("loan_accounts.id"),
        index=True
    )

    # Movement details
    movement_date: Mapped[Date] = mapped_column(Date, index=True)
    from_stage: Mapped[int] = mapped_column(Integer)
    to_stage: Mapped[int] = mapped_column(Integer)

    # Movement direction: upgrade (3→2→1), downgrade (1→2→3)
    movement_direction: Mapped[str] = mapped_column(String(20))

    # Reason for movement
    movement_reason: Mapped[str] = mapped_column(String(100))

    # DPD change
    dpd_before: Mapped[int] = mapped_column(Integer)
    dpd_after: Mapped[int] = mapped_column(Integer)

    # Exposure at movement
    exposure_at_movement: Mapped[float] = mapped_column(Numeric(18, 2))

    # Provision impact
    provision_before: Mapped[float] = mapped_column(Numeric(18, 2))
    provision_after: Mapped[float] = mapped_column(Numeric(18, 2))
    provision_impact: Mapped[float] = mapped_column(Numeric(18, 2))

    # Flags at movement
    is_restructured: Mapped[bool] = mapped_column(Boolean, default=False)
    is_npa: Mapped[bool] = mapped_column(Boolean, default=False)
    is_written_off: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    loan_account = relationship("LoanAccount")


class ECLPortfolioSummary(Base):
    """
    Portfolio-level ECL summary for reporting.

    Aggregated view as on a date (typically month-end).
    """
    __tablename__ = "ecl_portfolio_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Summary date
    summary_date: Mapped[Date] = mapped_column(Date, index=True, unique=True)
    is_month_end: Mapped[bool] = mapped_column(Boolean, default=True)

    # Total portfolio
    total_loans: Mapped[int] = mapped_column(Integer)
    total_exposure: Mapped[float] = mapped_column(Numeric(18, 2))
    total_provision: Mapped[float] = mapped_column(Numeric(18, 2))
    overall_coverage: Mapped[float] = mapped_column(Numeric(8, 4))

    # Stage 1 summary
    stage1_loans: Mapped[int] = mapped_column(Integer, default=0)
    stage1_exposure: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    stage1_provision: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    stage1_coverage: Mapped[float] = mapped_column(Numeric(8, 4), default=0)

    # Stage 2 summary
    stage2_loans: Mapped[int] = mapped_column(Integer, default=0)
    stage2_exposure: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    stage2_provision: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    stage2_coverage: Mapped[float] = mapped_column(Numeric(8, 4), default=0)

    # Stage 3 summary
    stage3_loans: Mapped[int] = mapped_column(Integer, default=0)
    stage3_exposure: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    stage3_provision: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    stage3_coverage: Mapped[float] = mapped_column(Numeric(8, 4), default=0)

    # Movement summary (for the period)
    stage1_to_stage2: Mapped[int] = mapped_column(Integer, default=0)
    stage2_to_stage3: Mapped[int] = mapped_column(Integer, default=0)
    stage2_to_stage1: Mapped[int] = mapped_column(Integer, default=0)  # Upgrades
    stage3_to_stage2: Mapped[int] = mapped_column(Integer, default=0)  # Upgrades

    # Write-offs in period
    write_off_count: Mapped[int] = mapped_column(Integer, default=0)
    write_off_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    # Provision movement
    opening_provision: Mapped[float] = mapped_column(Numeric(18, 2))
    provision_charge: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    provision_release: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    write_off_utilized: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    closing_provision: Mapped[float] = mapped_column(Numeric(18, 2))

    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
