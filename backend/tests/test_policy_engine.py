import pytest
from app.policy.engine import evaluate, compute_hash

def test_fee_reversal_approve():
    context = {
        "fee_amount_usd": 50.0,
        "account_standing": "good",
        "reversals_last_90_days": 0,
        "risk_score": 0.1
    }
    decision = evaluate("fee_reversal", context)
    assert decision.outcome == "APPROVE"
    assert decision.matched_rule_id == "fr_001"

def test_fee_reversal_cooldown_escalate():
    context = {
        "fee_amount_usd": 35.0,
        "account_standing": "good",
        "reversals_last_90_days": 1,
        "risk_score": 0.1
    }
    decision = evaluate("fee_reversal", context)
    assert decision.outcome == "ESCALATE"
    assert decision.matched_rule_id == "fr_002"

def test_fee_reversal_ceiling_escalate():
    context = {
        "fee_amount_usd": 150.0,
        "account_standing": "good",
        "reversals_last_90_days": 0,
        "risk_score": 0.1
    }
    decision = evaluate("fee_reversal", context)
    assert decision.outcome == "ESCALATE"
    assert decision.matched_rule_id == "fr_003"

def test_credit_limit_approve():
    context = {
        "requested_increase_pct": 20.0,
        "account_age_months": 12,
        "delinquency_last_12mo": 0,
        "utilization_pct": 30.0,
        "risk_score": 0.15
    }
    decision = evaluate("credit_limit_increase", context)
    assert decision.outcome == "APPROVE"
    assert decision.matched_rule_id == "cli_001"

def test_credit_limit_new_account_deny():
    context = {
        "requested_increase_pct": 15.0,
        "account_age_months": 3,
        "delinquency_last_12mo": 0,
        "utilization_pct": 20.0,
        "risk_score": 0.10
    }
    decision = evaluate("credit_limit_increase", context)
    assert decision.outcome == "DENY"
    assert decision.matched_rule_id == "cli_002"

def test_card_replacement_stolen_freeze():
    context = {
        "reason": "stolen",
        "shipping_address_changed": False,
        "step_up_auth_passed": True
    }
    decision = evaluate("card_replacement", context)
    assert decision.outcome == "ESCALATE"
    assert decision.matched_rule_id == "cr_001"
    assert decision.priority_action == "FREEZE_CARD"

def test_card_replacement_damaged_approve():
    context = {
        "reason": "damaged",
        "shipping_address_changed": False,
        "step_up_auth_passed": True
    }
    decision = evaluate("card_replacement", context)
    assert decision.outcome == "APPROVE"
    assert decision.matched_rule_id == "cr_002"

def test_fail_closed_default():
    context = {}  # Empty context matches no specific rule
    decision = evaluate("fee_reversal", context)
    assert decision.outcome == "ESCALATE"
    assert decision.matched_rule_id is None
