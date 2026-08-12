from sqlalchemy.ext.asyncio import AsyncSession
from app.orchestration.state import AgentState
from app.orchestration.nodes import (
    classify_intent_node,
    extract_entities_node,
    build_context_node,
    evaluate_policy_node,
    write_audit_node,
    priority_action_node,
    execute_action_node,
    escalate_node,
    deny_node
)

async def run_workflow(state: AgentState, db: AsyncSession) -> AgentState:
    """
    Executes the deterministic card servicing workflow:
    1. Classify Intent
    2. Extract Entities
    3. Build Account Context
    4. Evaluate Policy Engine Rules
    5. Write Audit Ledger Record (BEFORE ANY ACTION / ESCALATION)
    6. Run Priority Security Actions (if triggered, e.g., Freeze Stolen Card)
    7. Execute Action OR Escalate to Human OR Deny Request
    """
    # Step 1: Intent
    state = await classify_intent_node(state)

    # Step 2: Entities
    state = await extract_entities_node(state)

    # Step 3: Banking Context
    state = await build_context_node(state)

    # Step 4: Policy Engine Evaluation
    state = await evaluate_policy_node(state)

    # Step 5: Write Audit Record (GUARANTEED BEFORE EXECUTION)
    state = await write_audit_node(state, db)

    # Step 6: Priority Action (stolen card freeze, etc.)
    if state.policy_decision and state.policy_decision.priority_action:
        state = await priority_action_node(state, db)

    # Step 7: Conditional Branching based on policy outcome
    outcome = state.policy_decision.outcome if state.policy_decision else "ESCALATE"

    if outcome == "APPROVE":
        state = await execute_action_node(state, db)
    elif outcome == "ESCALATE":
        state = await escalate_node(state, db)
    elif outcome == "DENY":
        state = await deny_node(state, db)
    else:
        # Default fail-closed fallback
        state = await escalate_node(state, db)

    return state
