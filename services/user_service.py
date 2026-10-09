from __future__ import annotations

import logging
from typing import Any
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from common.models.user import User
from schemas.user import UserCreate, UserRole

logger = logging.getLogger("services.user_service")


class UserService:
    """Service handling user registration, lifecycle, and profile linking."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Fetch a user by their unique Telegram ID."""
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def register_user(self, data: UserCreate) -> User:
        """
        Register a new user in PostgreSQL.
        Validates telegram_id, gmail, barcode, and steam_id uniqueness.
        """
        # 1. Check telegram_id uniqueness
        existing_user = await self.get_by_telegram_id(data.telegram_id)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with Telegram ID {data.telegram_id} is already registered.",
            )

        # 2. Check gmail uniqueness
        stmt_email = select(User).where(
            or_(User.email == data.gmail, User.gmail == data.gmail)
        )
        existing_email = (await self.session.execute(stmt_email)).scalar_one_or_none()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with email '{data.gmail}' is already registered.",
            )

        # 3. Check student_barcode uniqueness if supplied
        if data.student_barcode:
            stmt_barcode = select(User).where(
                or_(User.barcode == data.student_barcode, User.student_barcode == data.student_barcode)
            )
            existing_barcode = (await self.session.execute(stmt_barcode)).scalar_one_or_none()
            if existing_barcode:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Barcode '{data.student_barcode}' is already registered to another user.",
                )

        # 4. Check steam_id uniqueness if supplied
        if data.steam_id:
            stmt_steam = select(User).where(User.steam_id == data.steam_id)
            existing_steam = (await self.session.execute(stmt_steam)).scalar_one_or_none()
            if existing_steam:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Steam ID '{data.steam_id}' is already linked to another account.",
                )

        # 5. Extract first and last name from full_name
        parts = data.full_name.strip().split(maxsplit=1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""

        role_str = data.role.value if hasattr(data.role, "value") else str(data.role)
        is_verified = (role_str == UserRole.student.value)

        user = User(
            telegram_id=data.telegram_id,
            username=data.username,
            full_name=data.full_name,
            first_name=first_name,
            last_name=last_name,
            phone_number=data.phone_number,
            email=data.gmail,
            role=role_str,
            barcode=data.student_barcode,
            steam_id=data.steam_id,
            is_verified=is_verified,
        )

        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        logger.info(f"Registered user telegram_id={user.telegram_id} role={user.role}")
        return user

    async def promote_to_student(self, telegram_id: int, barcode: str) -> User:
        """
        Promote an existing user to student status and link student barcode.
        """
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with Telegram ID {telegram_id} not found.",
            )

        # Verify barcode is not taken by another user
        stmt = select(User).where(
            or_(User.barcode == barcode, User.student_barcode == barcode),
            User.telegram_id != telegram_id,
        )
        existing_other = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing_other:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Student barcode '{barcode}' is already linked to another account.",
            )

        user.role = UserRole.student.value if hasattr(UserRole.student, "value") else "student"
        user.barcode = barcode
        user.is_verified = True

        await self.session.commit()
        await self.session.refresh(user)
        logger.info(f"Promoted user {telegram_id} to student with barcode {barcode}")
        return user

    async def attach_steam(self, telegram_id: int, steam_id: str) -> User:
        """
        Link Steam ID to user profile and elevate guest to verified_guest.
        """
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with Telegram ID {telegram_id} not found.",
            )

        # Check steam_id uniqueness across other users
        stmt = select(User).where(
            User.steam_id == steam_id,
            User.telegram_id != telegram_id,
        )
        existing_steam = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing_steam:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Steam ID '{steam_id}' is already linked to another account.",
            )

        user.steam_id = steam_id
        current_role = user.role.value if hasattr(user.role, "value") else str(user.role)
        if current_role == UserRole.guest.value:
            user.role = UserRole.verified_guest.value

        from common.models.tournament import TournamentBooking
        from sqlalchemy import update
        await self.session.execute(
            update(TournamentBooking)
            .where(TournamentBooking.creator_id == telegram_id)
            .values(creator_steam_id=steam_id)
        )

        await self.session.commit()
        await self.session.refresh(user)
        logger.info(f"Linked steam_id={steam_id} to user telegram_id={telegram_id}, new role={user.role}")
        return user

    async def delete_user_account(self, telegram_id: int) -> dict[str, Any] | None:
        """
        Deletes the user account permanently while preserving their tournament records
        linked to their Steam ID.
        """
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return None

        steam_id = user.steam_id

        # 1. Preserve tournament bookings on their Steam ID and detach creator_id
        from common.models.tournament import TournamentBooking
        from sqlalchemy import update
        await self.session.execute(
            update(TournamentBooking)
            .where(TournamentBooking.creator_id == telegram_id)
            .values(creator_steam_id=steam_id, creator_id=None)
        )

        # 2. Delete user entity (cascades to tickets, discipline_admins, whitelist)
        await self.session.delete(user)
        await self.session.commit()
        logger.info(
            f"Permanently deleted user telegram_id={telegram_id}, "
            f"tournaments preserved for steam_id={steam_id}"
        )

        return {
            "deleted": True,
            "telegram_id": telegram_id,
            "steam_id": steam_id,
        }

