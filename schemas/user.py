import re
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, model_validator


class UserRole(str, Enum):
    """Platform user roles."""
    guest = "guest"
    verified_guest = "verified_guest"
    student = "student"
    staff = "staff"
    admin = "admin"


class UserBase(BaseModel):
    """Base user attributes."""
    telegram_id: int
    username: str | None = None
    full_name: str
    phone_number: str
    gmail: EmailStr

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Full name must be a string")
        trimmed = v.strip()
        words = trimmed.split()
        if len(words) < 2:
            raise ValueError("Full name must contain at least 2 words")
        for word in words:
            if not word.isalpha():
                raise ValueError("Full name must contain only alphabetic characters")
        return " ".join(words)

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Phone number must be a string")
        cleaned = re.sub(r"[\s\-\(\)]", "", v.strip())
        if not re.match(r"^\+[1-9]\d{6,14}$", cleaned):
            raise ValueError("Phone number must be in international E.164 format (e.g. +77011234567)")
        return cleaned

    @field_validator("gmail")
    @classmethod
    def validate_gmail(cls, v: EmailStr) -> str:
        email_str = str(v).strip().lower()
        if not email_str.endswith("@gmail.com"):
            raise ValueError("Email domain must be strictly @gmail.com")
        user_part, domain_part = email_str.split("@", 1)
        if not user_part or domain_part != "gmail.com":
            raise ValueError("Email must be a valid address ending with @gmail.com")
        return email_str


class UserCreate(UserBase):
    """Registration payload for new users."""
    role: UserRole = UserRole.guest
    student_barcode: str | None = None
    steam_id: str | None = None

    @field_validator("student_barcode")
    @classmethod
    def validate_student_barcode(cls, v: str | None) -> str | None:
        if v is None:
            return None
        cleaned = v.strip()
        if not cleaned:
            return None
        if not (cleaned.isdigit() and len(cleaned) == 6):
            raise ValueError("Student barcode must consist of exactly 6 digits")
        return cleaned


class StudentVerifyRequest(BaseModel):
    """Request to initiate student verification by barcode."""
    telegram_id: int
    barcode: str
    email: str | None = None

    @field_validator("barcode")
    @classmethod
    def validate_barcode(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Barcode must be a string")
        cleaned = v.strip()
        if not (cleaned.isdigit() and len(cleaned) == 6):
            raise ValueError("Barcode must consist of exactly 6 digits")
        return cleaned


class OTPConfirmRequest(BaseModel):
    """Request to confirm OTP sent to student email."""
    telegram_id: int
    barcode: str
    otp_code: str

    @field_validator("barcode")
    @classmethod
    def validate_barcode(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Barcode must be a string")
        cleaned = v.strip()
        if not (cleaned.isdigit() and len(cleaned) == 6):
            raise ValueError("Barcode must consist of exactly 6 digits")
        return cleaned

    @field_validator("otp_code")
    @classmethod
    def validate_otp_code(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("OTP code must be a string")
        cleaned = v.strip()
        if not (cleaned.isdigit() and len(cleaned) == 6):
            raise ValueError("OTP code must consist of exactly 6 digits")
        return cleaned


class SteamLinkRequest(BaseModel):
    """Request to link a Steam profile."""
    telegram_id: int
    steam_payload: str

    @field_validator("steam_payload")
    @classmethod
    def validate_steam_payload(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Steam payload must be a string")
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Steam payload cannot be empty")
        return cleaned


class UserResponse(BaseModel):
    """Standard user response."""
    model_config = ConfigDict(from_attributes=True)

    telegram_id: int
    username: str | None = None
    full_name: str | None = None
    phone_number: str | None = None
    gmail: str | None = None
    role: str
    student_barcode: str | None = None
    steam_id: str | None = None
    is_verified: bool = False

    @model_validator(mode="before")
    @classmethod
    def pre_validate(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            email_val = getattr(data, "gmail", None) or getattr(data, "email", None)
            barcode_val = getattr(data, "student_barcode", None) or getattr(data, "barcode", None)
            fname = getattr(data, "full_name", None)
            if not fname:
                first = getattr(data, "first_name", "") or ""
                last = getattr(data, "last_name", "") or ""
                fname = f"{first} {last}".strip() or None
            role_val = getattr(data, "role", "guest")
            if hasattr(role_val, "value"):
                role_val = role_val.value
            return {
                "telegram_id": getattr(data, "telegram_id"),
                "username": getattr(data, "username", None),
                "full_name": fname,
                "phone_number": getattr(data, "phone_number", None),
                "gmail": email_val,
                "role": str(role_val),
                "student_barcode": barcode_val,
                "steam_id": getattr(data, "steam_id", None),
                "is_verified": getattr(data, "is_verified", False),
            }
        return data


class CheckUserResponse(BaseModel):
    """Response for fast user existence check."""
    exists: bool
    user: UserResponse | None = None
