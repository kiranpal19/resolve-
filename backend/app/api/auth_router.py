from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.auth.jwt import create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])

class LoginRequest(BaseModel):
    user_type: str  # "customer" or "agent"
    account_id: str = "acc_good_customer"

@router.post("/token")
def get_token(req: LoginRequest):
    if req.user_type == "agent":
        token_data = {
            "sub": "agent_7701",
            "name": "Sarah Connor (Senior Servicing Agent)",
            "role": "agent"
        }
    else:
        token_data = {
            "sub": "cust_101",
            "name": "Alex Mercer",
            "account_id": req.account_id,
            "role": "customer"
        }

    token = create_access_token(token_data)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": token_data
    }
