from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.entities import AdminUser


async def require_admin(request: Request, session: AsyncSession = Depends(get_session)) -> AdminUser:
    user_id = request.session.get("admin_id")
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Требуется вход")
    user = await session.scalar(select(AdminUser).where(AdminUser.id == user_id))
    if not user:
        request.session.clear()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Сессия недействительна")
    return user
