from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.loan import Loan, LoanStatusEnum
from models.user import RoleEnum, User
from schemas.loan import EMIResponse, LoanApprovalRequest, LoanApplyRequest, LoanOut
from utils.logger import log_activity, send_notification
from utils.security import get_current_user

router = APIRouter(prefix="/loans", tags=["Loan"])


def calculate_emi(principal: Decimal, annual_interest_rate: Decimal, tenure_months: int) -> Decimal:
    monthly_rate = annual_interest_rate / Decimal("1200")
    if monthly_rate == 0:
        return (principal / Decimal(tenure_months)).quantize(Decimal("0.01"))

    one_plus_r_pow_n = (Decimal("1") + monthly_rate) ** tenure_months
    emi = principal * monthly_rate * one_plus_r_pow_n / (one_plus_r_pow_n - Decimal("1"))
    return emi.quantize(Decimal("0.01"))


@router.post("/emi", response_model=EMIResponse)
async def emi_calculator(payload: LoanApplyRequest) -> EMIResponse:
    emi = calculate_emi(payload.principal, payload.annual_interest_rate, payload.tenure_months)
    return EMIResponse(
        principal=payload.principal,
        annual_interest_rate=payload.annual_interest_rate,
        tenure_months=payload.tenure_months,
        emi=emi,
    )


@router.post("/apply", response_model=LoanOut)
async def apply_loan(
    payload: LoanApplyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Loan:
    emi = calculate_emi(payload.principal, payload.annual_interest_rate, payload.tenure_months)

    loan = Loan(
        user_id=current_user.id,
        principal=payload.principal,
        annual_interest_rate=payload.annual_interest_rate,
        tenure_months=payload.tenure_months,
        emi=emi,
        status=LoanStatusEnum.pending,
    )

    db.add(loan)
    await log_activity(db, current_user.id, "LOAN_APPLIED", f"principal={payload.principal}, emi={emi}")
    await db.commit()
    await db.refresh(loan)
    return loan


@router.get("/my", response_model=list[LoanOut])
async def my_loans(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Loan]:
    result = await db.execute(select(Loan).where(Loan.user_id == current_user.id).order_by(desc(Loan.id)))
    return list(result.scalars().all())


@router.get("/admin/pending", response_model=list[LoanOut])
async def admin_pending_loans(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Loan]:
    if current_user.role != RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    result = await db.execute(select(Loan).where(Loan.status == LoanStatusEnum.pending).order_by(desc(Loan.id)))
    return list(result.scalars().all())


@router.patch("/admin/{loan_id}", response_model=LoanOut)
async def admin_approve_or_reject(
    loan_id: int,
    payload: LoanApprovalRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Loan:
    if current_user.role != RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    result = await db.execute(select(Loan).where(Loan.id == loan_id))
    loan = result.scalar_one_or_none()
    if loan is None:
        raise HTTPException(status_code=404, detail="Loan not found")

    loan.status = LoanStatusEnum.approved if payload.approve else LoanStatusEnum.rejected
    loan.approved_by = current_user.email

    await log_activity(db, current_user.id, "LOAN_REVIEW", f"loan_id={loan.id}, status={loan.status.value}")
    await db.commit()
    await db.refresh(loan)

    background_tasks.add_task(
        send_notification,
        "email",
        f"user_id={loan.user_id}",
        f"Loan #{loan.id} status updated to {loan.status.value}",
    )
    return loan
