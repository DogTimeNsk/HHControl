from typing import Any

import httpx


class TelegramBotError(Exception):
    """Raised when Telegram cannot return bot updates."""


async def recent_chats(token: str) -> list[dict[str, str | int]]:
    """Return unique chats that have sent the bot a recent update.

    The bot token is used only in this server-to-server request and is never
    returned to the client or written to logs.
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"https://api.telegram.org/bot{token}/getUpdates",
                params={"limit": 100, "timeout": 0},
            )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPError as exc:
        raise TelegramBotError("Не удалось связаться с Telegram") from exc
    except ValueError as exc:
        raise TelegramBotError("Telegram вернул некорректный ответ") from exc

    if not payload.get("ok"):
        raise TelegramBotError("Telegram не принял токен бота")

    chats: dict[int, dict[str, str | int]] = {}
    for update in payload.get("result", []):
        if not isinstance(update, dict):
            continue
        for key in ("message", "edited_message", "channel_post", "edited_channel_post"):
            event = update.get(key)
            chat = event.get("chat") if isinstance(event, dict) else None
            if not isinstance(chat, dict) or not isinstance(chat.get("id"), int):
                continue
            chat_id = chat["id"]
            name = chat.get("title") or " ".join(
                part for part in (chat.get("first_name"), chat.get("last_name")) if isinstance(part, str)
            ) or chat.get("username") or "Без названия"
            chats[chat_id] = {
                "id": chat_id,
                "type": str(chat.get("type") or "unknown"),
                "name": str(name),
                "username": str(chat["username"]) if isinstance(chat.get("username"), str) else "",
            }
    return list(chats.values())


def vacancy_notification_text(resume_title: str, vacancy: dict[str, object]) -> str:
    """Build a plain-text notification without Markdown escaping concerns."""
    salary_from = vacancy.get("salary_from")
    salary_to = vacancy.get("salary_to")
    currency = vacancy.get("salary_currency") or ""
    salary_parts = []
    if isinstance(salary_from, int):
        salary_parts.append(f"от {salary_from:,}".replace(",", " "))
    if isinstance(salary_to, int):
        salary_parts.append(f"до {salary_to:,}".replace(",", " "))
    salary = f"{' '.join(salary_parts)} {currency}".strip() if salary_parts else "не указана"
    responses = vacancy.get("total_responses_count")
    if not isinstance(responses, int):
        responses = vacancy.get("responses_count")
    lines = [
        "Новая подходящая вакансия",
        str(vacancy.get("title") or "Без названия"),
        f"Резюме: {resume_title}",
        f"Компания: {vacancy.get('employer_name') or 'не указана'}",
        f"Город: {vacancy.get('city') or 'не указан'}",
        f"Зарплата: {salary}",
        f"Откликов: {responses if isinstance(responses, int) else 'неизвестно'}",
        str(vacancy.get("vacancy_url") or ""),
    ]
    return "\n".join(line for line in lines if line)


async def send_message(token: str, chat_id: str, text: str) -> None:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
            )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPError as exc:
        raise TelegramBotError("Не удалось отправить сообщение в Telegram") from exc
    except ValueError as exc:
        raise TelegramBotError("Telegram вернул некорректный ответ") from exc
    if not payload.get("ok"):
        raise TelegramBotError("Telegram не принял сообщение")
