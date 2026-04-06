from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from models.transaction import TransactionStatusEnum, TransactionTypeEnum


class TransactionRequest(BaseModel):
    source_account_id: Optional[int] = None
    destination_account_id: Optional[int] = None
    amount: Decimal = Field(gt=0)
    location: Optional[str] = Field(default=None, max_length=120)


class TransactionOut(BaseModel):
    id: int
    transaction_type: TransactionTypeEnum
    source_account_id: Optional[int]
    destination_account_id: Optional[int]
    amount: Decimal
    status: TransactionStatusEnum
    message: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
