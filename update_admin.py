#!/usr/bin/env python3
import sys
import os
import socket
import asyncio
from sqlalchemy import select
from common.config import settings
from common.database.session import DatabaseSessionManager
from common.models.user import User
from common.enums import UserRole, STAFF_ROLE_TITLES


def get_resolved_db_manager() -> DatabaseSessionManager:
    """Returns a DatabaseSessionManager, falling back to localhost:5432 if run outside Docker."""
    db_url = os.getenv("DATABASE_URL") or settings.DATABASE_URL
    if "@postgres:" in db_url:
        try:
            socket.gethostbyname("postgres")
        except socket.gaierror:
            # Running on host outside docker network -> map to exposed port 5432
            db_url = db_url.replace("@postgres:", "@127.0.0.1:")
    
    manager = DatabaseSessionManager(db_url=db_url)
    manager.init()
    return manager


async def main():
    manager = get_resolved_db_manager()
    username_or_id = sys.argv[1] if len(sys.argv) > 1 else "ALG0RITHMs"
    roles_to_assign = sys.argv[2:] if len(sys.argv) > 2 else ["head_admin", "discipline_admin"]

    async with manager.session_factory() as session:
        if username_or_id.isdigit():
            stmt = select(User).where(User.telegram_id == int(username_or_id))
        else:
            clean_username = username_or_id.lstrip("@")
            stmt = select(User).where(User.username.ilike(clean_username))

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
            print("==================================================")
            print(f"✅ Success! Admin rights granted to: @{user.username or user.telegram_id}")
            print(f"• Telegram ID: {user.telegram_id}")
            print(f"• Full Name:   {user.full_name or '—'}")
            print(f"• Base Role:   {user.role} (Staff AITU Gaming 🛡️)")
            print(f"• RBAC Roles:  {user.roles}")
            print("==================================================")
        else:
            print(f"❌ User '{username_or_id}' not found in database.")

    await manager.close()


if __name__ == "__main__":
    asyncio.run(main())
