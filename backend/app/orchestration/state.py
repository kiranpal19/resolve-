import uuid
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.policy.engine import DecisionObject

class AgentState(BaseModel):
    case_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    account_id: str
    actor_id: str
    user_message: str
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)

    # Workflow properties
    intent: Optional[str] = None  # fee_reversal, credit_limit_increase, card_replacement, general
    confidence: float = 0.95
    entities: Dict[str, Any] = Field(default_factory=dict)
    context_snapshot: Dict[str, Any] = Field(default_factory=dict)
    context_snapshot_hash: Optional[str] = None

    # Decision & Audit
    policy_decision: Optional[DecisionObject] = None
    audit_seq: Optional[int] = None
    audit_hash: Optional[str] = None

    # Priority / Execution flags
    priority_action_executed: bool = False
    priority_action_result: Optional[Dict[str, Any]] = None
    execution_result: Optional[Dict[str, Any]] = None
    escalation_id: Optional[str] = None

    # Final response
    agent_response: Optional[str] = None
    status: str = "IN_PROGRESS"  # IN_PROGRESS, COMPLETED, ESCALATED, DENIED, ERROR
