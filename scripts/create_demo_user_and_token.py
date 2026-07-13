"""
Creates a demo User + Farm directly in the real database and prints a valid
JWT bearer token, bypassing /auth/register and /auth/login - those still use
a separate, disconnected auth stack (PyJWT + app.db_config + Universe B
models) that doesn't mint tokens app.auth.get_current_user can validate.
This is a known, documented gap, not something this script works around
silently - see the drone pipeline plan for the full explanation.

Usage:
    python scripts/create_demo_user_and_token.py
"""

import asyncio
import sys

sys.path.insert(0, ".")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.database import engine
from app.models.user import Farm, User
from app.auth import create_access_token, pwd_context


async def main():
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        result = await db.execute(select(User).where(User.phone_number == "+254700000000"))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                phone_number="+254700000000",
                email="demo-farmer@example.com",
                full_name="Demo Farmer",
                hashed_password=pwd_context.hash("demo-password"),
                role="farmer",
                is_active=True,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            print(f"Created user id={user.id}")
        else:
            print(f"Using existing user id={user.id}")

        result = await db.execute(select(Farm).where(Farm.owner_id == user.id))
        farm = result.scalars().first()
        if farm is None:
            farm = Farm(
                owner_id=user.id,
                name="Demo Orchard",
                latitude=-35.363261,
                longitude=149.165230,
                size_acres=5.0,
                crop_type="mango",
            )
            db.add(farm)
            await db.commit()
            await db.refresh(farm)
            print(f"Created farm id={farm.id}")
        else:
            print(f"Using existing farm id={farm.id}")

    token = create_access_token({"sub": str(user.id)})
    print("\n--- Use these in your requests ---")
    print(f"farm_id: {farm.id}")
    print(f"Authorization: Bearer {token}")


if __name__ == "__main__":
    asyncio.run(main())
