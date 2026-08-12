import re
import os
import json
import uuid
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.orchestration.state import AgentState
from app.policy.engine import evaluate, compute_hash, DecisionObject
from app.audit.ledger import append_audit_record
from app.core_banking.mock_client import get_banking_client

# Check for Anthropic API Key
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

async def classify_intent_node(state: AgentState) -> AgentState:
    msg = state.user_message.lower()

    if any(term in msg for term in ["fee", "waive", "reversal", "charge", "refund", "late fee", "annual fee"]):
        state.intent = "fee_reversal"
        state.confidence = 0.96
    elif any(term in msg for term in ["limit", "credit line", "raise", "increase", "higher limit", "more credit"]):
        state.intent = "credit_limit_increase"
        state.confidence = 0.94
    elif any(term in msg for term in ["replace", "stolen", "lost", "damaged", "broken card", "new card", "stole"]):
        state.intent = "card_replacement"
        state.confidence = 0.98
    else:
        state.intent = "general"
        state.confidence = 0.85

    return state

async def extract_entities_node(state: AgentState) -> AgentState:
    msg = state.user_message
    msg_lower = msg.lower()
    entities: Dict[str, Any] = {}

    if state.intent == "fee_reversal":
        # Extract amount in USD
        match = re.search(r'\$?(\d+(\.\d{1,2})?)', msg)
        if match:
            entities["fee_amount_usd"] = float(match.group(1))
        else:
            entities["fee_amount_usd"] = 35.00  # Default fee amount if unspecified

        entities["fee_id"] = "fee_801"

    elif state.intent == "credit_limit_increase":
        # Extract requested percentage or amount
        match = re.search(r'(\d+)%', msg)
        if match:
            entities["requested_increase_pct"] = float(match.group(1))
        else:
            match_amt = re.search(r'\$?(\d{3,6})', msg)
            if match_amt:
                amt = float(match_amt.group(1))
                entities["requested_increase_pct"] = round((amt / 5000.0) * 100, 1)
            else:
                entities["requested_increase_pct"] = 20.0  # Default 20% request

    elif state.intent == "card_replacement":
        if "stolen" in msg_lower or "stole" in msg_lower:
            entities["reason"] = "stolen"
        elif "lost" in msg_lower:
            entities["reason"] = "lost"
        else:
            entities["reason"] = "damaged"

        entities["shipping_address_changed"] = "new address" in msg_lower or "moved" in msg_lower or "different address" in msg_lower
        entities["step_up_auth_passed"] = True
        entities["card_id"] = "card_9901"

    state.entities = entities
    return state

async def build_context_node(state: AgentState) -> AgentState:
    client = get_banking_client()
    account_info = client.get_account_info(state.account_id)

    # Merge banking account parameters with user request entities into context snapshot
    context: Dict[str, Any] = {
        "account_id": state.account_id,
        "account_standing": account_info.get("account_standing", "good"),
        "account_age_months": account_info.get("account_age_months", 12),
        "delinquency_last_12mo": account_info.get("delinquency_last_12mo", 0),
        "utilization_pct": account_info.get("utilization_pct", 25.0),
        "current_credit_limit": account_info.get("current_credit_limit", 5000.0),
        "risk_score": account_info.get("risk_score", 0.10),
        "reversals_last_90_days": account_info.get("reversals_last_90_days", 0),
        "step_up_auth_passed": account_info.get("step_up_auth_passed", True)
    }

    # Overlay extracted request entities
    context.update(state.entities)

    state.context_snapshot = context
    state.context_snapshot_hash = compute_hash(context)
    return state

async def evaluate_policy_node(state: AgentState) -> AgentState:
    rule_set_name = state.intent
    decision = evaluate(rule_set_name, state.context_snapshot)
    state.policy_decision = decision
    return state

async def write_audit_node(state: AgentState, db: AsyncSession) -> AgentState:
    """
    Writes the proposed action and deterministic policy outcome to the immutable audit ledger
    BEFORE any execution or human escalation happens.
    """
    decision = state.policy_decision
    case_uuid = uuid.UUID(state.case_id)

    rec = await append_audit_record(
        db=db,
        case_id=case_uuid,
        actor_type="ai",
        actor_id=state.actor_id or "resolve_ai_agent",
        action=f"EVALUATE_{state.intent.upper()}",
        rule_set=decision.rule_set,
        rule_version=decision.rule_version,
        matched_rule_id=decision.matched_rule_id,
        outcome=decision.outcome,
        reason=decision.reason,
        context_snapshot_hash=decision.context_snapshot_hash,
        payload={
            "user_message": state.user_message,
            "entities": state.entities,
            "priority_action": decision.priority_action
        }
    )

    state.audit_seq = rec.seq
    state.audit_hash = rec.record_hash
    return state

async def priority_action_node(state: AgentState, db: AsyncSession) -> AgentState:
    """
    Handles immediate priority actions required by policy (e.g. freezing stolen cards instantly).
    """
    decision = state.policy_decision
    if decision and decision.priority_action == "FREEZE_CARD":
        client = get_banking_client()
        card_id = state.entities.get("card_id", "card_9901")
        result = client.freeze_card(state.account_id, card_id, reason="STOLEN_CARD_POLICY_TRIGGER")

        state.priority_action_executed = True
        state.priority_action_result = result

        # Write priority audit event
        case_uuid = uuid.UUID(state.case_id)
        await append_audit_record(
            db=db,
            case_id=case_uuid,
            actor_type="system",
            actor_id="priority_security_node",
            action="FREEZE_CARD_PRIORITY",
            rule_set=decision.rule_set,
            rule_version=decision.rule_version,
            matched_rule_id=decision.matched_rule_id,
            outcome="EXECUTED",
            reason="Immediate freeze executed per card replacement policy (stolen card)",
            context_snapshot_hash=decision.context_snapshot_hash,
            payload=result
        )

    return state

async def execute_action_node(state: AgentState, db: AsyncSession) -> AgentState:
    client = get_banking_client()
    decision = state.policy_decision
    result = None

    if state.intent == "fee_reversal":
        fee_id = state.entities.get("fee_id", "fee_801")
        amount = state.entities.get("fee_amount_usd", 35.00)
        result = client.reverse_fee(state.account_id, fee_id, amount)
        state.agent_response = f"I've evaluated your request and approved the fee reversal. A credit of ${amount:.2f} has been posted to your account."

    elif state.intent == "credit_limit_increase":
        pct = state.entities.get("requested_increase_pct", 20.0)
        current = state.context_snapshot.get("current_credit_limit", 5000.0)
        new_limit = current * (1 + pct / 100.0)
        result = client.update_credit_limit(state.account_id, new_limit)
        state.agent_response = f"Great news! Your request for a credit limit increase was approved. Your new credit limit is ${new_limit:,.2f}."

    elif state.intent == "card_replacement":
        card_id = state.entities.get("card_id", "card_9901")
        address = {"street": "123 Main St", "city": "New York", "state": "NY", "zip": "10001"}
        result = client.reissue_card(state.account_id, card_id, address)
        state.agent_response = f"Your replacement card has been ordered! It will arrive at your address on file within 3 business days."

    state.execution_result = result
    state.status = "COMPLETED"

    # Write execution audit record
    case_uuid = uuid.UUID(state.case_id)
    await append_audit_record(
        db=db,
        case_id=case_uuid,
        actor_type="system",
        actor_id="execution_engine",
        action=f"EXECUTE_{state.intent.upper()}",
        rule_set=decision.rule_set if decision else None,
        rule_version=decision.rule_version if decision else None,
        matched_rule_id=decision.matched_rule_id if decision else None,
        outcome="SUCCESS",
        reason="Automated action completed successfully following policy approval",
        context_snapshot_hash=state.context_snapshot_hash,
        payload=result or {}
    )

    return state

async def escalate_node(state: AgentState, db: AsyncSession) -> AgentState:
    decision = state.policy_decision
    state.status = "ESCALATED"
    state.escalation_id = f"esc_{uuid.uuid4().hex[:8]}"

    prefix = ""
    if state.priority_action_executed:
        prefix = "ALERT: Your card has been IMMEDIATELY FROZEN to protect your account. "

    state.agent_response = (
        f"{prefix}Your request requires specialized specialist authorization ({decision.reason if decision else 'Policy limit'}). "
        f"Case #{state.case_id[:8]} has been assigned to a Senior Card Servicing Specialist in our escalation queue."
    )

    # Write escalation audit record
    case_uuid = uuid.UUID(state.case_id)
    await append_audit_record(
        db=db,
        case_id=case_uuid,
        actor_type="system",
        actor_id="escalation_manager",
        action="ESCALATE_TO_HUMAN",
        rule_set=decision.rule_set if decision else None,
        rule_version=decision.rule_version if decision else None,
        matched_rule_id=decision.matched_rule_id if decision else None,
        outcome="ESCALATED",
        reason=decision.reason if decision else "Manual escalation required",
        context_snapshot_hash=state.context_snapshot_hash,
        payload={
            "escalation_id": state.escalation_id,
            "priority_action_executed": state.priority_action_executed,
            "context": state.context_snapshot
        }
    )

    return state

async def deny_node(state: AgentState, db: AsyncSession) -> AgentState:
    decision = state.policy_decision
    state.status = "DENIED"
    state.agent_response = f"We are unable to approve your request at this time. Reason: {decision.reason if decision else 'Policy terms not met'}."

    # Write denial audit record
    case_uuid = uuid.UUID(state.case_id)
    await append_audit_record(
        db=db,
        case_id=case_uuid,
        actor_type="system",
        actor_id="policy_enforcer",
        action=f"DENY_{state.intent.upper()}",
        rule_set=decision.rule_set if decision else None,
        rule_version=decision.rule_version if decision else None,
        matched_rule_id=decision.matched_rule_id if decision else None,
        outcome="DENIED",
        reason=decision.reason if decision else "Denied by policy engine",
        context_snapshot_hash=state.context_snapshot_hash,
        payload={"context": state.context_snapshot}
    )

    return state
