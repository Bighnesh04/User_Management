from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import RoleEnum, User
from schemas.user import KYCVerifyRequest, Token, UserOut, UserRegister
from utils.logger import log_activity
from utils.rate_limit import limiter
from utils.security import create_access_token, get_current_user, get_password_hash, verify_password

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserOut)
@limiter.limit("10/minute")
async def register_user(request: Request, payload: UserRegister, db: AsyncSession = Depends(get_db)) -> User:
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        role=RoleEnum.customer,
    )
    db.add(user)
    await log_activity(db, None, "USER_REGISTER", f"email={payload.email}")
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=Token)
@limiter.limit("20/minute")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)) -> Token:
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    await log_activity(db, user.id, "USER_LOGIN", "Login success")
    await db.commit()
    return Token(access_token=token)


@router.post("/kyc/verify", response_model=UserOut)
async def verify_kyc(
    payload: KYCVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    current_user.pan_number = payload.pan_number
    current_user.aadhaar_number = payload.aadhaar_number
    current_user.kyc_verified = True

    await log_activity(db, current_user.id, "KYC_VERIFIED", "KYC simulated verification complete")
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.get("/admin/users", response_model=list[UserOut])
async def list_all_users(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[User]:
    if current_user.role != RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    result = await db.execute(select(User).order_by(User.id.desc()))
    return list(result.scalars().all())
