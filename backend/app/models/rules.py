"""
Rules engine models.

RuleSet: Collection of rules for a product/decision type
DecisionRule: Individual decision rule with conditions and actions
"""

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RuleSet(Base):
    """
    A set of rules for credit decisioning.

    Examples:
    - Eligibility rules for a product
    - Credit score rules
    - Income verification rules
    """
    __tablename__ = "rule_sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)

    # Rule set type: eligibility, credit_decision, pricing, collection
    rule_type: Mapped[str] = mapped_column(String(30), index=True)

    # Optional product association
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("loan_products.id"),
        nullable=True
    )

    # Versioning
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Execution order (lower = executed first)
    priority: Mapped[int] = mapped_column(Integer, default=100)

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    rules: Mapped[list["DecisionRule"]] = relationship(
        "DecisionRule",
        back_populates="rule_set",
        cascade="all, delete-orphan",
        order_by="DecisionRule.rule_order"
    )
    product = relationship("LoanProduct")


class DecisionRule(Base):
    """
    Individual decision rule within a rule set.

    Supports:
    - Condition-based evaluation (JSON conditions)
    - Multiple action types (approve, reject, refer, score_adjustment)
    """
    __tablename__ = "decision_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_set_id: Mapped[int] = mapped_column(
        ForeignKey("rule_sets.id", ondelete="CASCADE"),
        index=True
    )

    # Rule identification
    rule_name: Mapped[str] = mapped_column(String(200))
    rule_code: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)

    # Execution order within rule set
    rule_order: Mapped[int] = mapped_column(Integer, default=1)

    # Condition (JSON format)
    # Example: {"field": "credit_score", "operator": ">=", "value": 700}
    # Complex: {"and": [{"field": "income", "operator": ">", "value": 50000}, {"field": "age", "operator": ">=", "value": 21}]}
    condition_json: Mapped[str] = mapped_column(Text)

    # Action type: approve, reject, refer, score_adjustment, set_field, skip_next
    action_type: Mapped[str] = mapped_column(String(30))

    # Action parameters (JSON)
    # For approve: {"auto_approve": true}
    # For reject: {"reason_code": "LOW_SCORE", "message": "Credit score below threshold"}
    # For score_adjustment: {"adjustment": -10, "reason": "High DTI ratio"}
    # For refer: {"refer_to": "underwriter", "priority": "high"}
    action_params: Mapped[str | None] = mapped_column(Text)

    # Should evaluation continue after this rule triggers?
    stop_on_match: Mapped[bool] = mapped_column(Boolean, default=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    rule_set: Mapped["RuleSet"] = relationship("RuleSet", back_populates="rules")


class RuleExecutionLog(Base):
    """
    Log of rule execution for audit and debugging.
    """
    __tablename__ = "rule_execution_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_set_id: Mapped[int] = mapped_column(
        ForeignKey("rule_sets.id"),
        index=True
    )
    rule_id: Mapped[int | None] = mapped_column(
        ForeignKey("decision_rules.id"),
        nullable=True
    )

    # What was evaluated
    entity_type: Mapped[str] = mapped_column(String(50))  # loan_application, borrower
    entity_id: Mapped[int] = mapped_column(Integer, index=True)

    # Execution details
    execution_time: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    input_data: Mapped[str | None] = mapped_column(Text)  # JSON of input values
    condition_result: Mapped[bool | None] = mapped_column(Boolean)
    action_taken: Mapped[str | None] = mapped_column(String(30))
    action_result: Mapped[str | None] = mapped_column(Text)  # JSON result

    # Overall decision if this is final
    final_decision: Mapped[str | None] = mapped_column(String(30))  # approved, rejected, referred
    decision_score: Mapped[int | None] = mapped_column(Integer)

    # Relationships
    rule_set = relationship("RuleSet")
    rule = relationship("DecisionRule")
