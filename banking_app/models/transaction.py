from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class TransactionTypeEnum(str, enum.Enum):
    deposit = "deposit"
    withdraw = "withdraw"
    transfer = "transfer"


class TransactionStatusEnum(str, enum.Enum):
    success = "success"
    failed = "failed"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    transaction_type: Mapped[TransactionTypeEnum] = mapped_column(Enum(TransactionTypeEnum), nullable=False)

    source_account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    destination_account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("accounts.id"), nullable=True)

    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[TransactionStatusEnum] = mapped_column(Enum(TransactionStatusEnum), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    message: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    source_account = relationship("Account", foreign_keys=[source_account_id], back_populates="outgoing_transactions")
    destination_account = relationship(
        "Account",
        foreign_keys=[destination_account_id],
        back_populates="incoming_transactions",
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
