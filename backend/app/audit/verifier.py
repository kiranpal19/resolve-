from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.audit.models import AuditLogRecord
from app.audit.ledger import calculate_record_hash, GENESIS_HASH

async def verify_chain(db: AsyncSession, case_id: Optional[str] = None) -> Dict[str, Any]:
    stmt = select(AuditLogRecord).order_by(AuditLogRecord.seq.asc())
    if case_id:
        stmt = stmt.where(AuditLogRecord.case_id == case_id)

    result = await db.execute(stmt)
    records: List[AuditLogRecord] = list(result.scalars().all())

    if not records:
        return {
            "valid": True,
            "total_records": 0,
            "message": "Audit log is empty."
        }

    expected_prev_hash = GENESIS_HASH if not case_id else records[0].prev_hash

    for i, record in enumerate(records):
        # 1. Check prev_hash continuity unless filtering by specific case_id
        if not case_id and record.prev_hash != expected_prev_hash:
            return {
                "valid": False,
                "broken_seq": record.seq,
                "case_id": str(record.case_id),
                "reason": f"Broken chain link at sequence {record.seq}: expected prev_hash {expected_prev_hash}, got {record.prev_hash}"
            }

        # 2. Recalculate hash for current record fields
        fields = {
            "seq": record.seq,
            "case_id": record.case_id,
            "actor_type": record.actor_type,
            "actor_id": record.actor_id,
            "action": record.action,
            "rule_set": record.rule_set,
            "rule_version": record.rule_version,
            "matched_rule_id": record.matched_rule_id,
            "outcome": record.outcome,
            "reason": record.reason,
            "context_snapshot_hash": record.context_snapshot_hash,
            "payload": record.payload
        }

        recalculated = calculate_record_hash(record.prev_hash, fields)
        if recalculated != record.record_hash:
            return {
                "valid": False,
                "broken_seq": record.seq,
                "case_id": str(record.case_id),
                "reason": f"Tampered record detected at sequence {record.seq}: stored record_hash {record.record_hash} does not match recalculated hash {recalculated}"
            }

        expected_prev_hash = record.record_hash

    return {
        "valid": True,
        "total_records": len(records),
        "last_seq": records[-1].seq,
        "latest_hash": records[-1].record_hash,
        "message": "Audit ledger cryptographic integrity verified successfully."
    }
