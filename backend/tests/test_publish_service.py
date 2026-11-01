from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models.entities import Resume
from app.services.publish_service import publish_resume


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as value:
        resume = Resume(hh_resume_id="hh-1", title="Test", enabled=True, created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
        value.add(resume)
        await value.commit()
        yield value, resume
    await engine.dispose()


@pytest.mark.asyncio
async def test_publish_is_skipped_when_hh_disallows_it(session) -> None:
    db, resume = session
    client = AsyncMock()
    client.resume_status.return_value = {"can_publish_or_update": False, "status": {"id": "published"}}
    event = await publish_resume(db, resume, client)
    assert event.result == "skipped"
    client.publish.assert_not_awaited()


@pytest.mark.asyncio
async def test_publish_records_success(session) -> None:
    db, resume = session
    client = AsyncMock()
    client.resume_status.return_value = {"can_publish_or_update": True, "status": {"id": "published"}}
    client.publish.return_value = 204
    event = await publish_resume(db, resume, client)
    assert event.result == "success"
    assert event.http_status == 204
    client.publish.assert_awaited_once_with("hh-1")
