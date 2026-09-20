import logging
from typing import Any
from redis.asyncio import Redis
from sqlalchemy import case, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from common.enums import DisciplineType, UserRole
from common.models.discipline import Discipline, DisciplineTier
from common.models.tournament import DisciplineAdmin
from common.models.user import User

logger = logging.getLogger("services.discipline_service")


class DisciplineService:
    """Service layer managing dynamic esports disciplines and reactive RBAC role transitions."""

    @staticmethod
    async def _invalidate_user_cache(user_id: int, redis: Redis | None) -> None:
        """Clear navigator stack history and interaction lock in Redis without wiping anchor message ID."""
        if redis is None:
            return
        try:
            await redis.delete(
                f"anchor:{user_id}:stack",
                f"anchor:user:{user_id}:stack",
                f"lock:user:{user_id}",
            )
            logger.debug(f"Invalidated Redis navigation stack for user={user_id}")
        except Exception as exc:
            logger.warning(f"Error invalidating Redis cache for user {user_id}: {exc}")

        # Re-render active anchor message in-place if runtime core is available
        try:
            from core.lifespan import runtime
            if runtime.core and runtime.core.navigator:
                anchor_id = await runtime.core.navigator.get_anchor_id(user_id)
                if anchor_id:
                    from plugins.auth.screens import get_welcome_screen
                    from common.database.session import db_manager
                    async with db_manager.session_factory() as s:
                        u = await s.scalar(select(User).where(User.telegram_id == user_id))
                        if u:
                            full_name = f"{u.first_name or ''} {u.last_name or ''}".strip() or (u.username and f"@{u.username}") or "Студент"
                            screen = get_welcome_screen(is_verified=u.is_verified, full_name=full_name)
                            await runtime.core.navigator.render(
                                user_id=user_id,
                                chat_id=user_id,
                                screen=screen,
                                screen_id="home",
                                push_to_history=False,
                            )
        except Exception as exc:
            logger.debug(f"Silent catch re-rendering anchor on role change: {exc}")


    @classmethod
    async def assign_admin(
        cls,
        discipline_slug: str,
        new_admin_id: int | None,
        session: AsyncSession,
        redis: Redis | None = None,
    ) -> Discipline:
        """
        Atomically assigns/reassigns a curator for a discipline, synchronously updating:
        1. disciplines.admin_id
        2. discipline_admins relational table (for tournament wizard zero-input lookup)
        3. Reactive RBAC promotion (STUDENT -> DISCIPLINE_ADMIN)
        4. Reactive RBAC demotion (DISCIPLINE_ADMIN -> STUDENT) with strict HEAD_ADMIN protection
        5. Redis session and navigation stack cache invalidation
        """
        stmt = select(Discipline).where(Discipline.slug == discipline_slug)
        res = await session.execute(stmt)
        discipline = res.scalar_one_or_none()

        if not discipline:
            raise ValueError(f"Discipline with slug '{discipline_slug}' not found.")

        old_admin_id = discipline.admin_id

        # Skip if curator unchanged
        if old_admin_id == new_admin_id:
            return discipline

        discipline.admin_id = new_admin_id

        # Parse discipline enum for sync with discipline_admins table
        disc_enum: DisciplineType | None = None
        try:
            disc_enum = DisciplineType(discipline_slug.upper())
        except ValueError:
            # If not in standard enum, try mapping or OTHER
            disc_enum = DisciplineType.OTHER

        # 1. Atomic sync with discipline_admins table:
        # Delete old curator mapping for this discipline
        if old_admin_id is not None and disc_enum is not None:
            await session.execute(
                delete(DisciplineAdmin).where(
                    DisciplineAdmin.telegram_id == old_admin_id,
                    DisciplineAdmin.discipline == disc_enum,
                )
            )

        # Insert new curator mapping for this discipline
        if new_admin_id is not None and disc_enum is not None:
            existing_da = await session.scalar(
                select(DisciplineAdmin).where(
                    DisciplineAdmin.telegram_id == new_admin_id,
                    DisciplineAdmin.discipline == disc_enum,
                )
            )
            if not existing_da:
                session.add(DisciplineAdmin(telegram_id=new_admin_id, discipline=disc_enum))

        # 2. Reactive Promotion:
        if new_admin_id is not None:
            u_stmt = select(User).where(User.telegram_id == new_admin_id)
            u_res = await session.execute(u_stmt)
            new_user = u_res.scalar_one_or_none()

            if new_user and new_user.role == UserRole.STUDENT:
                logger.info(f"Promoting user {new_admin_id} ({new_user.username}) from STUDENT to DISCIPLINE_ADMIN")
                new_user.role = UserRole.DISCIPLINE_ADMIN

            await cls._invalidate_user_cache(new_admin_id, redis)

        # 3. Reactive Demotion Check:
        if old_admin_id is not None:
            # Count remaining active disciplines curated by old_admin_id
            count_stmt = select(func.count()).where(
                Discipline.admin_id == old_admin_id,
                Discipline.is_active == True,
                Discipline.slug != discipline_slug,
            )
            remaining_disciplines = (await session.scalar(count_stmt)) or 0

            old_u_stmt = select(User).where(User.telegram_id == old_admin_id)
            old_u_res = await session.execute(old_u_stmt)
            old_user = old_u_res.scalar_one_or_none()

            # Strict guard: only DISCIPLINE_ADMIN is demoted. HEAD_ADMIN remains intact under all circumstances!
            if old_user and old_user.role == UserRole.DISCIPLINE_ADMIN and remaining_disciplines == 0:
                logger.info(f"Demoting user {old_admin_id} ({old_user.username}) from DISCIPLINE_ADMIN to STUDENT")
                old_user.role = UserRole.STUDENT

            await cls._invalidate_user_cache(old_admin_id, redis)

        await session.commit()
        await session.refresh(discipline)
        return discipline

    @classmethod
    async def get_all(
        cls,
        session: AsyncSession,
        active_only: bool = False,
    ) -> list[Discipline]:
        """Fetch all disciplines with joined curator user record."""
        stmt = select(Discipline).options(joinedload(Discipline.admin))

        if active_only:
            stmt = stmt.where(Discipline.is_active == True)

        # Order: Major first, then Medium, then alphabetical by name
        stmt = stmt.order_by(
            case((Discipline.tier == DisciplineTier.MAJOR, 0), else_=1),
            Discipline.name.asc(),
        )
        res = await session.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    async def get_by_slug(
        cls,
        slug: str,
        session: AsyncSession,
    ) -> Discipline | None:
        """Fetch single discipline by slug with joined curator."""
        stmt = (
            select(Discipline)
            .options(joinedload(Discipline.admin))
            .where(Discipline.slug == slug)
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    @classmethod
    async def create(
        cls,
        slug: str,
        name: str,
        tier: DisciplineTier,
        description: str,
        chat_url: str,
        admin_id: int | None,
        session: AsyncSession,
        redis: Redis | None = None,
    ) -> Discipline:
        """Create a new discipline and optionally assign an initial curator."""
        clean_slug = slug.strip().lower()
        existing = await cls.get_by_slug(clean_slug, session)
        if existing:
            raise ValueError(f"Discipline with slug '{clean_slug}' already exists.")

        discipline = Discipline(
            slug=clean_slug,
            name=name.strip(),
            tier=tier,
            description=description.strip(),
            chat_url=chat_url.strip(),
            admin_id=None,
            is_active=True,
        )
        session.add(discipline)
        await session.commit()
        await session.refresh(discipline)

        if admin_id is not None:
            discipline = await cls.assign_admin(clean_slug, admin_id, session, redis)

        return discipline

    @classmethod
    async def update(
        cls,
        slug: str,
        session: AsyncSession,
        redis: Redis | None = None,
        **fields: Any,
    ) -> Discipline:
        """Update discipline fields and reassign curator if admin_id changed."""
        discipline = await cls.get_by_slug(slug, session)
        if not discipline:
            raise ValueError(f"Discipline with slug '{slug}' not found.")

        # Reassign admin if passed
        if "admin_id" in fields:
            new_admin_id = fields.pop("admin_id")
            discipline = await cls.assign_admin(slug, new_admin_id, session, redis)

        for key, value in fields.items():
            if value is not None and hasattr(discipline, key):
                setattr(discipline, key, value)

        await session.commit()
        await session.refresh(discipline)
        return discipline

    @classmethod
    async def delete_or_deactivate(
        cls,
        slug: str,
        session: AsyncSession,
        redis: Redis | None = None,
    ) -> Discipline:
        """Soft-deactivates discipline and frees up curator with demotion check."""
        discipline = await cls.get_by_slug(slug, session)
        if not discipline:
            raise ValueError(f"Discipline with slug '{slug}' not found.")

        # If curator was assigned, unassign to trigger demotion check
        if discipline.admin_id is not None:
            await cls.assign_admin(slug, None, session, redis)

        discipline.is_active = False
        await session.commit()
        await session.refresh(discipline)
        return discipline
