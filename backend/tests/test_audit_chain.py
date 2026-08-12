import uuid
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

from app.audit.models import Base, AuditLogRecord
from app.audit.ledger import append_audit_record
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
async def test_audit_ledger_valid_chain(async_db_session):
    case_id = uuid.uuid4()

    # Append 2 valid records
    rec1 = await append_audit_record(
        db=async_db_session,
        case_id=case_id,
        actor_type="ai",
        actor_id="test_agent",
        action="EVALUATE_FEE_REVERSAL",
        rule_set="fee_reversal",
        rule_version="2026.07.1",
        matched_rule_id="fr_001",
        outcome="APPROVE",
        reason="Under ceiling",
        context_snapshot_hash="sha256:abc",
        payload={"amount": 50.0}
    )

    rec2 = await append_audit_record(
        db=async_db_session,
        case_id=case_id,
        actor_type="system",
        actor_id="execution_engine",
        action="EXECUTE_FEE_REVERSAL",
        outcome="SUCCESS",
        context_snapshot_hash="sha256:abc",
        payload={"transaction_id": "tx_123"}
    )

    await async_db_session.commit()

    # Verify unbroken chain
    result = await verify_chain(async_db_session)
    assert result["valid"] is True
    assert result["total_records"] == 2
    assert result["last_seq"] == 2

@pytest.mark.asyncio
async def test_audit_ledger_detects_tampering(async_db_session):
    case_id = uuid.uuid4()

    # Append 2 valid records
    rec1 = await append_audit_record(
        db=async_db_session,
        case_id=case_id,
        actor_type="ai",
        actor_id="test_agent",
        action="EVALUATE_FEE_REVERSAL",
        outcome="APPROVE",
        context_snapshot_hash="sha256:111",
        payload={"amount": 50.0}
    )

    rec2 = await append_audit_record(
        db=async_db_session,
        case_id=case_id,
        actor_type="system",
        actor_id="execution_engine",
        action="EXECUTE_FEE_REVERSAL",
        outcome="SUCCESS",
        context_snapshot_hash="sha256:111",
        payload={"amount": 50.0}
    )

    await async_db_session.commit()

    # Direct database tampering simulation: alter rec1 outcome from APPROVE to DENY
    stmt = select(AuditLogRecord).where(AuditLogRecord.seq == 1)
    res = await async_db_session.execute(stmt)
    tampered_row = res.scalar_one()
    tampered_row.outcome = "DENY"  # Tamper with historical payload/outcome
    await async_db_session.commit()

    # Chain verification MUST fail at sequence 1
    verify_res = await verify_chain(async_db_session)
    assert verify_res["valid"] is False
    assert verify_res["broken_seq"] == 1
    assert "Tampered record detected" in verify_res["reason"]
