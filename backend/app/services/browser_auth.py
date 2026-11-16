"""Browser-session authorization checks and their critical notification."""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.entities import AppSetting
from app.services.browser_control import BrowserControlClient
from app.services.telegram_bot import TelegramBotError, send_message


logger = logging.getLogger(__name__)
_EXPIRED_NOTIFICATION_KEY = "browser_auth_expired_notified"
_EXPIRED_MESSAGE = (
    "Критично: сессия hh.ru в браузере истекла. Автоматическое обновление резюме "
    "и сбор вакансий остановлены. Откройте «Войти в hh.ru», завершите вход в noVNC "
    "и нажмите «Сохранить сессию»."
)


class BrowserSessionExpired(Exception):
    """Raised after an HH login redirect and, at most once, a Telegram alert."""


async def require_browser_authorization(session: AsyncSession, client: BrowserControlClient) -> None:
    """Require the HH browser session and notify once during each expired period."""
    if await client.authenticated():
        marker = await session.get(AppSetting, _EXPIRED_NOTIFICATION_KEY)
        if marker:
            await session.delete(marker)
            await session.commit()
        return

    await _notify_expired_session_once(session)
    raise BrowserSessionExpired("Сессия hh.ru истекла: войдите в hh.ru через noVNC и сохраните сессию")


async def _notify_expired_session_once(session: AsyncSession) -> None:
    if await session.get(AppSetting, _EXPIRED_NOTIFICATION_KEY):
        return
    settings = get_settings()
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.warning("HH browser session expired, but Telegram notifications are not configured")
        return

    # Persist before delivery so repeated scheduler runs cannot flood Telegram
    # while the user has not restored the browser session.
    session.add(AppSetting(key=_EXPIRED_NOTIFICATION_KEY, value="1"))
    await session.commit()
    try:
        await send_message(settings.telegram_bot_token, settings.telegram_chat_id, _EXPIRED_MESSAGE)
    except TelegramBotError as exc:
        logger.warning("HH browser-session expiration notification was not sent: %s", exc)
