"""
Loan Lifecycle Management Service

Handles restructuring, prepayment, closure, and write-off operations.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any, List
from dataclasses import dataclass


def to_decimal(value: Any) -> Decimal:
    """Convert any numeric value to Decimal."""
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass
class RestructureImpact:
    """Impact of restructuring on loan terms."""
    new_emi: Decimal
    new_tenure: int
    new_rate: Decimal
    total_interest_change: Decimal
    monthly_savings: Decimal


@dataclass
class PrepaymentOption:
    """Prepayment option with impact analysis."""
    option_type: str  # reduce_emi, reduce_tenure
    new_emi: Decimal
    new_tenure: int
    interest_saved: Decimal
    total_savings: Decimal


@dataclass
class ClosureEligibility:
    """Loan closure eligibility check result."""
    can_close: bool
    closure_type: str  # normal, settlement, foreclosure, writeoff
    outstanding_amount: Decimal
    settlement_amount: Optional[Decimal]
    reason: str


@dataclass
class WriteOffSummary:
    """Write-off summary with recovery tracking."""
    principal_written_off: Decimal
    interest_written_off: Decimal
    fees_written_off: Decimal
    total_written_off: Decimal
    recovered_amount: Decimal
    net_loss: Decimal


class RestructureService:
    """Service for loan restructuring calculations."""

    @staticmethod
    def calculate_restructure_impact(
        principal_outstanding: Decimal,
        current_rate: Decimal,
        current_tenure: int,
        current_emi: Decimal,
        new_rate: Optional[Decimal] = None,
        new_tenure: Optional[int] = None,
        principal_waiver: Decimal = Decimal("0")
    ) -> RestructureImpact:
        """Calculate the impact of restructuring on loan terms."""
        principal = to_decimal(principal_outstanding) - to_decimal(principal_waiver)
        rate = to_decimal(new_rate) if new_rate is not None else to_decimal(current_rate)
        tenure = new_tenure if new_tenure is not None else current_tenure

        # Calculate new EMI
        monthly_rate = rate / Decimal("12") / Decimal("100")
        if monthly_rate > 0:
            factor = (1 + monthly_rate) ** tenure
            new_emi = (principal * monthly_rate * factor / (factor - 1)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        else:
            new_emi = (principal / tenure).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Calculate total interest
        new_total_interest = (new_emi * tenure) - principal
        old_total_interest = (to_decimal(current_emi) * current_tenure) - to_decimal(principal_outstanding)

        return RestructureImpact(
            new_emi=new_emi,
            new_tenure=tenure,
            new_rate=rate,
            total_interest_change=new_total_interest - old_total_interest,
            monthly_savings=to_decimal(current_emi) - new_emi
        )


class PrepaymentService:
    """Service for prepayment calculations."""

    @staticmethod
    def get_prepayment_options(
        principal_outstanding: Decimal,
        interest_rate: Decimal,
        remaining_tenure: int,
        current_emi: Decimal,
        prepayment_amount: Decimal
    ) -> List[PrepaymentOption]:
        """Get prepayment options with impact analysis."""
        principal = to_decimal(principal_outstanding)
        rate = to_decimal(interest_rate)
        prepay = to_decimal(prepayment_amount)
        emi = to_decimal(current_emi)

        new_principal = principal - prepay
        monthly_rate = rate / Decimal("12") / Decimal("100")

        options = []

        # Option 1: Reduce EMI (same tenure)
        if monthly_rate > 0:
            factor = (1 + monthly_rate) ** remaining_tenure
            new_emi_reduce = (new_principal * monthly_rate * factor / (factor - 1)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        else:
            new_emi_reduce = (new_principal / remaining_tenure).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

        old_total = emi * remaining_tenure
        new_total_reduce = new_emi_reduce * remaining_tenure

        options.append(PrepaymentOption(
            option_type="reduce_emi",
            new_emi=new_emi_reduce,
            new_tenure=remaining_tenure,
            interest_saved=old_total - new_total_reduce - prepay,
            total_savings=old_total - new_total_reduce
        ))

        # Option 2: Reduce tenure (same EMI)
        if monthly_rate > 0 and emi > 0:
            import math
            # n = log(EMI / (EMI - P*r)) / log(1+r)
            numerator = float(emi)
            denominator = float(emi - new_principal * monthly_rate)
            if denominator > 0:
                new_tenure_reduce = int(math.ceil(
                    math.log(numerator / denominator) / math.log(float(1 + monthly_rate))
                ))
                new_total_tenure = emi * new_tenure_reduce

                options.append(PrepaymentOption(
                    option_type="reduce_tenure",
                    new_emi=emi,
                    new_tenure=new_tenure_reduce,
                    interest_saved=old_total - new_total_tenure - prepay,
                    total_savings=old_total - new_total_tenure
                ))

        return options


class ClosureService:
    """Service for loan closure operations."""

    @staticmethod
    def can_close_loan(
        principal_outstanding: Decimal,
        interest_outstanding: Decimal,
        fees_outstanding: Decimal,
        dpd: int,
        is_npa: bool = False
    ) -> ClosureEligibility:
        """Check if loan can be closed and determine closure type."""
        total_outstanding = (
            to_decimal(principal_outstanding) +
            to_decimal(interest_outstanding) +
            to_decimal(fees_outstanding)
        )

        if total_outstanding <= Decimal("0.01"):
            return ClosureEligibility(
                can_close=True,
                closure_type="normal",
                outstanding_amount=total_outstanding,
                settlement_amount=None,
                reason="Loan fully paid"
            )

        if dpd > 90 or is_npa:
            # Eligible for settlement or write-off
            settlement_discount = Decimal("0.20") if dpd > 180 else Decimal("0.10")
            settlement_amount = (total_outstanding * (1 - settlement_discount)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            if dpd > 365:
                return ClosureEligibility(
                    can_close=True,
                    closure_type="writeoff",
                    outstanding_amount=total_outstanding,
                    settlement_amount=settlement_amount,
                    reason="Eligible for write-off (DPD > 365)"
                )

            return ClosureEligibility(
                can_close=True,
                closure_type="settlement",
                outstanding_amount=total_outstanding,
                settlement_amount=settlement_amount,
                reason="Eligible for settlement"
            )

        return ClosureEligibility(
            can_close=False,
            closure_type="none",
            outstanding_amount=total_outstanding,
            settlement_amount=None,
            reason="Outstanding amount must be paid"
        )


class WriteOffService:
    """Service for write-off operations."""

    @staticmethod
    def calculate_write_off_summary(
        principal_written_off: Decimal,
        interest_written_off: Decimal,
        fees_written_off: Decimal,
        recovered_amount: Decimal = Decimal("0")
    ) -> WriteOffSummary:
        """Calculate write-off summary with recovery tracking."""
        total = (
            to_decimal(principal_written_off) +
            to_decimal(interest_written_off) +
            to_decimal(fees_written_off)
        )
        recovered = to_decimal(recovered_amount)

        return WriteOffSummary(
            principal_written_off=to_decimal(principal_written_off),
            interest_written_off=to_decimal(interest_written_off),
            fees_written_off=to_decimal(fees_written_off),
            total_written_off=total,
            recovered_amount=recovered,
            net_loss=total - recovered
        )

    @staticmethod
    def record_recovery_allocation(
        total_written_off: Decimal,
        principal_written_off: Decimal,
        interest_written_off: Decimal,
        fees_written_off: Decimal,
        recovery_amount: Decimal
    ) -> Dict[str, Decimal]:
        """Allocate recovery amount proportionally to written-off components."""
        total = to_decimal(total_written_off)
        recovery = to_decimal(recovery_amount)

        if total == Decimal("0"):
            return {
                "principal_recovered": Decimal("0"),
                "interest_recovered": Decimal("0"),
                "fees_recovered": Decimal("0")
            }

        principal = to_decimal(principal_written_off)
        interest = to_decimal(interest_written_off)
        fees = to_decimal(fees_written_off)

        # Proportional allocation
        return {
            "principal_recovered": (recovery * principal / total).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ),
            "interest_recovered": (recovery * interest / total).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ),
            "fees_recovered": (recovery * fees / total).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        }
