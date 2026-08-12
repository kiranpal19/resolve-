from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.audit.verifier import verify_chain
from app.audit.models import AuditLogRecord
from app.auth.jwt import get_current_user

router = APIRouter(prefix="/audit", tags=["audit"])

@router.get("/verify")
async def verify_audit_chain_endpoint(
    case_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Public / Internal verification endpoint.
    Cryptographically verifies that the append-only audit log chain is 100% intact,
    re-computing hashes from genesis to latest sequence number.
    """
    result = await verify_chain(db, case_id=case_id)
    return result

@router.get("/case/{case_id}")
async def get_case_audit_trail(
    case_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Customer-facing transparent audit trail.
    Returns audit records for a given case.
    """
    stmt = select(AuditLogRecord).where(AuditLogRecord.case_id == case_id).order_by(AuditLogRecord.seq.asc())
    result = await db.execute(stmt)
    records = result.scalars().all()

    audit_entries = []
    for r in records:
        entry = {
            "seq": r.seq,
            "case_id": str(r.case_id),
            "actor_type": r.actor_type,
            "action": r.action,
            "rule_set": r.rule_set,
            "rule_version": r.rule_version,
            "matched_rule_id": r.matched_rule_id,
            "outcome": r.outcome,
            "reason": r.reason,
            "context_snapshot_hash": r.context_snapshot_hash,
            "prev_hash": r.prev_hash,
            "record_hash": r.record_hash,
            "created_at": r.created_at.isoformat() if r.created_at else None
        }

        # Hide internal sensitive fields for customer role if needed, but preserve cryptographic proof
        if current_user.get("role") == "customer":
            entry["actor_id"] = "REDACTED_SYSTEM_ID" if r.actor_type != "customer" else r.actor_id
        else:
            entry["actor_id"] = r.actor_id

        audit_entries.append(entry)

    return {
        "case_id": case_id,
        "record_count": len(audit_entries),
        "audit_trail": audit_entries
    }
