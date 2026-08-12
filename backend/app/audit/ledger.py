import hashlib
import json
import uuid
from typing import Dict, Any, Optional, Union
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.audit.models import AuditLogRecord

GENESIS_HASH = "0" * 64

def calculate_record_hash(prev_hash: str, fields: Dict[str, Any]) -> str:
    payload_to_hash = {
        "prev_hash": prev_hash,
        "seq": fields["seq"],
        "case_id": str(fields["case_id"]),
        "actor_type": fields["actor_type"],
        "actor_id": fields["actor_id"],
        "action": fields["action"],
        "rule_set": fields.get("rule_set"),
        "rule_version": fields.get("rule_version"),
        "matched_rule_id": fields.get("matched_rule_id"),
        "outcome": fields.get("outcome"),
        "reason": fields.get("reason"),
        "context_snapshot_hash": fields["context_snapshot_hash"],
        "payload": fields["payload"]
    }
    canonical = json.dumps(payload_to_hash, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()

async def append_audit_record(
    db: AsyncSession,
    case_id: Union[uuid.UUID, str],
    actor_type: str,
    actor_id: str,
    action: str,
    context_snapshot_hash: str,
    payload: Dict[str, Any],
    rule_set: Optional[str] = None,
    rule_version: Optional[str] = None,
    matched_rule_id: Optional[str] = None,
    outcome: Optional[str] = None,
    reason: Optional[str] = None
) -> AuditLogRecord:
    """
    CRITICAL SECURITY CONTRACT:
    This is the ONLY function in the codebase permitted to insert into the audit_log table.
    Records are immutable once inserted.
    """
    if actor_type not in ('ai', 'human', 'system'):
        raise ValueError(f"Invalid actor_type: {actor_type}. Must be 'ai', 'human', or 'system'.")

    case_id_str = str(case_id)

    # Fetch latest record to obtain prev_hash and next sequence number
    stmt = select(AuditLogRecord).order_by(AuditLogRecord.seq.desc()).limit(1)
    result = await db.execute(stmt)
    latest_record = result.scalar_one_or_none()

    if latest_record is None:
        seq = 1
        prev_hash = GENESIS_HASH
    else:
        seq = latest_record.seq + 1
        prev_hash = latest_record.record_hash

    fields = {
        "seq": seq,
        "case_id": case_id_str,
        "actor_type": actor_type,
        "actor_id": actor_id,
        "action": action,
        "rule_set": rule_set,
        "rule_version": rule_version,
        "matched_rule_id": matched_rule_id,
        "outcome": outcome,
        "reason": reason,
        "context_snapshot_hash": context_snapshot_hash,
        "payload": payload
    }

    rec_hash = calculate_record_hash(prev_hash, fields)

    record = AuditLogRecord(
        seq=seq,
        case_id=case_id_str,
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        rule_set=rule_set,
        rule_version=rule_version,
        matched_rule_id=matched_rule_id,
        outcome=outcome,
        reason=reason,
        context_snapshot_hash=context_snapshot_hash,
        payload=payload,
        prev_hash=prev_hash,
        record_hash=rec_hash
    )

    db.add(record)
    await db.flush()
    return record
