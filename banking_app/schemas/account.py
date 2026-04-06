from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from models.account import AccountTypeEnum


class AccountCreate(BaseModel):
    account_type: AccountTypeEnum
    initial_deposit: Decimal = Field(ge=0)


class AccountOut(BaseModel):
    id: int
    account_number: str
    account_type: AccountTypeEnum
    balance: Decimal
    minimum_balance: Decimal
    annual_interest_rate: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}


class InterestApplyResponse(BaseModel):
    account_id: int
    old_balance: Decimal
    interest_added: Decimal
    new_balance: Decimal
