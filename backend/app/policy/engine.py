import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from app.policy.loader import get_loader, RuleLoader

class DecisionObject(BaseModel):
    decision_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    rule_set: str
    rule_version: str
    matched_rule_id: Optional[str] = None
    outcome: str  # "APPROVE", "DENY", "ESCALATE"
    reason: Optional[str] = None
    priority_action: Optional[str] = None
    context_snapshot_hash: str
    evaluated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

def compute_hash(data: Any) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"

def match_condition(field_value: Any, condition: Any) -> bool:
    if isinstance(condition, dict):
        for op, target in condition.items():
            if op == "lte":
                if not (field_value is not None and field_value <= target):
                    return False
            elif op == "lt":
                if not (field_value is not None and field_value < target):
                    return False
            elif op == "gte":
                if not (field_value is not None and field_value >= target):
                    return False
            elif op == "gt":
                if not (field_value is not None and field_value > target):
                    return False
            elif op == "eq":
                if not (field_value == target):
                    return False
            elif op == "ne":
                if not (field_value != target):
                    return False
            elif op == "in":
                if not (field_value in target):
                    return False
            else:
                return False
        return True
    else:
        return field_value == condition

def evaluate(rule_set_name: str, context: Dict[str, Any], loader: Optional[RuleLoader] = None) -> DecisionObject:
    if loader is None:
        loader = get_loader()

    rule_data = loader.get_rule_set(rule_set_name)
    rule_version = rule_data.get("version", "1.0.0")
    rules = rule_data.get("rules", [])
    default_outcome = rule_data.get("default", "ESCALATE")

    context_hash = compute_hash(context)

    for rule in rules:
        conditions = rule.get("when", {})
        all_matched = True
        for key, cond in conditions.items():
            val = context.get(key)
            if not match_condition(val, cond):
                all_matched = False
                break

        if all_matched:
            return DecisionObject(
                rule_set=rule_set_name,
                rule_version=rule_version,
                matched_rule_id=rule.get("id"),
                outcome=rule.get("then"),
                reason=rule.get("reason", rule.get("description")),
                priority_action=rule.get("priority_action"),
                context_snapshot_hash=context_hash
            )

    # Fallback to fail-closed default
    return DecisionObject(
        rule_set=rule_set_name,
        rule_version=rule_version,
        matched_rule_id=None,
        outcome=default_outcome,
        reason=f"No matching rule found. Fail-closed default ({default_outcome}) applied.",
        context_snapshot_hash=context_hash
    )
