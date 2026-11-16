from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models.entities import AppSetting
from app.services.browser_auth import BrowserSessionExpired, require_browser_authorization


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as value:
        yield value
    await engine.dispose()


@pytest.mark.asyncio
async def test_expired_browser_session_notifies_only_once(monkeypatch, session) -> None:
    client = AsyncMock()
    client.authenticated.return_value = False
    sent = AsyncMock()
    monkeypatch.setattr("app.services.browser_auth.send_message", sent)
    monkeypatch.setattr("app.services.browser_auth.get_settings", lambda: type("Settings", (), {
        "telegram_bot_token": "token", "telegram_chat_id": "chat"
    })())

    with pytest.raises(BrowserSessionExpired):
        await require_browser_authorization(session, client)
    with pytest.raises(BrowserSessionExpired):
        await require_browser_authorization(session, client)

    sent.assert_awaited_once()
    assert await session.get(AppSetting, "browser_auth_expired_notified") is not None


@pytest.mark.asyncio
async def test_valid_browser_session_clears_expiration_marker(session) -> None:
    session.add(AppSetting(key="browser_auth_expired_notified", value="1"))
    await session.commit()
    client = AsyncMock()
    client.authenticated.return_value = True

    await require_browser_authorization(session, client)

    assert await session.get(AppSetting, "browser_auth_expired_notified") is None
