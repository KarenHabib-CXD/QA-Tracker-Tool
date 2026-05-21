from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ── Sprint ──────────────────────────────────────────────
class SprintCreate(BaseModel):
    name: str
    goal: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class SprintOut(SprintCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Ticket ──────────────────────────────────────────────
class TicketCreate(BaseModel):
    sprint_id: Optional[int] = None
    external_id: Optional[str] = None
    title: str
    description: str
    ticket_type: Optional[str] = "feature"


class TicketOut(TicketCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── TestCase ─────────────────────────────────────────────
class TestCaseCreate(BaseModel):
    ticket_id: int
    title: str
    preconditions: Optional[str] = None
    steps: str          # JSON string: ["Step 1", "Step 2", ...]
    expected_result: str
    priority: Optional[str] = "Medium"
    tags: Optional[str] = None


class TestCaseOut(TestCaseCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── TestExecution ────────────────────────────────────────
class ExecutionCreate(BaseModel):
    test_case_id: int
    status: str = Field(..., pattern="^(Pass|Fail|Blocked)$")
    platform: str = Field(..., pattern="^(iOS|Android|Web)$")
    environment: str = Field(..., pattern="^(Production|Staging|Integration)$")
    app_version: Optional[str] = None
    os_version: Optional[str] = None
    notes: Optional[str] = None
    bug_id: Optional[str] = None


class ExecutionOut(ExecutionCreate):
    id: int
    executed_at: datetime

    model_config = {"from_attributes": True}


# ── Reports ──────────────────────────────────────────────
class EnvironmentCell(BaseModel):
    status: Optional[str] = None     # Pass / Fail / Blocked / —


class EnvironmentMatrixRow(BaseModel):
    test_case_id: int
    test_case_title: str
    ticket_ref: str
    matrix: dict  # key: "iOS-Production" etc., value: latest status


class TicketReport(BaseModel):
    ticket_id: int
    external_id: Optional[str]
    title: str
    total_cases: int
    total_executions: int
    passed: int
    failed: int
    blocked: int
    coverage_pct: float
    environments_tested: List[str]
    platforms_tested: List[str]


class SprintReport(BaseModel):
    sprint_name: str
    total_tickets: int
    total_test_cases: int
    total_executions: int
    passed: int
    failed: int
    blocked: int
    pass_rate: float
    bug_count: int
    ticket_reports: List[TicketReport]
