from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from common.dtos.events import StaffPreCreatedEvent, UserRoleRevealedEvent
from common.enums import STAFF_ROLE_TITLES, StaffRole
from common.models.pending_staff import PendingStaffMember
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

    async def precreate_staff_member(
        self,
        first_name: str,
        last_name: str,
        staff_role: StaffRole,
        academic_group: str | None = None,
        barcode: str | None = None,
        email: str | None = None,
        corp_email: str | None = None,
        phone_number: str | None = None,
        username: str | None = None,
        discipline_id: str | None = None,
    ) -> PendingStaffMember:
        """
        Pre-creates a pending staff member profile.
        If user is already registered in users table, attaches role directly.
        """
        clean_username = username.lstrip("@").strip().lower() if username else None
        clean_email = email.strip().lower() if email else None
        clean_corp_email = corp_email.strip().lower() if corp_email else None
        clean_barcode = barcode.strip() if barcode else None

        # Check uniqueness across pending_staff_members
        if clean_barcode:
            stmt = select(PendingStaffMember).where(PendingStaffMember.barcode == clean_barcode)
            if (await self.session.execute(stmt)).scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Pending member with barcode '{clean_barcode}' already exists.",
                )

        if clean_email:
            stmt = select(PendingStaffMember).where(PendingStaffMember.email == clean_email)
            if (await self.session.execute(stmt)).scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Pending member with email '{clean_email}' already exists.",
                )

        if clean_corp_email:
            stmt = select(PendingStaffMember).where(PendingStaffMember.corp_email == clean_corp_email)
            if (await self.session.execute(stmt)).scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Pending member with corporate email '{clean_corp_email}' already exists.",
                )

        if clean_username:
            stmt = select(PendingStaffMember).where(func.lower(PendingStaffMember.username) == clean_username)
            if (await self.session.execute(stmt)).scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Pending member with username '@{clean_username}' already exists.",
                )

        # Check if user already exists in users table
        existing_user: User | None = None
        user_conds = []
        if clean_barcode:
            user_conds.append(User.barcode == clean_barcode)
        if clean_email:
            user_conds.append(func.lower(User.email) == clean_email)
        if clean_corp_email:
            user_conds.append(func.lower(User.email) == clean_corp_email)
        if clean_username:
            user_conds.append(func.lower(User.username) == clean_username)

        if user_conds:
            stmt_user = select(User).where(or_(*user_conds))
            existing_user = (await self.session.execute(stmt_user)).scalars().first()

        if existing_user:
            existing_user.staff_role = staff_role
            existing_user.discipline_id = discipline_id
            existing_user.is_role_revealed = False
            await self.session.commit()
            await self.session.refresh(existing_user)
            logger.info(
                f"Directly linked pending staff role {staff_role} (discipline={discipline_id}) "
                f"to existing user telegram_id={existing_user.telegram_id}"
            )

        pending = PendingStaffMember(
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            academic_group=academic_group.strip() if academic_group else None,
            barcode=clean_barcode,
            email=clean_email,
            corp_email=clean_corp_email,
            phone_number=phone_number.strip() if phone_number else None,
            username=clean_username,
            staff_role=staff_role,
            discipline_id=discipline_id,
        )

        if not existing_user:
            self.session.add(pending)
            await self.session.commit()
            await self.session.refresh(pending)
            logger.info(f"Created PendingStaffMember id={pending.id} for {first_name} {last_name}")

        await self._publish_event(
            StaffPreCreatedEvent(
                pending_id=pending.id if not existing_user else 0,
                first_name=first_name,
                last_name=last_name,
                staff_role=staff_role.value if hasattr(staff_role, "value") else str(staff_role),
                discipline_id=discipline_id,
            )
        )
        return pending

    async def claim_pending_role_if_exists(self, user: User) -> bool:
        """
        Searches pending_staff_members matching user by username, barcode, email, or corp_email.
        If found, transfers staff_role and discipline_id to user, sets is_role_revealed=False,
        removes the pending record, and commits.
        """
        conditions = []
        if user.username:
            clean_user_tag = user.username.lstrip("@").strip().lower()
            conditions.append(func.lower(PendingStaffMember.username) == clean_user_tag)
        if user.barcode:
            conditions.append(PendingStaffMember.barcode == user.barcode.strip())
        if user.email:
            clean_email = user.email.strip().lower()
            conditions.append(func.lower(PendingStaffMember.email) == clean_email)
            conditions.append(func.lower(PendingStaffMember.corp_email) == clean_email)

        if not conditions:
            return False

        stmt = select(PendingStaffMember).where(or_(*conditions))
        result = await self.session.execute(stmt)
        pending = result.scalars().first()

        if not pending:
            return False

        user.staff_role = pending.staff_role
        user.discipline_id = pending.discipline_id
        user.is_role_revealed = False

        await self.session.delete(pending)
        await self.session.commit()
        await self.session.refresh(user)
        logger.info(
            f"Claimed pending staff role {user.staff_role} (discipline={user.discipline_id}) "
            f"for user telegram_id={user.telegram_id}"
        )
        return True

    async def reveal_role(self, telegram_id: int) -> tuple[User, str, str | None]:
        """
        Reveals the assigned staff role for the user, sets is_role_revealed=True and role_revealed_at,
        dispatches UserRoleRevealedEvent, and returns (user, localized_title, discipline_name).
        """
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with Telegram ID {telegram_id} not found.",
            )

        if not user.is_role_revealed:
            user.is_role_revealed = True
            user.role_revealed_at = datetime.now(timezone.utc)
            await self.session.commit()
            await self.session.refresh(user)

        role_key = (
            user.staff_role.value if hasattr(user.staff_role, "value") else str(user.staff_role)
        ).lower()
        role_title = STAFF_ROLE_TITLES.get(role_key, role_key.title())

        discipline_name = None
        if user.discipline_id:
            from common.models.discipline import Discipline
            disc_res = await self.session.execute(select(Discipline.name).where(Discipline.slug == user.discipline_id))
            discipline_name = disc_res.scalar_one_or_none() or user.discipline_id

        await self._publish_event(
            UserRoleRevealedEvent(
                user_id=user.telegram_id,
                telegram_id=user.telegram_id,
                staff_role=role_key,
                discipline_id=user.discipline_id,
            )
        )
        logger.info(f"User {telegram_id} revealed staff role: {role_title} ({discipline_name})")
        return user, role_title, discipline_name

    async def _publish_event(self, event: Any) -> None:
        try:
            from core.lifespan import runtime
            if runtime.core and runtime.core.event_bus:
                await runtime.core.event_bus.publish(event)
        except Exception as exc:
            logger.warning(f"Could not publish domain event {event}: {exc}")

