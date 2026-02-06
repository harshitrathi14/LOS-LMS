from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


# --- CollectionCase ---

class CollectionCaseBase(BaseModel):
    loan_account_id: int
    status: str = "open"
    priority: str = "medium"
    assigned_to: str | None = None
    assigned_queue: str | None = None
    notes: str | None = None


class CollectionCaseCreate(BaseModel):
    loan_account_id: int
    assigned_to: str | None = None
    assigned_queue: str | None = None
    priority: str = "medium"
    notes: str | None = None


class CollectionCaseUpdate(BaseModel):
    status: str | None = None
    priority: str | None = None
    assigned_to: str | None = None
    assigned_queue: str | None = None
    resolution_type: str | None = None
    notes: str | None = None


class CollectionCaseRead(BaseModel):
    id: int
    loan_account_id: int
    case_number: str
    status: str
    priority: str
    assigned_to: str | None = None
    assigned_queue: str | None = None
    opened_date: date
    last_action_date: date | None = None
    next_action_date: date | None = None
    resolution_date: date | None = None
    resolution_type: str | None = None
    dpd_at_open: int
    overdue_at_open: float
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# --- CollectionAction ---

class CollectionActionBase(BaseModel):
    action_type: str
    performed_by: str
    outcome: str | None = None
    outcome_details: str | None = None
    next_action_date: date | None = None
    next_action_type: str | None = None
    notes: str | None = None


class CollectionActionCreate(CollectionActionBase):
    pass


class CollectionActionRead(CollectionActionBase):
    id: int
    case_id: int
    action_date: datetime
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# --- PromiseToPay ---

class PromiseToPayBase(BaseModel):
    promise_date: date
    payment_due_date: date
    promised_amount: float


class PromiseToPayCreate(PromiseToPayBase):
    notes: str | None = None


class PromiseToPayUpdate(BaseModel):
    actual_payment_date: date | None = None
    actual_amount: float | None = None
    status: str | None = None
    notes: str | None = None


class PromiseToPayRead(BaseModel):
    id: int
    case_id: int
    promise_date: date
    payment_due_date: date
    promised_amount: float
    actual_payment_date: date | None = None
    actual_amount: float | None = None
    status: str
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# --- EscalationRule ---

class EscalationRuleBase(BaseModel):
    name: str
    trigger_dpd: int | None = None
    trigger_bucket: str | None = None
    trigger_amount: float | None = None
    action_type: str
    action_config: str | None = None
    priority: int = 100
    is_active: bool = True
    applies_to_product_id: int | None = None


class EscalationRuleCreate(EscalationRuleBase):
    pass


class EscalationRuleRead(EscalationRuleBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
