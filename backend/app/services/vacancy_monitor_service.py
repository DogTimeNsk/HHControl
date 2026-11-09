from datetime import datetime, timezone
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Resume, VacancyMatch
from app.services.browser_control import BrowserControlClient
from app.core.config import get_settings
from app.services.telegram_bot import TelegramBotError, send_message, vacancy_notification_text


logger = logging.getLogger(__name__)


async def collect_vacancies(
    session: AsyncSession, resume: Resume, client: BrowserControlClient
) -> int:
    """Persist newly seen vacancies from HH's resume-based search."""
    rows = await client.vacancies(resume.hh_resume_id)
    now = datetime.now(timezone.utc)
    new_count = 0
    new_rows: list[dict[str, object]] = []
    for row in rows:
        if not _should_collect_vacancy(row, resume):
            continue
        vacancy_id = str(row["hh_vacancy_id"])
        match = await session.scalar(select(VacancyMatch).where(
            VacancyMatch.resume_id == resume.id,
            VacancyMatch.hh_vacancy_id == vacancy_id,
        ))
        values = _match_values(row, now)
        if match is None:
            session.add(VacancyMatch(resume_id=resume.id, hh_vacancy_id=vacancy_id, parsed_at=now, **values))
            new_count += 1
            new_rows.append(row)
    resume.last_vacancy_check_at = now
    await session.commit()
    await _notify_about_new_vacancies(resume, new_rows)
    return new_count


def _should_collect_vacancy(row: dict[str, object], resume: Resume) -> bool:
    """Apply the optional per-resume response limit before persisting a vacancy."""
    if not resume.vacancy_response_limit_enabled:
        return True
    responses = _optional_int(row.get("total_responses_count"))
    if responses is None:
        responses = _optional_int(row.get("responses_count"))
    return responses is not None and responses < resume.vacancy_response_limit


async def _notify_about_new_vacancies(resume: Resume, rows: list[dict[str, object]]) -> None:
    settings = get_settings()
    if not rows or not resume.vacancy_response_limit_enabled:
        return
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.info("Telegram notifications skipped: bot token or chat ID is not configured")
        return
    for row in rows:
        try:
            await send_message(
                settings.telegram_bot_token,
                settings.telegram_chat_id,
                vacancy_notification_text(resume.title, row),
            )
        except TelegramBotError as exc:
            # The vacancy is already safely stored. A temporary Telegram
            # outage must not make a manual or scheduled collection fail.
            logger.warning("Telegram notification was not sent: resume_id=%s error=%s", resume.id, exc)


def _optional_text(value: object | None) -> str | None:
    return str(value) if value else None


def _optional_int(value: object | None) -> int | None:
    return value if isinstance(value, int) else None


def _optional_bool(value: object | None) -> bool | None:
    return value if isinstance(value, bool) else None


def _object_list(value: object | None) -> list[dict[str, object]]:
    return value if isinstance(value, list) else []


def _object_dict(value: object | None) -> dict[str, object] | None:
    return value if isinstance(value, dict) else None


def _string_list(value: object | None) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def _match_values(row: dict[str, object], now: datetime) -> dict[str, object]:
    return {
        "title": str(row["title"]), "vacancy_url": str(row["vacancy_url"]),
        "employer_name": _optional_text(row.get("employer_name")),
        "employer_url": _optional_text(row.get("employer_url")),
        "salary_from": _optional_int(row.get("salary_from")),
        "salary_to": _optional_int(row.get("salary_to")),
        "salary_currency": _optional_text(row.get("salary_currency")),
        "salary_gross": _optional_bool(row.get("salary_gross")), "city": _optional_text(row.get("city")),
        "responses_count": _optional_int(row.get("responses_count")),
        "total_responses_count": _optional_int(row.get("total_responses_count")),
        "online_users_count": _optional_int(row.get("online_users_count")),
        "user_test_present": _optional_bool(row.get("user_test_present")),
        "user_test_id": _optional_text(row.get("user_test_id")),
        "accept_temporary": _optional_bool(row.get("accept_temporary")),
        "work_formats": _string_list(row.get("work_formats")),
        "company_negative_attributes": _object_dict(row.get("company_negative_attributes")),
        "vacancy_properties": _object_list(row.get("vacancy_properties")), "last_seen_at": now,
    }
