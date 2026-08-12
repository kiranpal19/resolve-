import os
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET_KEY = os.getenv("JWT_SECRET", "resolve-amex-codestreet-2026-secret-key-signature")
ALGORITHM = "HS256"

security = HTTPBearer(auto_error=False)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=8)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired authentication token")

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    if not credentials:
        # For seamless testing/demo mode, return a default customer identity if token is missing
        return {
            "sub": "cust_101",
            "name": "Alex Mercer",
            "account_id": "acc_good_customer",
            "role": "customer"
        }
    return decode_access_token(credentials.credentials)

def require_role(role: str):
    def role_checker(user: dict = Depends(get_current_user)):
        user_role = user.get("role", "customer")
        if user_role != role and user_role != "admin":
            raise HTTPException(status_code=403, detail=f"Operation requires {role} role privilege")
        return user
    return role_checker
