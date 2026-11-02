from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.api.routes import check_ats
from app.models.entities import Resume


@pytest.mark.asyncio
async def test_ats_check_persists_achievements_marker(monkeypatch) -> None:
    resume = Resume(
        id=7,
        hh_resume_id="hh-7",
        title="Test",
        enabled=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session = AsyncMock()
    session.get.side_effect = [resume, object()]

    class BrowserClient:
        def __init__(self, _settings) -> None:
            pass

        async def ats_check(self, resume_id: str) -> bool:
            assert resume_id == "hh-7"
            return True

    monkeypatch.setattr("app.api.routes.BrowserControlClient", BrowserClient)

    result = await check_ats(resume.id, None, session)  # type: ignore[arg-type]

    assert result is resume
    assert resume.ats_achievements is True
    assert resume.ats_checked_at is not None
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(resume)
