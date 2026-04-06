from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from models.user import RoleEnum


class UserRegister(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=64)


class UserOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: RoleEnum
    kyc_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class KYCVerifyRequest(BaseModel):
    pan_number: str = Field(min_length=10, max_length=10)
    aadhaar_number: str = Field(min_length=12, max_length=12)

    @field_validator("pan_number")
    @classmethod
    def validate_pan(cls, value: str) -> str:
        if not value[:5].isalpha() or not value[5:9].isdigit() or not value[9].isalpha():
            raise ValueError("Invalid PAN format")
        return value.upper()

    @field_validator("aadhaar_number")
    @classmethod
    def validate_aadhaar(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("Aadhaar must contain only digits")
        return value


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
