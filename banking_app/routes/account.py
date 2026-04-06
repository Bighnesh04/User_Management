from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.account import Account, AccountTypeEnum
from models.user import User
from schemas.account import AccountCreate, AccountOut, InterestApplyResponse
from services.payment_service import balance_cache
from utils.logger import log_activity
from utils.security import get_current_user

router = APIRouter(prefix="/accounts", tags=["Account"])


@router.post("", response_model=AccountOut)
async def create_account(
    payload: AccountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Account:
    if not current_user.kyc_verified:
        raise HTTPException(status_code=400, detail="Complete KYC before creating an account")

    minimum_balance = Decimal("1000.00") if payload.account_type == AccountTypeEnum.savings else Decimal("0.00")
    annual_interest_rate = Decimal("4.00") if payload.account_type == AccountTypeEnum.savings else Decimal("0.00")

    if payload.initial_deposit < minimum_balance:
        raise HTTPException(status_code=400, detail=f"Initial deposit must be at least {minimum_balance}")

    account = Account(
        account_number=f"AC{current_user.id}{int(datetime.utcnow().timestamp())}",
        user_id=current_user.id,
        account_type=payload.account_type,
        balance=payload.initial_deposit,
        minimum_balance=minimum_balance,
        annual_interest_rate=annual_interest_rate,
    )
    db.add(account)
    await log_activity(db, current_user.id, "ACCOUNT_CREATED", f"account_number={account.account_number}")
    await db.commit()
    await db.refresh(account)
    await balance_cache.set_balance(account.id, Decimal(account.balance))
    return account


@router.get("", response_model=list[AccountOut])
async def list_my_accounts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Account]:
    result = await db.execute(select(Account).where(Account.user_id == current_user.id).order_by(Account.id.desc()))
    return list(result.scalars().all())


@router.post("/{account_id}/interest", response_model=InterestApplyResponse)
async def apply_interest(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InterestApplyResponse:
    result = await db.execute(select(Account).where(Account.id == account_id, Account.user_id == current_user.id))
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")

    if account.account_type != AccountTypeEnum.savings:
        raise HTTPException(status_code=400, detail="Interest applies only to savings account")

    old_balance = Decimal(account.balance)
    monthly_rate = Decimal(account.annual_interest_rate) / Decimal("1200")
    interest = (old_balance * monthly_rate).quantize(Decimal("0.01"))
    account.balance = old_balance + interest

    await log_activity(db, current_user.id, "INTEREST_APPLIED", f"account_id={account.id}, interest={interest}")
    await db.commit()
    await db.refresh(account)
    await balance_cache.set_balance(account.id, Decimal(account.balance))

    return InterestApplyResponse(
        account_id=account.id,
        old_balance=old_balance,
        interest_added=interest,
        new_balance=Decimal(account.balance),
    )
