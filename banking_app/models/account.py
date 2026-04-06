from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class AccountTypeEnum(str, enum.Enum):
    savings = "savings"
    current = "current"


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_number: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    account_type: Mapped[AccountTypeEnum] = mapped_column(Enum(AccountTypeEnum), nullable=False)

    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    minimum_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    annual_interest_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    owner = relationship("User", back_populates="accounts")
    outgoing_transactions = relationship(
        "Transaction",
        back_populates="source_account",
        foreign_keys="Transaction.source_account_id",
    )
    incoming_transactions = relationship(
        "Transaction",
        back_populates="destination_account",
        foreign_keys="Transaction.destination_account_id",
    )
