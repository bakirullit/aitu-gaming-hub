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


class CuratorSummary(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    role: UserRole

    class Config:
        from_attributes = True


class DisciplineResponse(BaseModel):
    slug: str
    name: str
    tier: str
    description: str
    chat_url: str
    admin_id: int | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    admin: CuratorSummary | None = None

    class Config:
        from_attributes = True


class DisciplineCreateRequest(BaseModel):
    slug: str = Field(..., min_length=2, max_length=32, description="URL-friendly identifier e.g. cs2")
    name: str = Field(..., min_length=2, max_length=64)
    tier: str = Field(default="medium", description="major or medium")
    description: str = Field(..., min_length=5, max_length=512)
    chat_url: str = Field(..., min_length=5, max_length=255)
    admin_id: int | None = None


class DisciplineUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=64)
    tier: str | None = None
    description: str | None = Field(None, min_length=5, max_length=512)
    chat_url: str | None = Field(None, min_length=5, max_length=255)
    admin_id: int | None = None
    is_active: bool | None = None

