"""
Workflow models.

WorkflowDefinition: Template for approval workflows
WorkflowInstance: Active workflow instances
WorkflowTransition: Transition history
"""

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class WorkflowDefinition(Base):
    """
    Definition of an approval workflow.

    Defines the stages, transitions, and conditions for a workflow.
    """
    __tablename__ = "workflow_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)

    # What entity type this workflow applies to
    entity_type: Mapped[str] = mapped_column(String(50), index=True)  # loan_application, restructure, etc.

    # Workflow stages (JSON array)
    # Example: ["draft", "submitted", "under_review", "approved", "rejected"]
    stages_json: Mapped[str] = mapped_column(Text)

    # Allowed transitions (JSON)
    # Example: {"draft": ["submitted"], "submitted": ["under_review", "rejected"], ...}
    transitions_json: Mapped[str] = mapped_column(Text)

    # Stage requirements (JSON)
    # Example: {"under_review": {"required_documents": ["income_proof", "address_proof"]}}
    stage_requirements_json: Mapped[str | None] = mapped_column(Text)

    # Initial stage
    initial_stage: Mapped[str] = mapped_column(String(50))

    # Final stages (no further transitions)
    final_stages_json: Mapped[str] = mapped_column(Text)  # ["approved", "rejected", "cancelled"]

    # Versioning
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    instances: Mapped[list["WorkflowInstance"]] = relationship(
        "WorkflowInstance",
        back_populates="definition",
        cascade="all, delete-orphan"
    )


class WorkflowInstance(Base):
    """
    Active instance of a workflow.
    """
    __tablename__ = "workflow_instances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workflow_id: Mapped[int] = mapped_column(
        ForeignKey("workflow_definitions.id"),
        index=True
    )

    # What entity this workflow is for
    entity_type: Mapped[str] = mapped_column(String(50), index=True)
    entity_id: Mapped[int] = mapped_column(Integer, index=True)

    # Current state
    current_stage: Mapped[str] = mapped_column(String(50), index=True)
    previous_stage: Mapped[str | None] = mapped_column(String(50))

    # Assignment
    assigned_to: Mapped[str | None] = mapped_column(String(100))  # User ID/email
    assigned_role: Mapped[str | None] = mapped_column(String(50))  # Role for pool assignment
    assigned_at: Mapped[DateTime | None] = mapped_column(DateTime)

    # Priority: low, medium, high, urgent
    priority: Mapped[str] = mapped_column(String(20), default="medium")

    # SLA tracking
    sla_due_date: Mapped[DateTime | None] = mapped_column(DateTime)
    is_sla_breached: Mapped[bool] = mapped_column(Boolean, default=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime)

    # Additional data (JSON)
    context_data: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    definition: Mapped["WorkflowDefinition"] = relationship(
        "WorkflowDefinition",
        back_populates="instances"
    )
    transitions: Mapped[list["WorkflowTransition"]] = relationship(
        "WorkflowTransition",
        back_populates="instance",
        cascade="all, delete-orphan",
        order_by="WorkflowTransition.transition_date"
    )


class WorkflowTransition(Base):
    """
    Record of a workflow stage transition.
    """
    __tablename__ = "workflow_transitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instance_id: Mapped[int] = mapped_column(
        ForeignKey("workflow_instances.id", ondelete="CASCADE"),
        index=True
    )

    # Transition details
    from_stage: Mapped[str] = mapped_column(String(50))
    to_stage: Mapped[str] = mapped_column(String(50))

    # Who made the transition
    transitioned_by: Mapped[str] = mapped_column(String(100))  # User ID/email
    transition_date: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # Action that triggered transition
    action: Mapped[str] = mapped_column(String(50))  # approve, reject, refer, request_info

    # Comments and data
    comments: Mapped[str | None] = mapped_column(Text)
    attachments: Mapped[str | None] = mapped_column(Text)  # JSON list of document IDs

    # Time metrics
    time_in_stage_minutes: Mapped[int | None] = mapped_column(Integer)

    # Relationships
    instance: Mapped["WorkflowInstance"] = relationship(
        "WorkflowInstance",
        back_populates="transitions"
    )


class WorkflowTask(Base):
    """
    Task created during workflow execution.
    """
    __tablename__ = "workflow_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instance_id: Mapped[int] = mapped_column(
        ForeignKey("workflow_instances.id", ondelete="CASCADE"),
        index=True
    )

    # Task details
    task_type: Mapped[str] = mapped_column(String(50))  # document_upload, verification, approval
    task_name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)

    # Assignment
    assigned_to: Mapped[str | None] = mapped_column(String(100))
    assigned_role: Mapped[str | None] = mapped_column(String(50))

    # Due date
    due_date: Mapped[DateTime | None] = mapped_column(DateTime)

    # Status: pending, in_progress, completed, cancelled
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime)
    completed_by: Mapped[str | None] = mapped_column(String(100))

    # Result
    result: Mapped[str | None] = mapped_column(Text)  # JSON result data

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    instance = relationship("WorkflowInstance")
