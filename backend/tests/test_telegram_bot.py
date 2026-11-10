from unittest.mock import AsyncMock, Mock

import pytest

from app.services.telegram_bot import recent_chats, vacancy_notification_text


@pytest.mark.asyncio
async def test_recent_chats_returns_unique_chats(monkeypatch) -> None:
    response = Mock()
    response.json.return_value = {
        "ok": True,
        "result": [
            {"message": {"chat": {"id": 10, "type": "private", "first_name": "Linas"}}},
            {"channel_post": {"chat": {"id": -20, "type": "group", "title": "Jobs"}}},
            {"edited_message": {"chat": {"id": 10, "type": "private", "first_name": "Linas"}}},
        ],
    }

    client = AsyncMock()
    client.get.return_value = response
    client.__aenter__.return_value = client
    monkeypatch.setattr("app.services.telegram_bot.httpx.AsyncClient", lambda **_: client)

    assert await recent_chats("secret") == [
        {"id": 10, "type": "private", "name": "Linas", "username": ""},
        {"id": -20, "type": "group", "name": "Jobs", "username": ""},
    ]


def test_vacancy_notification_includes_useful_details() -> None:
    text = vacancy_notification_text("Python resume", {
        "title": "Data Engineer", "employer_name": "Acme", "city": "Москва",
        "salary_from": 100_000, "salary_currency": "RUB", "total_responses_count": 12,
        "vacancy_url": "https://hh.ru/vacancy/1",
    })

    assert "Data Engineer" in text
    assert "Резюме: Python resume" in text
    assert "Откликов: 12" in text
    assert "https://hh.ru/vacancy/1" in text
