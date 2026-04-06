from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class LoanStatusEnum(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)

    principal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    annual_interest_rate: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)
    tenure_months: Mapped[int] = mapped_column(nullable=False)
    emi: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    status: Mapped[LoanStatusEnum] = mapped_column(Enum(LoanStatusEnum), default=LoanStatusEnum.pending, nullable=False)
    approved_by: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    owner = relationship("User", back_populates="loans")
