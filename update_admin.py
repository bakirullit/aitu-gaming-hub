import asyncio
from common.database.session import db_manager
from common.models.user import User
from common.enums import UserRole
from sqlalchemy import select

async def main():
    db_manager.init()
    async with db_manager.session_factory() as session:
        stmt = select(User).where(User.username == "ALG0RITHMs")
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            user.role = UserRole.HEAD_ADMIN
            await session.commit()
            print(f"Success! {user.username} is now HEAD_ADMIN.")
        else:
            print("User not found.")

asyncio.run(main())
