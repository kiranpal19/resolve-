import uuid
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import CaseModel
from app.audit.ledger import append_audit_record
from app.policy.engine import compute_hash
from app.audit.models import AuditLogRecord
from app.auth.jwt import get_current_user, require_role
from app.core_banking.mock_client import get_banking_client

router = APIRouter(prefix="/api/agent", tags=["agent-console"])

class ResolveCaseRequest(BaseModel):
    action: str  # "APPROVE_OVERRULE", "REJECT", "REQUEST_INFO"
    resolution_notes: str
    override_reason: Optional[str] = None

@router.get("/queue")
async def get_escalated_queue(
    current_user: Dict[str, Any] = Depends(require_role("agent")),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns queue of escalated cases requiring human servicing agent intervention.
    """
    stmt = select(CaseModel).where(CaseModel.status == "ESCALATED").order_by(CaseModel.created_at.desc())
    result = await db.execute(stmt)
    escalated_cases = result.scalars().all()
    return escalated_cases

@router.get("/case/{case_id}/context")
async def get_full_context_packet(
    case_id: str,
    current_user: Dict[str, Any] = Depends(require_role("agent")),
    db: AsyncSession = Depends(get_db)
):
    """
    Fetches complete context packet for an escalated case:
    - Customer details & account standing
    - AI Intent & extracted entities
    - Policy Engine matched rule & evaluation details
    - Cryptographic Audit Log history
    """
    stmt_case = select(CaseModel).where(CaseModel.case_id == case_id)
    res_case = await db.execute(stmt_case)
    case_rec = res_case.scalar_one_or_none()

    if not case_rec:
        raise HTTPException(status_code=404, detail="Case not found")

    # Fetch audit records
    stmt_audit = select(AuditLogRecord).where(AuditLogRecord.case_id == case_id).order_by(AuditLogRecord.seq.asc())
    res_audit = await db.execute(stmt_audit)
    audit_records = res_audit.scalars().all()

    # Fetch banking details
    banking = get_banking_client()
    acc_info = banking.get_account_info(case_rec.account_id)

    return {
        "case": case_rec,
        "account_info": acc_info,
        "context_snapshot": case_rec.context_snapshot,
        "policy_decision": {
            "policy_outcome": case_rec.policy_outcome,
            "rule_matched": case_rec.rule_matched,
            "reason": case_rec.escalation_reason,
            "priority_action_taken": case_rec.priority_action_taken
        },
        "audit_history": audit_records
    }

@router.post("/case/{case_id}/resolve")
async def resolve_case_human(
    case_id: str,
    req: ResolveCaseRequest,
    current_user: Dict[str, Any] = Depends(require_role("agent")),
    db: AsyncSession = Depends(get_db)
):
    """
    Human servicing agent resolves an escalated case.
    CRITICAL: Writing to audit ledger is mandatory before updating case status.
    """
    stmt = select(CaseModel).where(CaseModel.case_id == case_id)
    res = await db.execute(stmt)
    case_rec = res.scalar_one_or_none()

    if not case_rec:
        raise HTTPException(status_code=404, detail="Case not found")

    agent_id = current_user.get("sub", "agent_7701")
    agent_name = current_user.get("name", "Human Specialist")

    new_status = "RESOLVED" if req.action in ("APPROVE_OVERRULE", "REJECT") else "INFO_REQUESTED"
    outcome_label = "HUMAN_APPROVED" if req.action == "APPROVE_OVERRULE" else "HUMAN_REJECTED"

    # Execute core banking action if agent approved an overrule
    banking_res = None
    if req.action == "APPROVE_OVERRULE":
        client = get_banking_client()
        if case_rec.intent == "fee_reversal":
            banking_res = client.reverse_fee(case_rec.account_id, "fee_801", 35.00)
        elif case_rec.intent == "credit_limit_increase":
            banking_res = client.update_credit_limit(case_rec.account_id, 6500.00)
        elif case_rec.intent == "card_replacement":
            banking_res = client.reissue_card(case_rec.account_id, "card_9901", {"street": "123 Main St", "city": "NYC"})

    context_hash = compute_hash(case_rec.context_snapshot or {})

    # Append to Immutable Audit Ledger
    audit_rec = await append_audit_record(
        db=db,
        case_id=uuid.UUID(case_id),
        actor_type="human",
        actor_id=f"{agent_id} ({agent_name})",
        action=f"HUMAN_RESOLVE_{req.action}",
        rule_set=case_rec.intent,
        rule_version="2026.07.1",
        matched_rule_id="HUMAN_OVERRULE" if req.action == "APPROVE_OVERRULE" else "HUMAN_REJECT",
        outcome=outcome_label,
        reason=req.resolution_notes,
        context_snapshot_hash=context_hash,
        payload={
            "action": req.action,
            "notes": req.resolution_notes,
            "override_reason": req.override_reason,
            "banking_execution": banking_res
        }
    )

    # Update Case record in DB
    case_rec.status = new_status
    case_rec.assigned_agent_id = agent_id
    case_rec.resolution_notes = req.resolution_notes
    await db.commit()

    return {
        "status": "SUCCESS",
        "case_id": case_id,
        "new_case_status": new_status,
        "audit_seq": audit_rec.seq,
        "audit_hash": audit_rec.record_hash,
        "message": f"Case #{case_id[:8]} resolved by agent {agent_name} and recorded in audit ledger."
    }
