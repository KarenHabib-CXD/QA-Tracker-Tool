import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from backend.database import Base


class Sprint(Base):
    __tablename__ = "sprints"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    goal = Column(Text, nullable=True)
    start_date = Column(DateTime, default=datetime.datetime.utcnow)
    end_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    tickets = relationship("Ticket", back_populates="sprint")


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    sprint_id = Column(Integer, ForeignKey("sprints.id"), nullable=True)
    external_id = Column(String, nullable=True)   # e.g. JIRA-123
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    ticket_type = Column(String, default="feature")  # feature / bug / improvement
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    sprint = relationship("Sprint", back_populates="tickets")
    test_cases = relationship("TestCase", back_populates="ticket", cascade="all, delete-orphan")


class TestCase(Base):
    __tablename__ = "test_cases"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    title = Column(String, nullable=False)
    preconditions = Column(Text, nullable=True)
    steps = Column(Text, nullable=False)        # stored as JSON string
    expected_result = Column(Text, nullable=False)
    priority = Column(String, default="Medium") # Critical / High / Medium / Low
    tags = Column(String, nullable=True)        # comma-separated: smoke, regression, etc.
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    ticket = relationship("Ticket", back_populates="test_cases")
    executions = relationship("TestExecution", back_populates="test_case", cascade="all, delete-orphan")


class TestExecution(Base):
    __tablename__ = "executions"

    id = Column(Integer, primary_key=True, index=True)
    test_case_id = Column(Integer, ForeignKey("test_cases.id"), nullable=False)
    status = Column(String, nullable=False)         # Pass / Fail / Blocked
    platform = Column(String, nullable=False)       # iOS / Android / Web
    environment = Column(String, nullable=False)    # Production / Staging / Integration
    app_version = Column(String, nullable=True)
    os_version = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    bug_id = Column(String, nullable=True)          # linked bug reference
    executed_at = Column(DateTime, default=datetime.datetime.utcnow)

    test_case = relationship("TestCase", back_populates="executions")
