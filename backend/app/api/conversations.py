import uuid
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import CaseModel
from app.auth.jwt import get_current_user
from app.orchestration.state import AgentState
from app.orchestration.workflow_router import run_workflow

router = APIRouter(prefix="/api/conversation", tags=["conversation"])

class ChatMessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    account_id: Optional[str] = None

@router.post("/send")
async def send_chat_message(
    req: ChatMessageRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    account_id = req.account_id or current_user.get("account_id", "acc_good_customer")
    actor_id = current_user.get("sub", "cust_101")
    session_id = req.session_id or f"sess_{uuid.uuid4().hex[:8]}"
    case_id = str(uuid.uuid4())

    state = AgentState(
        case_id=case_id,
        session_id=session_id,
        account_id=account_id,
        actor_id=actor_id,
        user_message=req.message
    )

    # Execute workflow
    final_state = await run_workflow(state, db)

    # Persist or update servicing case record in DB
    decision = final_state.policy_decision
    case_rec = CaseModel(
        case_id=final_state.case_id,
        account_id=account_id,
        customer_id=actor_id,
        customer_name=current_user.get("name", "Valued Cardmember"),
        intent=final_state.intent or "general",
        status=final_state.status,
        escalation_reason=decision.reason if (decision and decision.outcome == "ESCALATE") else None,
        priority_action_taken=decision.priority_action if (decision and final_state.priority_action_executed) else None,
        context_snapshot=final_state.context_snapshot,
        policy_outcome=decision.outcome if decision else None,
        rule_matched=decision.matched_rule_id if decision else None
    )

    db.add(case_rec)
    await db.commit()

    return {
        "case_id": final_state.case_id,
        "session_id": final_state.session_id,
        "intent": final_state.intent,
        "agent_response": final_state.agent_response,
        "status": final_state.status,
        "priority_action_executed": final_state.priority_action_executed,
        "policy_decision": {
            "rule_set": decision.rule_set if decision else None,
            "rule_version": decision.rule_version if decision else None,
            "matched_rule_id": decision.matched_rule_id if decision else None,
            "outcome": decision.outcome if decision else None,
            "reason": decision.reason if decision else None,
            "context_snapshot_hash": decision.context_snapshot_hash if decision else None
        },
        "audit_ledger": {
            "seq": final_state.audit_seq,
            "record_hash": final_state.audit_hash
        }
    }
