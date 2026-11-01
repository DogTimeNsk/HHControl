from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models.entities import Resume
from app.services.resume_service import sync_resumes


@pytest.mark.asyncio
async def test_sync_adds_resumes_disabled_by_default() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        rows = await sync_resumes(session, [{"id": "hh-1", "title": "Python", "updated_at": "2026-01-01T12:00:00+0300"}])
        assert len(rows) == 1
        assert rows[0].enabled is False
        assert rows[0].published_at == datetime(2026, 1, 1, 9, tzinfo=timezone.utc)
    await engine.dispose()
