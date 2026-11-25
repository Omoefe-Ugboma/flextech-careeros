
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)

class CompanyRegister(BaseModel):
    company_name: str = Field(min_length=2, max_length=200)
    company_email: EmailStr
    website: str | None = Field(default=None, max_length=255)
    description: str | None = None
    admin_email: EmailStr
    password: str = Field(min_length=12, max_length=128)

class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class EmailVerificationRequest(BaseModel):
    token: str = Field(min_length=1, max_length=256)


class ResendVerificationRequest(BaseModel):
    email: EmailStr

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(
        min_length=1,
        max_length=256,
    )
    new_password: str = Field(
        min_length=12,
        max_length=128,
    )