"""
LAP (Loan Against Property) approval workflow service.

5-level approval workflow:
draft → branch_data_entry → branch_manager_review → regional_credit_review
  → central_credit_review → sanctioning_authority → approved → disbursement

Review stages can → referred_back or → rejected
referred_back → branch_data_entry (re-entry loop)
Final stages: disbursement, rejected
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.loan_application import LoanApplication
from app.models.workflow import WorkflowDefinition, WorkflowInstance
from app.services import workflow

LAP_WORKFLOW_CODE = "lap_approval"

LAP_STAGES = [
    "draft",
    "branch_data_entry",
    "branch_manager_review",
    "regional_credit_review",
    "central_credit_review",
    "sanctioning_authority",
    "approved",
    "disbursement",
    "referred_back",
    "rejected",
]

LAP_TRANSITIONS = {
    "draft": ["branch_data_entry"],
    "branch_data_entry": ["branch_manager_review"],
    "branch_manager_review": ["regional_credit_review", "referred_back", "rejected"],
    "regional_credit_review": ["central_credit_review", "referred_back", "rejected"],
    "central_credit_review": ["sanctioning_authority", "referred_back", "rejected"],
    "sanctioning_authority": ["approved", "referred_back", "rejected"],
    "approved": ["disbursement"],
    "referred_back": ["branch_data_entry"],
    "disbursement": [],
    "rejected": [],
}

LAP_FINAL_STAGES = ["disbursement", "rejected"]

LAP_STAGE_REQUIREMENTS = {
    "branch_data_entry": {
        "required_documents": ["kyc_docs", "income_proof", "property_docs"],
        "description": "Branch data entry: KYC, income proof, property documents",
    },
    "branch_manager_review": {
        "required_documents": ["collateral_photos", "site_visit_report"],
        "description": "Branch manager review: collateral photos, site visit report",
    },
    "regional_credit_review": {
        "required_documents": ["valuation_report", "legal_opinion"],
        "description": "Regional credit review: valuation report, legal opinion",
    },
    "central_credit_review": {
        "required_documents": ["all_docs_verified", "credit_assessment"],
        "description": "Central credit review: all documents verified, credit assessment",
    },
    "sanctioning_authority": {
        "required_documents": ["all_prior_approvals"],
        "description": "Sanctioning authority: all prior level approvals",
    },
}

# Stage-to-LoanApplication.status mapping
STAGE_STATUS_MAP = {
    "draft": "draft",
    "branch_data_entry": "data_entry",
    "branch_manager_review": "under_review",
    "regional_credit_review": "under_review",
    "central_credit_review": "under_review",
    "sanctioning_authority": "under_review",
    "approved": "approved",
    "disbursement": "disbursed",
    "rejected": "rejected",
    "referred_back": "referred_back",
}


def seed_lap_workflow_definition(db: Session) -> WorkflowDefinition:
    """
    Idempotent creation of the LAP workflow definition.
    Returns existing definition if already present.
    """
    existing = db.query(WorkflowDefinition).filter(
        WorkflowDefinition.code == LAP_WORKFLOW_CODE
    ).first()

    if existing:
        return existing

    return workflow.create_workflow_definition(
        code=LAP_WORKFLOW_CODE,
        name="LAP 5-Level Approval Workflow",
        entity_type="loan_application",
        stages=LAP_STAGES,
        transitions=LAP_TRANSITIONS,
        initial_stage="draft",
        final_stages=LAP_FINAL_STAGES,
        stage_requirements=LAP_STAGE_REQUIREMENTS,
        db=db,
    )


def start_lap_workflow(
    application_id: int,
    started_by: str,
    priority: str = "medium",
    sla_hours: int | None = None,
    db: Session = None,
) -> WorkflowInstance:
    """
    Start a LAP approval workflow for a loan application.

    Seeds the workflow definition if it doesn't exist yet,
    then starts a workflow instance and updates LoanApplication.status.
    """
    application = db.query(LoanApplication).filter(
        LoanApplication.id == application_id
    ).first()
    if not application:
        raise ValueError(f"Loan application {application_id} not found")

    # Ensure definition exists
    seed_lap_workflow_definition(db)

    instance = workflow.start_workflow(
        workflow_code=LAP_WORKFLOW_CODE,
        entity_type="loan_application",
        entity_id=application_id,
        started_by=started_by,
        priority=priority,
        sla_hours=sla_hours,
        db=db,
    )

    # Sync application status
    application.status = STAGE_STATUS_MAP.get(instance.current_stage, application.status)
    db.commit()
    db.refresh(instance)

    return instance


def transition_lap_workflow(
    application_id: int,
    to_stage: str,
    transitioned_by: str,
    action: str,
    comments: str | None = None,
    db: Session = None,
) -> WorkflowInstance:
    """
    Transition the LAP workflow for an application.

    Validates transition, updates workflow instance, and syncs LoanApplication.status.
    """
    application = db.query(LoanApplication).filter(
        LoanApplication.id == application_id
    ).first()
    if not application:
        raise ValueError(f"Loan application {application_id} not found")

    # Find active workflow instance
    instance = db.query(WorkflowInstance).filter(
        and_(
            WorkflowInstance.entity_type == "loan_application",
            WorkflowInstance.entity_id == application_id,
            WorkflowInstance.is_active == True,
        )
    ).first()

    if not instance:
        raise ValueError(
            f"No active workflow found for application {application_id}"
        )

    instance = workflow.transition_workflow(
        instance_id=instance.id,
        to_stage=to_stage,
        transitioned_by=transitioned_by,
        action=action,
        comments=comments,
        db=db,
    )

    # Sync application status
    new_status = STAGE_STATUS_MAP.get(to_stage)
    if new_status:
        application.status = new_status

    # Set decision_at on terminal stages
    if to_stage in ("approved", "rejected", "disbursement"):
        if not application.decision_at:
            application.decision_at = datetime.utcnow()

    db.commit()
    db.refresh(instance)

    return instance


def assign_lap_workflow(
    application_id: int,
    assigned_to: str,
    assigned_role: str | None = None,
    db: Session = None,
) -> WorkflowInstance:
    """Assign the LAP workflow to a user or role."""
    instance = db.query(WorkflowInstance).filter(
        and_(
            WorkflowInstance.entity_type == "loan_application",
            WorkflowInstance.entity_id == application_id,
            WorkflowInstance.is_active == True,
        )
    ).first()

    if not instance:
        raise ValueError(
            f"No active workflow found for application {application_id}"
        )

    return workflow.assign_workflow(
        instance_id=instance.id,
        assigned_to=assigned_to,
        assigned_role=assigned_role,
        db=db,
    )


def get_lap_workflow_status(
    application_id: int, db: Session
) -> dict | None:
    """Get the current LAP workflow status for an application."""
    return workflow.get_workflow_status(
        entity_type="loan_application",
        entity_id=application_id,
        db=db,
    )
