import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Float, Boolean, JSON
from sqlalchemy.dialects.postgresql import JSONB
from app.audit.models import Base, JSON_TYPE

class CaseModel(Base):
    __tablename__ = "servicing_cases"

    case_id = Column(String, primary_key=True)
    account_id = Column(String, nullable=False)
    customer_id = Column(String, nullable=False)
    customer_name = Column(String, nullable=False, default="Valued Cardmember")
    intent = Column(String, nullable=False)
    status = Column(String, nullable=False, default="IN_PROGRESS")  # IN_PROGRESS, APPROVED, DENIED, ESCALATED, RESOLVED
    escalation_reason = Column(Text, nullable=True)
    priority_action_taken = Column(String, nullable=True)
    context_snapshot = Column(JSON_TYPE, nullable=True)
    policy_outcome = Column(String, nullable=True)
    rule_matched = Column(String, nullable=True)
    assigned_agent_id = Column(String, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
