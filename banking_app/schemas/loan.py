from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from models.loan import LoanStatusEnum


class LoanApplyRequest(BaseModel):
    principal: Decimal = Field(gt=0)
    annual_interest_rate: Decimal = Field(gt=0)
    tenure_months: int = Field(gt=0, le=600)


class LoanApprovalRequest(BaseModel):
    approve: bool


class LoanOut(BaseModel):
    id: int
    user_id: int
    principal: Decimal
    annual_interest_rate: Decimal
    tenure_months: int
    emi: Decimal
    status: LoanStatusEnum
    approved_by: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class EMIResponse(BaseModel):
    principal: Decimal
    annual_interest_rate: Decimal
    tenure_months: int
    emi: Decimal
