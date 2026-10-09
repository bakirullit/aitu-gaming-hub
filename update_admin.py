import sys
import asyncio
from sqlalchemy import select
from common.database.session import db_manager
from common.models.user import User
from common.enums import UserRole, STAFF_ROLE_TITLES


async def main():
    db_manager.init()
    username_or_id = sys.argv[1] if len(sys.argv) > 1 else "ALG0RITHMs"
    roles_to_assign = sys.argv[2:] if len(sys.argv) > 2 else ["head_admin", "discipline_admin"]

    async with db_manager.session_factory() as session:
        if username_or_id.isdigit():
            stmt = select(User).where(User.telegram_id == int(username_or_id))
        else:
            clean_username = username_or_id.lstrip("@")
            stmt = select(User).where(User.username == clean_username)

        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            user.role = "staff"
            current_roles = list(user.roles or [])
            for r in roles_to_assign:
                clean_r = r.lower().replace(" ", "_")
                if clean_r not in current_roles:
                    current_roles.append(clean_r)
            user.roles = current_roles
            await session.commit()
            print(f"Success! User '{user.username or user.telegram_id}' updated.")
            print(f"Primary role: {user.role}")
            print(f"Assigned staff roles: {user.roles}")
        else:
            print(f"User '{username_or_id}' not found.")


if __name__ == "__main__":
    asyncio.run(main())
