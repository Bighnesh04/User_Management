from __future__ import annotations

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.account import Account
from models.transaction import Transaction, TransactionStatusEnum, TransactionTypeEnum
from models.user import RoleEnum, User
from schemas.transaction import TransactionOut, TransactionRequest
from services.fraud_detection import fraud_detector
from services.payment_service import balance_cache
from utils.logger import log_activity, send_notification
from utils.rate_limit import limiter
from utils.security import get_current_user

router = APIRouter(prefix="/transactions", tags=["Transaction"])


async def _get_account_for_update(db: AsyncSession, account_id: int) -> Optional[Account]:
    result = await db.execute(select(Account).where(Account.id == account_id).with_for_update())
    return result.scalar_one_or_none()


@router.post("/deposit", response_model=TransactionOut)
@limiter.limit("30/minute")
async def deposit(
    request: Request,
    payload: TransactionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Transaction:
    if payload.destination_account_id is None:
        raise HTTPException(status_code=400, detail="destination_account_id is required")

    async with db.begin():
        account = await _get_account_for_update(db, payload.destination_account_id)
        if account is None or account.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Destination account not found")

        account.balance = Decimal(account.balance) + payload.amount
        transaction = Transaction(
            transaction_type=TransactionTypeEnum.deposit,
            destination_account_id=account.id,
            amount=payload.amount,
            status=TransactionStatusEnum.success,
            location=payload.location,
            message="Deposit successful",
        )
        db.add(transaction)
        await log_activity(db, current_user.id, "DEPOSIT", f"account_id={account.id}, amount={payload.amount}")

    await db.refresh(transaction)
    await balance_cache.set_balance(account.id, Decimal(account.balance))
    background_tasks.add_task(send_notification, "email", current_user.email, f"Deposit success: {payload.amount}")
    return transaction


@router.post("/withdraw", response_model=TransactionOut)
@limiter.limit("30/minute")
async def withdraw(
    request: Request,
    payload: TransactionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Transaction:
    if payload.source_account_id is None:
        raise HTTPException(status_code=400, detail="source_account_id is required")

    async with db.begin():
        account = await _get_account_for_update(db, payload.source_account_id)
        if account is None or account.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Source account not found")

        new_balance = Decimal(account.balance) - payload.amount
        if new_balance < Decimal(account.minimum_balance):
            raise HTTPException(status_code=400, detail="Minimum balance rule violated")

        account.balance = new_balance
        transaction = Transaction(
            transaction_type=TransactionTypeEnum.withdraw,
            source_account_id=account.id,
            amount=payload.amount,
            status=TransactionStatusEnum.success,
            location=payload.location,
            message="Withdrawal successful",
        )
        db.add(transaction)
        await log_activity(db, current_user.id, "WITHDRAW", f"account_id={account.id}, amount={payload.amount}")

    await db.refresh(transaction)
    await balance_cache.set_balance(account.id, Decimal(account.balance))
    background_tasks.add_task(send_notification, "sms", current_user.email, f"Withdrawal success: {payload.amount}")
    return transaction


@router.post("/transfer", response_model=TransactionOut)
@limiter.limit("20/minute")
async def transfer(
    request: Request,
    payload: TransactionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Transaction:
    if payload.source_account_id is None or payload.destination_account_id is None:
        raise HTTPException(status_code=400, detail="source_account_id and destination_account_id are required")
    if payload.source_account_id == payload.destination_account_id:
        raise HTTPException(status_code=400, detail="Source and destination must be different")

    alert_reasons: list[str] = []

    try:
        async with db.begin():
            source = await _get_account_for_update(db, payload.source_account_id)
            destination = await _get_account_for_update(db, payload.destination_account_id)

            if source is None or destination is None:
                raise HTTPException(status_code=404, detail="Account not found")
            if source.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="Not allowed to transfer from this source account")

            new_balance = Decimal(source.balance) - payload.amount
            if new_balance < Decimal(source.minimum_balance):
                raise HTTPException(status_code=400, detail="Minimum balance rule violated")

            source.balance = new_balance
            destination.balance = Decimal(destination.balance) + payload.amount

            alert_reasons = fraud_detector.evaluate(source.id, payload.amount, payload.location)
            message = "Transfer successful"
            if alert_reasons:
                message += f" | Fraud alert: {', '.join(alert_reasons)}"

            transaction = Transaction(
                transaction_type=TransactionTypeEnum.transfer,
                source_account_id=source.id,
                destination_account_id=destination.id,
                amount=payload.amount,
                status=TransactionStatusEnum.success,
                location=payload.location,
                message=message,
            )
            db.add(transaction)
            await log_activity(
                db,
                current_user.id,
                "TRANSFER",
                f"source={source.id}, destination={destination.id}, amount={payload.amount}",
            )

        await db.refresh(transaction)
        await balance_cache.set_balance(source.id, Decimal(source.balance))
        await balance_cache.set_balance(destination.id, Decimal(destination.balance))
    except HTTPException:
        raise
    except Exception as exc:
        async with db.begin():
            failed_tx = Transaction(
                transaction_type=TransactionTypeEnum.transfer,
                source_account_id=payload.source_account_id,
                destination_account_id=payload.destination_account_id,
                amount=payload.amount,
                status=TransactionStatusEnum.failed,
                location=payload.location,
                message=f"Rollback due to failure: {exc}",
            )
            db.add(failed_tx)
            await log_activity(db, current_user.id, "TRANSFER_ROLLBACK", str(exc))
        raise HTTPException(status_code=500, detail="Transfer failed and rolled back") from exc

    background_tasks.add_task(send_notification, "email", current_user.email, f"Transfer success: {payload.amount}")
    return transaction


@router.get("/my", response_model=list[TransactionOut])
async def list_my_transactions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Transaction]:
    my_account_ids_result = await db.execute(select(Account.id).where(Account.user_id == current_user.id))
    account_ids = [row[0] for row in my_account_ids_result.all()]
    if not account_ids:
        return []

    result = await db.execute(
        select(Transaction)
        .where(
            or_(
                Transaction.source_account_id.in_(account_ids),
                Transaction.destination_account_id.in_(account_ids),
            )
        )
        .order_by(desc(Transaction.id))
    )
    return list(result.scalars().all())


@router.get("/admin/all", response_model=list[TransactionOut])
async def admin_all_transactions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Transaction]:
    if current_user.role != RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    result = await db.execute(select(Transaction).order_by(desc(Transaction.id)).limit(500))
    return list(result.scalars().all())


@router.get("/admin/fraud-alerts")
async def admin_fraud_alerts(current_user: User = Depends(get_current_user)) -> dict:
    if current_user.role != RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return {"alerts": fraud_detector.get_alerts()}
