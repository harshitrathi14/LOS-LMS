"""
Workflow service.

Handles:
- Workflow instance creation
- Stage transitions
- Task management
- SLA tracking
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.workflow import (
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowTransition,
    WorkflowTask
)


def create_workflow_definition(
    code: str,
    name: str,
    entity_type: str,
    stages: list[str],
    transitions: dict[str, list[str]],
    initial_stage: str,
    final_stages: list[str],
    stage_requirements: dict | None = None,
    db: Session = None
) -> WorkflowDefinition:
    """
    Create a workflow definition.

    Args:
        code: Unique code
        name: Display name
        entity_type: Entity type this workflow applies to
        stages: List of stage names
        transitions: Dict mapping stage to allowed next stages
        initial_stage: Starting stage
        final_stages: Terminal stages
        stage_requirements: Optional requirements per stage
        db: Database session

    Returns:
        Created WorkflowDefinition
    """
    definition = WorkflowDefinition(
        code=code,
        name=name,
        entity_type=entity_type,
        stages_json=json.dumps(stages),
        transitions_json=json.dumps(transitions),
        initial_stage=initial_stage,
        final_stages_json=json.dumps(final_stages),
        stage_requirements_json=json.dumps(stage_requirements) if stage_requirements else None,
        is_active=True
    )

    db.add(definition)
    db.commit()
    db.refresh(definition)

    return definition


def start_workflow(
    workflow_code: str,
    entity_type: str,
    entity_id: int,
    started_by: str,
    priority: str = "medium",
    context_data: dict | None = None,
    sla_hours: int | None = None,
    db: Session = None
) -> WorkflowInstance:
    """
    Start a new workflow instance.

    Args:
        workflow_code: Workflow definition code
        entity_type: Entity type
        entity_id: Entity ID
        started_by: User who started the workflow
        priority: Priority level
        context_data: Additional context
        sla_hours: SLA in hours
        db: Database session

    Returns:
        Created WorkflowInstance
    """
    definition = db.query(WorkflowDefinition).filter(
        and_(
            WorkflowDefinition.code == workflow_code,
            WorkflowDefinition.is_active == True
        )
    ).first()

    if not definition:
        raise ValueError(f"Workflow definition '{workflow_code}' not found")

    if definition.entity_type != entity_type:
        raise ValueError(
            f"Workflow '{workflow_code}' is for '{definition.entity_type}', "
            f"not '{entity_type}'"
        )

    # Check for existing active workflow
    existing = db.query(WorkflowInstance).filter(
        and_(
            WorkflowInstance.entity_type == entity_type,
            WorkflowInstance.entity_id == entity_id,
            WorkflowInstance.is_active == True
        )
    ).first()

    if existing:
        raise ValueError(
            f"Active workflow already exists for {entity_type} {entity_id}"
        )

    sla_due = None
    if sla_hours:
        sla_due = datetime.utcnow() + timedelta(hours=sla_hours)

    instance = WorkflowInstance(
        workflow_id=definition.id,
        entity_type=entity_type,
        entity_id=entity_id,
        current_stage=definition.initial_stage,
        priority=priority,
        context_data=json.dumps(context_data) if context_data else None,
        sla_due_date=sla_due,
        is_active=True
    )

    db.add(instance)
    db.flush()

    # Create initial transition record
    transition = WorkflowTransition(
        instance_id=instance.id,
        from_stage="",
        to_stage=definition.initial_stage,
        transitioned_by=started_by,
        action="start",
        comments="Workflow started"
    )

    db.add(transition)
    db.commit()
    db.refresh(instance)

    return instance


def transition_workflow(
    instance_id: int,
    to_stage: str,
    transitioned_by: str,
    action: str,
    comments: str | None = None,
    db: Session = None
) -> WorkflowInstance:
    """
    Transition a workflow to a new stage.

    Args:
        instance_id: Workflow instance ID
        to_stage: Target stage
        transitioned_by: User making the transition
        action: Action being taken (approve, reject, refer, etc.)
        comments: Optional comments
        db: Database session

    Returns:
        Updated WorkflowInstance
    """
    instance = db.query(WorkflowInstance).filter(
        WorkflowInstance.id == instance_id
    ).first()

    if not instance:
        raise ValueError(f"Workflow instance {instance_id} not found")

    if not instance.is_active:
        raise ValueError(f"Workflow instance {instance_id} is not active")

    definition = instance.definition
    transitions = json.loads(definition.transitions_json)
    final_stages = json.loads(definition.final_stages_json)

    # Validate transition
    allowed = transitions.get(instance.current_stage, [])
    if to_stage not in allowed:
        raise ValueError(
            f"Transition from '{instance.current_stage}' to '{to_stage}' "
            f"is not allowed. Allowed: {allowed}"
        )

    # Calculate time in previous stage
    last_transition = db.query(WorkflowTransition).filter(
        WorkflowTransition.instance_id == instance_id
    ).order_by(WorkflowTransition.transition_date.desc()).first()

    time_in_stage = None
    if last_transition:
        delta = datetime.utcnow() - last_transition.transition_date
        time_in_stage = int(delta.total_seconds() / 60)

    # Create transition record
    transition = WorkflowTransition(
        instance_id=instance_id,
        from_stage=instance.current_stage,
        to_stage=to_stage,
        transitioned_by=transitioned_by,
        action=action,
        comments=comments,
        time_in_stage_minutes=time_in_stage
    )

    db.add(transition)

    # Update instance
    instance.previous_stage = instance.current_stage
    instance.current_stage = to_stage

    # Check if workflow is complete
    if to_stage in final_stages:
        instance.is_active = False
        instance.completed_at = datetime.utcnow()

    # Clear assignment if transitioning
    instance.assigned_to = None
    instance.assigned_at = None

    db.commit()
    db.refresh(instance)

    return instance


def assign_workflow(
    instance_id: int,
    assigned_to: str | None = None,
    assigned_role: str | None = None,
    db: Session = None
) -> WorkflowInstance:
    """
    Assign a workflow instance to a user or role.

    Args:
        instance_id: Workflow instance ID
        assigned_to: User to assign to
        assigned_role: Role for pool assignment
        db: Database session

    Returns:
        Updated WorkflowInstance
    """
    instance = db.query(WorkflowInstance).filter(
        WorkflowInstance.id == instance_id
    ).first()

    if not instance:
        raise ValueError(f"Workflow instance {instance_id} not found")

    instance.assigned_to = assigned_to
    instance.assigned_role = assigned_role
    instance.assigned_at = datetime.utcnow()

    db.commit()
    db.refresh(instance)

    return instance


def get_workflow_status(
    entity_type: str,
    entity_id: int,
    db: Session
) -> dict | None:
    """
    Get the current workflow status for an entity.

    Args:
        entity_type: Entity type
        entity_id: Entity ID
        db: Database session

    Returns:
        Status dictionary or None
    """
    instance = db.query(WorkflowInstance).filter(
        and_(
            WorkflowInstance.entity_type == entity_type,
            WorkflowInstance.entity_id == entity_id
        )
    ).order_by(WorkflowInstance.created_at.desc()).first()

    if not instance:
        return None

    definition = instance.definition
    stages = json.loads(definition.stages_json)
    final_stages = json.loads(definition.final_stages_json)

    transitions = db.query(WorkflowTransition).filter(
        WorkflowTransition.instance_id == instance.id
    ).order_by(WorkflowTransition.transition_date).all()

    return {
        "instance_id": instance.id,
        "workflow_code": definition.code,
        "current_stage": instance.current_stage,
        "is_active": instance.is_active,
        "is_final": instance.current_stage in final_stages,
        "assigned_to": instance.assigned_to,
        "assigned_role": instance.assigned_role,
        "priority": instance.priority,
        "sla_due_date": instance.sla_due_date.isoformat() if instance.sla_due_date else None,
        "is_sla_breached": instance.is_sla_breached,
        "stages": stages,
        "history": [
            {
                "from_stage": t.from_stage,
                "to_stage": t.to_stage,
                "action": t.action,
                "transitioned_by": t.transitioned_by,
                "timestamp": t.transition_date.isoformat(),
                "comments": t.comments
            }
            for t in transitions
        ]
    }


def create_task(
    instance_id: int,
    task_type: str,
    task_name: str,
    description: str | None = None,
    assigned_to: str | None = None,
    assigned_role: str | None = None,
    due_date: datetime | None = None,
    db: Session = None
) -> WorkflowTask:
    """
    Create a task for a workflow instance.

    Args:
        instance_id: Workflow instance ID
        task_type: Task type
        task_name: Task name
        description: Task description
        assigned_to: User assignment
        assigned_role: Role assignment
        due_date: Due date
        db: Database session

    Returns:
        Created WorkflowTask
    """
    task = WorkflowTask(
        instance_id=instance_id,
        task_type=task_type,
        task_name=task_name,
        description=description,
        assigned_to=assigned_to,
        assigned_role=assigned_role,
        due_date=due_date,
        status="pending"
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    return task


def complete_task(
    task_id: int,
    completed_by: str,
    result: dict | None = None,
    db: Session = None
) -> WorkflowTask:
    """
    Mark a task as completed.

    Args:
        task_id: Task ID
        completed_by: User completing the task
        result: Task result data
        db: Database session

    Returns:
        Updated WorkflowTask
    """
    task = db.query(WorkflowTask).filter(
        WorkflowTask.id == task_id
    ).first()

    if not task:
        raise ValueError(f"Task {task_id} not found")

    task.status = "completed"
    task.completed_at = datetime.utcnow()
    task.completed_by = completed_by
    task.result = json.dumps(result) if result else None

    db.commit()
    db.refresh(task)

    return task


def get_pending_tasks(
    assigned_to: str | None = None,
    assigned_role: str | None = None,
    db: Session = None
) -> list[WorkflowTask]:
    """
    Get pending tasks for a user or role.

    Args:
        assigned_to: Filter by assigned user
        assigned_role: Filter by assigned role
        db: Database session

    Returns:
        List of pending tasks
    """
    query = db.query(WorkflowTask).filter(
        WorkflowTask.status == "pending"
    )

    if assigned_to:
        query = query.filter(WorkflowTask.assigned_to == assigned_to)

    if assigned_role:
        query = query.filter(WorkflowTask.assigned_role == assigned_role)

    return query.order_by(WorkflowTask.due_date, WorkflowTask.created_at).all()


def get_my_workflows(
    user: str,
    role: str | None = None,
    db: Session = None
) -> list[WorkflowInstance]:
    """
    Get active workflow instances assigned to a user or their role.

    Args:
        user: User ID/email
        role: User's role
        db: Database session

    Returns:
        List of assigned workflow instances
    """
    query = db.query(WorkflowInstance).filter(
        WorkflowInstance.is_active == True
    )

    if role:
        query = query.filter(
            (WorkflowInstance.assigned_to == user) |
            (WorkflowInstance.assigned_role == role)
        )
    else:
        query = query.filter(WorkflowInstance.assigned_to == user)

    return query.order_by(
        WorkflowInstance.priority.desc(),
        WorkflowInstance.sla_due_date
    ).all()


def check_sla_breaches(db: Session) -> int:
    """
    Check and mark SLA breached workflows.

    Args:
        db: Database session

    Returns:
        Count of newly breached workflows
    """
    now = datetime.utcnow()

    breached = db.query(WorkflowInstance).filter(
        and_(
            WorkflowInstance.is_active == True,
            WorkflowInstance.is_sla_breached == False,
            WorkflowInstance.sla_due_date < now
        )
    ).all()

    for instance in breached:
        instance.is_sla_breached = True

    db.commit()

    return len(breached)
