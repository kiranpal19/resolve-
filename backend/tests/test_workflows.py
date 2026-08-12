import uuid
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.audit.models import Base
from app.orchestration.state import AgentState
from app.orchestration.workflow_router import run_workflow
from app.audit.verifier import verify_chain

@pytest_asyncio.fixture
async def async_db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    await engine.dispose()

@pytest.mark.asyncio
async def test_fee_reversal_workflow_approval(async_db_session):
    state = AgentState(
        case_id=str(uuid.uuid4()),
        session_id="sess_test_1",
        account_id="acc_good_customer",
        actor_id="cust_101",
        user_message="Can you please reverse my $35 late fee from last week?"
    )

    final_state = await run_workflow(state, async_db_session)
    assert final_state.status == "COMPLETED"
    assert final_state.policy_decision.outcome == "APPROVE"
    assert "approved" in final_state.agent_response.lower()

    # Verify audit chain created during workflow execution
    audit_res = await verify_chain(async_db_session, case_id=final_state.case_id)
    assert audit_res["valid"] is True
    assert audit_res["total_records"] >= 2  # Evaluate + Execute

@pytest.mark.asyncio
async def test_stolen_card_priority_freeze_workflow(async_db_session):
    state = AgentState(
        case_id=str(uuid.uuid4()),
        session_id="sess_test_2",
        account_id="acc_good_customer",
        actor_id="cust_101",
        user_message="My credit card was stolen in the subway this morning! Please send a new one."
    )

    final_state = await run_workflow(state, async_db_session)
    assert final_state.status == "ESCALATED"
    assert final_state.priority_action_executed is True
    assert final_state.priority_action_result["status"] == "SUCCESS"
    assert "IMMEDIATELY FROZEN" in final_state.agent_response

    # Verify audit chain includes security priority freeze record
    audit_res = await verify_chain(async_db_session, case_id=final_state.case_id)
    assert audit_res["valid"] is True
    assert audit_res["total_records"] >= 3  # Evaluate + Priority Freeze + Escalate
