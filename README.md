# Resolve: End-to-End Card Servicing Agent

**Resolve** is a production-grade, deterministic AI servicing agent for credit card customers built for **American Express CodeStreet 2026** (Round 2 — Working Prototype).

It automates three core request types:
1. **Fee Reversals**
2. **Credit Limit Increases**
3. **Card Replacements** (including immediate priority freeze protocols on stolen card reports)

---

## 🏛️ Core Architectural Principle

> **Non-negotiable Architectural Guarantee**:
> The conversational AI layer (LLM) may **ONLY propose** a structured action. It NEVER has direct write access to any banking database or account-changing service. A separate, pure-function **Policy Engine** evaluates every proposed action against versioned YAML rule sets. The evaluation decision is written to an **Immutable, Hash-Chained Audit Ledger** *BEFORE* any action executes or any human handoff occurs.

```
┌─────────────────┐       Propose Action       ┌───────────────────┐
│ Customer Chat / │ ─────────────────────────> │   Policy Engine   │
│ Conversational  │                            │ (Declarative YAML)│
└─────────────────┘                            └─────────┬─────────┘
                                                         │ Evaluates Outcome
                                                         ▼ (APPROVE/DENY/ESCALATE)
┌─────────────────┐      Recalculates Hash     ┌───────────────────┐
│   GET /audit/   │ <───────────────────────── │ Immutable Ledger  │
│     verify      │    SHA-256 Chain Record    │   (Append-Only)   │
└─────────────────┘                            └─────────┬─────────┘
                                                         │ Written BEFORE Action
                                                         ▼
                                               ┌───────────────────┐
                                               │ Core Banking API /│
                                               │ Agent Escalation  │
                                               └───────────────────┘
```

### How the Code Enforces This Structurally

1. **Decoupled Policy Engine (`backend/app/policy/engine.py`)**:
   Pure-function `evaluate(rule_set_name, context) -> DecisionObject`. It parses strict boolean/numeric condition trees without LLM involvement. Fail-closed default enforces `ESCALATE` on any unmapped condition.
2. **Immutable Audit Ledger (`backend/app/audit/ledger.py`)**:
   `append_audit_record()` is the **ONLY** function in the entire codebase allowed to write to the `audit_log` table. Each entry contains a cryptographic SHA-256 record hash chaining from `prev_hash`: `record_hash = SHA256(canonical_json(prev_hash + fields))`.
3. **Ordering in LangGraph Orchestration (`backend/app/orchestration/workflow_router.py`)**:
   The workflow strictly executes `write_audit_node` **prior** to executing `execute_action_node`, `priority_action_node` (card freeze), or `escalate_node`.
4. **Verification Endpoint (`GET /audit/verify`)**:
   Replays sequence numbers from genesis (`0"*64`) to latest record, detecting any missing links or modified row content.

---

## 🚀 Quick Start (Docker Compose)

Run the full stack with a single command:

```bash
docker-compose up --build
```

### Services & Endpoints

| Service | Endpoint | Description |
| :--- | :--- | :--- |
| **Customer Chat UI** | `http://localhost:3000` | Conversational interface & live cryptographic audit ledger viewer |
| **Human Agent Console** | `http://localhost:3001` | Escalated queue & decision dashboard with context packets |
| **FastAPI Backend API** | `http://localhost:8000` | REST API, OpenAPI docs at `http://localhost:8000/docs` |
| **Chain Verification** | `http://localhost:8000/audit/verify` | Public cryptographic ledger audit endpoint |

---

## 🧪 Running Tests Locally

Run the complete automated test suite (Policy Engine rules, Cryptographic Hash Chain, DB Tampering Detection, and Workflow Integration tests):

```bash
cd backend
python -m pytest tests/ -v
```

### Key Test Coverage
- `test_policy_engine.py`: Verifies every rule path in `fee_reversal.yaml`, `credit_limit_increase.yaml`, `card_replacement.yaml`, and the fail-closed default path.
- `test_audit_chain.py`: Verifies SHA-256 hash chaining and simulates direct SQL database tampering to assert `verify_chain()` detects broken links at the exact sequence number.
- `test_workflows.py`: End-to-end simulation of automated fee reversals and stolen card priority freeze workflows.

---

## 🔍 Core Banking Integration Contract

In production, `backend/app/core_banking/mock_client.py` would integrate directly with core banking ledger APIs (e.g. FIS/Fiserv/TSYS). The client interface exposes deterministic endpoints for:
- Account standing & credit limit info lookup
- Fee reversal transaction execution (`reverse_fee`)
- Credit limit adjustments (`update_credit_limit`)
- Emergency card freeze (`freeze_card`) and card reissuance (`reissue_card`)

---

## ✅ Definition of Done Verification

- [x] All three workflows runnable end-to-end via Customer Chat UI
- [x] Every state-changing action has an `audit_log` entry written *before* execution, verifiable via `GET /audit/verify`
- [x] Direct database tampering is detected by `verify_chain()`
- [x] Zero LLM code paths write to account data without passing through `evaluate_policy()`
- [x] Escalated cases populate human Agent Console with full context packets
- [x] Stolen-card reports trigger an immediate freeze priority action before graph completion
- [x] Full stack runnable via `docker-compose up`
- [x] Unit + integration test suites passing cleanly
