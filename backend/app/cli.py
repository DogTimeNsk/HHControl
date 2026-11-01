import asyncio
import getpass
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.entities import AdminUser


async def create_admin() -> None:
    settings = get_settings()
    password = getpass.getpass("Пароль для admin: ")
    confirmation = getpass.getpass("Повторите пароль: ")
    if len(password) < 12:
        raise SystemExit("Пароль должен содержать не менее 12 символов")
    if password != confirmation:
        raise SystemExit("Пароли не совпадают")
    async with SessionLocal() as session:
        user = await session.scalar(select(AdminUser).where(AdminUser.username == settings.admin_username))
        if user:
            user.password_hash = hash_password(password)
            print("Пароль администратора обновлён.")
        else:
            session.add(AdminUser(username=settings.admin_username, password_hash=hash_password(password),
                                  created_at=datetime.now(timezone.utc)))
            print("Учётная запись администратора создана.")
        await session.commit()


if __name__ == "__main__":
    asyncio.run(create_admin())
