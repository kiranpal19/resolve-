from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import CaseModel
from app.auth.jwt import get_current_user

router = APIRouter(prefix="/api/cases", tags=["cases"])

@router.get("/my-cases")
async def get_my_cases(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    account_id = current_user.get("account_id", "acc_good_customer")
    stmt = select(CaseModel).where(CaseModel.account_id == account_id).order_by(CaseModel.created_at.desc())
    result = await db.execute(stmt)
    cases = result.scalars().all()
    return cases

@router.get("/{case_id}")
async def get_case_by_id(
    case_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(CaseModel).where(CaseModel.case_id == case_id)
    result = await db.execute(stmt)
    case_rec = result.scalar_one_or_none()

    if not case_rec:
        raise HTTPException(status_code=404, detail="Case not found")

    return case_rec
