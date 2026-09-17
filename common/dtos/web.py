from pydantic import BaseModel, Field
from common.enums import UserRole
from datetime import datetime

class OTPRequest(BaseModel):
    identifier: str = Field(..., description="Telegram ID (int/str) or @username")

class OTPVerify(BaseModel):
    telegram_id: int = Field(..., description="The user's Telegram ID")
    code: str = Field(..., description="6-digit OTP code sent via Telegram")

class UserResponse(BaseModel):
    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    barcode: str | None
    phone_number: str | None
    email: str | None
    academic_group: str | None
    role: UserRole
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class RoleUpdateRequest(BaseModel):
    role: UserRole

class PaginatedUsersResponse(BaseModel):
    items: list[UserResponse]
    total: int
    limit: int
    offset: int
