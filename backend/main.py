from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import io

from backend.database import engine, Base, get_db
import backend.models as models
import backend.schemas as schemas
from backend.services.ai_generator import generate_test_cases
from backend.services.pdf_report import generate_sprint_pdf
from backend.services.jira_service import (
    verify_jira_user, fetch_sprints, fetch_tickets_for_sprint, fetch_single_ticket
)

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="QA Sprint Tracker",
    description="Track tickets, test cases, executions and generate sprint reports.",
    version="1.0.0",
)


# ══════════════════════════════════════════════════════════════════════════════
# JIRA INTEGRATION
# ══════════════════════════════════════════════════════════════════════════════

def _jira_creds(
    x_jira_email: str = Header(..., alias="X-Jira-Email"),
    x_jira_token: str = Header(..., alias="X-Jira-Token"),
):
    """Extract Jira credentials from request headers."""
    return x_jira_email, x_jira_token


@app.post("/jira/verify", tags=["Jira"])
def jira_verify(creds=Depends(_jira_creds)):
    """Verify Jira credentials and return user profile."""
    email, token = creds
    result = verify_jira_user(email, token)
    if not result["ok"]:
        raise HTTPException(401, detail={
            "error": result.get("error", "Invalid credentials"),
            "hint": (
                "Make sure the email matches your Atlassian account at "
                "https://id.atlassian.com — it may differ from your work email. "
                f"You used: {email}"
            )
        })
    return result


@app.get("/jira/sprints", tags=["Jira"])
def jira_sprints(state: str = "active,future,closed", creds=Depends(_jira_creds)):
    """Fetch all sprints from the Jira board."""
    email, token = creds
    sprints = fetch_sprints(email, token, state)
    return sprints


@app.get("/jira/sprints/{jira_sprint_id}/tickets", tags=["Jira"])
def jira_tickets(jira_sprint_id: int, creds=Depends(_jira_creds)):
    """Fetch all tickets for a specific sprint."""
    email, token = creds
    tickets = fetch_tickets_for_sprint(email, token, jira_sprint_id)
    return tickets


@app.get("/jira/tickets/{ticket_key}", tags=["Jira"])
def jira_single_ticket(ticket_key: str, creds=Depends(_jira_creds)):
    """Fetch a single ticket by key e.g. APD-123."""
    email, token = creds
    ticket = fetch_single_ticket(email, token, ticket_key)
    if "error" in ticket:
        raise HTTPException(404, ticket["error"])
    return ticket


# ══════════════════════════════════════════════════════════════════════════════
# SPRINTS (local — kept as fallback / offline mode)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/sprints/", response_model=schemas.SprintOut, tags=["Sprints"])
def create_sprint(data: schemas.SprintCreate, db: Session = Depends(get_db)):
    sprint = models.Sprint(**data.model_dump())
    db.add(sprint)
    db.commit()
    db.refresh(sprint)
    return sprint


@app.get("/sprints/", response_model=List[schemas.SprintOut], tags=["Sprints"])
def list_sprints(db: Session = Depends(get_db)):
    return db.query(models.Sprint).order_by(models.Sprint.created_at.desc()).all()


@app.get("/sprints/{sprint_id}", response_model=schemas.SprintOut, tags=["Sprints"])
def get_sprint(sprint_id: int, db: Session = Depends(get_db)):
    sprint = db.query(models.Sprint).filter(models.Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(404, "Sprint not found")
    return sprint


@app.delete("/sprints/{sprint_id}", tags=["Sprints"])
def delete_sprint(sprint_id: int, db: Session = Depends(get_db)):
    sprint = db.query(models.Sprint).filter(models.Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(404, "Sprint not found")
    db.delete(sprint)
    db.commit()
    return {"message": "Sprint deleted"}


# ══════════════════════════════════════════════════════════════════════════════
# TICKETS
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/tickets/", response_model=schemas.TicketOut, tags=["Tickets"])
def create_ticket(data: schemas.TicketCreate, db: Session = Depends(get_db)):
    ticket = models.Ticket(**data.model_dump())
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@app.get("/tickets/", response_model=List[schemas.TicketOut], tags=["Tickets"])
def list_tickets(sprint_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(models.Ticket)
    if sprint_id:
        q = q.filter(models.Ticket.sprint_id == sprint_id)
    return q.order_by(models.Ticket.created_at.desc()).all()


@app.get("/tickets/{ticket_id}", response_model=schemas.TicketOut, tags=["Tickets"])
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    t = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not t:
        raise HTTPException(404, "Ticket not found")
    return t


@app.delete("/tickets/{ticket_id}", tags=["Tickets"])
def delete_ticket(ticket_id: int, db: Session = Depends(get_db)):
    t = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not t:
        raise HTTPException(404, "Ticket not found")
    db.delete(t)
    db.commit()
    return {"message": "Ticket deleted"}


# ══════════════════════════════════════════════════════════════════════════════
# TEST CASES
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/test-cases/", response_model=schemas.TestCaseOut, tags=["Test Cases"])
def create_test_case(data: schemas.TestCaseCreate, db: Session = Depends(get_db)):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == data.ticket_id).first()
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    tc = models.TestCase(**data.model_dump())
    db.add(tc)
    db.commit()
    db.refresh(tc)
    return tc


@app.post("/tickets/{ticket_id}/generate-test-cases/",
          response_model=List[schemas.TestCaseOut], tags=["Test Cases"])
def ai_generate_test_cases(ticket_id: int, db: Session = Depends(get_db)):
    """Use AI (or smart mock) to auto-generate test cases for a ticket."""
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(404, "Ticket not found")

    generated = generate_test_cases(ticket.title, ticket.description, ticket.ticket_type)

    created = []
    for g in generated:
        tc = models.TestCase(
            ticket_id=ticket_id,
            title=g["title"],
            preconditions=g.get("preconditions"),
            steps=g["steps"],
            expected_result=g["expected_result"],
            priority=g.get("priority", "Medium"),
            tags=g.get("tags", ""),
        )
        db.add(tc)
        db.commit()
        db.refresh(tc)
        created.append(tc)

    return created


@app.get("/test-cases/", response_model=List[schemas.TestCaseOut], tags=["Test Cases"])
def list_test_cases(ticket_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(models.TestCase)
    if ticket_id:
        q = q.filter(models.TestCase.ticket_id == ticket_id)
    return q.order_by(models.TestCase.created_at.desc()).all()


@app.put("/test-cases/{tc_id}", response_model=schemas.TestCaseOut, tags=["Test Cases"])
def update_test_case(tc_id: int, data: schemas.TestCaseCreate, db: Session = Depends(get_db)):
    tc = db.query(models.TestCase).filter(models.TestCase.id == tc_id).first()
    if not tc:
        raise HTTPException(404, "Test case not found")
    for k, v in data.model_dump().items():
        setattr(tc, k, v)
    db.commit()
    db.refresh(tc)
    return tc


@app.delete("/test-cases/{tc_id}", tags=["Test Cases"])
def delete_test_case(tc_id: int, db: Session = Depends(get_db)):
    tc = db.query(models.TestCase).filter(models.TestCase.id == tc_id).first()
    if not tc:
        raise HTTPException(404, "Test case not found")
    db.delete(tc)
    db.commit()
    return {"message": "Test case deleted"}


# ══════════════════════════════════════════════════════════════════════════════
# EXECUTIONS
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/executions/", response_model=schemas.ExecutionOut, tags=["Executions"])
def log_execution(data: schemas.ExecutionCreate, db: Session = Depends(get_db)):
    tc = db.query(models.TestCase).filter(models.TestCase.id == data.test_case_id).first()
    if not tc:
        raise HTTPException(404, "Test case not found")
    exe = models.TestExecution(**data.model_dump())
    db.add(exe)
    db.commit()
    db.refresh(exe)
    return exe


@app.get("/executions/", response_model=List[schemas.ExecutionOut], tags=["Executions"])
def list_executions(test_case_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(models.TestExecution)
    if test_case_id:
        q = q.filter(models.TestExecution.test_case_id == test_case_id)
    return q.order_by(models.TestExecution.executed_at.desc()).all()


@app.delete("/executions/{exe_id}", tags=["Executions"])
def delete_execution(exe_id: int, db: Session = Depends(get_db)):
    exe = db.query(models.TestExecution).filter(models.TestExecution.id == exe_id).first()
    if not exe:
        raise HTTPException(404, "Execution not found")
    db.delete(exe)
    db.commit()
    return {"message": "Execution deleted"}


# ══════════════════════════════════════════════════════════════════════════════
# ENVIRONMENT MATRIX
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/matrix/{ticket_id}", tags=["Reports"])
def environment_matrix(ticket_id: int, db: Session = Depends(get_db)):
    """
    Returns an environment matrix for all test cases of a ticket.
    Columns: platform-environment combos (e.g. iOS-Production).
    Each cell shows the latest execution status.
    """
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(404, "Ticket not found")

    test_cases = db.query(models.TestCase).filter(
        models.TestCase.ticket_id == ticket_id
    ).all()

    rows = []
    all_columns = set()

    for tc in test_cases:
        executions = db.query(models.TestExecution).filter(
            models.TestExecution.test_case_id == tc.id
        ).order_by(models.TestExecution.executed_at.desc()).all()

        cell_map = {}
        for exe in executions:
            key = f"{exe.platform} / {exe.environment}"
            all_columns.add(key)
            if key not in cell_map:          # keep latest only
                cell_map[key] = exe.status

        rows.append({
            "test_case_id": tc.id,
            "test_case_title": tc.title,
            "priority": tc.priority,
            "matrix": cell_map,
        })

    return {
        "ticket_id": ticket_id,
        "ticket_title": ticket.title,
        "columns": sorted(all_columns),
        "rows": rows,
    }


# ══════════════════════════════════════════════════════════════════════════════
# REPORTS
# ══════════════════════════════════════════════════════════════════════════════

def _build_sprint_report(sprint_id: int, db: Session) -> schemas.SprintReport:
    sprint = db.query(models.Sprint).filter(models.Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(404, "Sprint not found")

    tickets = db.query(models.Ticket).filter(models.Ticket.sprint_id == sprint_id).all()

    total_cases = total_executions = passed = failed = blocked = bug_count = 0
    ticket_reports = []

    for ticket in tickets:
        tcs = db.query(models.TestCase).filter(models.TestCase.ticket_id == ticket.id).all()
        tc_ids = [tc.id for tc in tcs]

        exes = db.query(models.TestExecution).filter(
            models.TestExecution.test_case_id.in_(tc_ids)
        ).all() if tc_ids else []

        t_passed  = sum(1 for e in exes if e.status == "Pass")
        t_failed  = sum(1 for e in exes if e.status == "Fail")
        t_blocked = sum(1 for e in exes if e.status == "Blocked")
        t_bugs    = sum(1 for e in exes if e.bug_id)

        envs      = list({e.environment for e in exes})
        platforms = list({e.platform for e in exes})

        total_cases      += len(tcs)
        total_executions += len(exes)
        passed   += t_passed
        failed   += t_failed
        blocked  += t_blocked
        bug_count += t_bugs

        executed_cases = len({e.test_case_id for e in exes})
        coverage = (executed_cases / len(tcs) * 100) if tcs else 0

        ticket_reports.append(schemas.TicketReport(
            ticket_id=ticket.id,
            external_id=ticket.external_id,
            title=ticket.title,
            total_cases=len(tcs),
            total_executions=len(exes),
            passed=t_passed,
            failed=t_failed,
            blocked=t_blocked,
            coverage_pct=coverage,
            environments_tested=envs,
            platforms_tested=platforms,
        ))

    pass_rate = (passed / total_executions * 100) if total_executions else 0

    return schemas.SprintReport(
        sprint_name=sprint.name,
        total_tickets=len(tickets),
        total_test_cases=total_cases,
        total_executions=total_executions,
        passed=passed,
        failed=failed,
        blocked=blocked,
        pass_rate=pass_rate,
        bug_count=bug_count,
        ticket_reports=ticket_reports,
    )


@app.get("/reports/sprint/{sprint_id}", response_model=schemas.SprintReport, tags=["Reports"])
def sprint_report_json(sprint_id: int, db: Session = Depends(get_db)):
    return _build_sprint_report(sprint_id, db)


@app.get("/reports/sprint/{sprint_id}/pdf", tags=["Reports"])
def sprint_report_pdf(sprint_id: int, db: Session = Depends(get_db)):
    report = _build_sprint_report(sprint_id, db)
    pdf_bytes = generate_sprint_pdf(report)
    filename = f"QA_Sprint_Report_{report.sprint_name.replace(' ', '_')}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
