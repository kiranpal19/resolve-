import uuid
from typing import Dict, Any, List

# Seeded mock dataset for demo/test accounts
MOCK_ACCOUNTS: Dict[str, Dict[str, Any]] = {
    "acc_good_customer": {
        "account_id": "acc_good_customer",
        "customer_id": "cust_101",
        "customer_name": "Alex Mercer",
        "account_standing": "good",
        "account_age_months": 24,
        "delinquency_last_12mo": 0,
        "utilization_pct": 22.5,
        "current_credit_limit": 10000.00,
        "risk_score": 0.08,
        "reversals_last_90_days": 0,
        "step_up_auth_passed": True,
        "cards": [
            {"card_id": "card_9901", "last4": "9901", "status": "active", "type": "Gold Credit"}
        ],
        "fees": [
            {"fee_id": "fee_801", "description": "Late Payment Fee", "amount_usd": 35.00, "date": "2026-07-15", "status": "posted"},
            {"fee_id": "fee_802", "description": "Annual Membership Fee", "amount_usd": 95.00, "date": "2026-07-01", "status": "posted"},
            {"fee_id": "fee_803", "description": "Expedited Delivery Fee", "amount_usd": 150.00, "date": "2026-06-20", "status": "posted"}
        ]
    },
    "acc_cooldown_customer": {
        "account_id": "acc_cooldown_customer",
        "customer_id": "cust_102",
        "customer_name": "Jordan Lee",
        "account_standing": "good",
        "account_age_months": 18,
        "delinquency_last_12mo": 0,
        "utilization_pct": 45.0,
        "current_credit_limit": 5000.00,
        "risk_score": 0.15,
        "reversals_last_90_days": 2,
        "step_up_auth_passed": True,
        "cards": [
            {"card_id": "card_9902", "last4": "9902", "status": "active", "type": "Platinum Credit"}
        ],
        "fees": [
            {"fee_id": "fee_804", "description": "Late Fee", "amount_usd": 40.00, "date": "2026-07-10", "status": "posted"}
        ]
    },
    "acc_high_risk": {
        "account_id": "acc_high_risk",
        "customer_id": "cust_103",
        "customer_name": "Taylor Swift",
        "account_standing": "fair",
        "account_age_months": 4,
        "delinquency_last_12mo": 1,
        "utilization_pct": 88.0,
        "current_credit_limit": 2000.00,
        "risk_score": 0.42,
        "reversals_last_90_days": 0,
        "step_up_auth_passed": False,
        "cards": [
            {"card_id": "card_9903", "last4": "9903", "status": "active", "type": "EveryDay Credit"}
        ],
        "fees": [
            {"fee_id": "fee_805", "description": "Overlimit Fee", "amount_usd": 120.00, "date": "2026-07-20", "status": "posted"}
        ]
    }
}

class CoreBankingClient:
    def __init__(self):
        self.accounts = MOCK_ACCOUNTS

    def get_account_info(self, account_id: str) -> Dict[str, Any]:
        acc = self.accounts.get(account_id)
        if not acc:
            # Return default template for unknown accounts
            return {
                "account_id": account_id,
                "customer_id": f"cust_{account_id}",
                "customer_name": "Valued Cardmember",
                "account_standing": "good",
                "account_age_months": 12,
                "delinquency_last_12mo": 0,
                "utilization_pct": 30.0,
                "current_credit_limit": 5000.00,
                "risk_score": 0.10,
                "reversals_last_90_days": 0,
                "step_up_auth_passed": True,
                "cards": [{"card_id": "card_1000", "last4": "1000", "status": "active", "type": "Blue Cash"}],
                "fees": [{"fee_id": "fee_100", "description": "Late Fee", "amount_usd": 39.00, "date": "2026-07-20", "status": "posted"}]
            }
        return acc

    def reverse_fee(self, account_id: str, fee_id: str, amount_usd: float) -> Dict[str, Any]:
        acc = self.get_account_info(account_id)
        acc["reversals_last_90_days"] = acc.get("reversals_last_90_days", 0) + 1
        return {
            "status": "SUCCESS",
            "transaction_id": f"tx_rev_{uuid.uuid4().hex[:8]}",
            "account_id": account_id,
            "fee_id": fee_id,
            "amount_reversed_usd": amount_usd,
            "message": f"Successfully reversed fee {fee_id} for ${amount_usd:.2f}."
        }

    def update_credit_limit(self, account_id: str, new_limit: float) -> Dict[str, Any]:
        acc = self.get_account_info(account_id)
        old_limit = acc.get("current_credit_limit", 5000.00)
        acc["current_credit_limit"] = new_limit
        return {
            "status": "SUCCESS",
            "transaction_id": f"tx_cli_{uuid.uuid4().hex[:8]}",
            "account_id": account_id,
            "previous_limit": old_limit,
            "new_limit": new_limit,
            "message": f"Successfully updated credit limit to ${new_limit:.2f}."
        }

    def freeze_card(self, account_id: str, card_id: str, reason: str) -> Dict[str, Any]:
        acc = self.get_account_info(account_id)
        for card in acc.get("cards", []):
            if card["card_id"] == card_id:
                card["status"] = "FROZEN"
        return {
            "status": "SUCCESS",
            "action": "FREEZE_CARD",
            "account_id": account_id,
            "card_id": card_id,
            "reason": reason,
            "timestamp": "2026-07-27T09:50:00Z",
            "message": f"Card {card_id} has been IMMEDIATELY FROZEN due to: {reason}."
        }

    def reissue_card(self, account_id: str, card_id: str, shipping_address: Dict[str, Any]) -> Dict[str, Any]:
        new_card_id = f"card_{uuid.uuid4().hex[:4]}"
        return {
            "status": "SUCCESS",
            "action": "REISSUE_CARD",
            "account_id": account_id,
            "old_card_id": card_id,
            "new_card_id": new_card_id,
            "shipping_address": shipping_address,
            "estimated_delivery_days": 3,
            "message": f"New replacement card {new_card_id} ordered and queued for shipping."
        }

_banking_client = None
def get_banking_client() -> CoreBankingClient:
    global _banking_client
    if _banking_client is None:
        _banking_client = CoreBankingClient()
    return _banking_client
