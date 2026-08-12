import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, CheckConstraint, UniqueConstraint, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Cross-DB compatible JSON column (PostgreSQL JSONB / SQLite JSON)
JSON_TYPE = JSON().with_variant(JSONB, "postgresql")

class AuditLogRecord(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    seq = Column(Integer, nullable=False, unique=True)
    case_id = Column(String, nullable=False)
    actor_type = Column(String, nullable=False)
    actor_id = Column(String, nullable=False)
    action = Column(String, nullable=False)
    rule_set = Column(String, nullable=True)
    rule_version = Column(String, nullable=True)
    matched_rule_id = Column(String, nullable=True)
    outcome = Column(String, nullable=True)
    reason = Column(Text, nullable=True)
    context_snapshot_hash = Column(String, nullable=False)
    payload = Column(JSON_TYPE, nullable=False)
    prev_hash = Column(String(64), nullable=False)
    record_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint("actor_type IN ('ai', 'human', 'system')", name="chk_actor_type"),
        UniqueConstraint("seq", name="uq_audit_seq")
    )
