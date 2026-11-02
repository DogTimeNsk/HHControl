from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Resume, VacancyMatch
from app.services.browser_control import BrowserControlClient


async def collect_vacancies(
    session: AsyncSession, resume: Resume, client: BrowserControlClient
) -> int:
    """Persist newly seen vacancies from HH's resume-based search."""
    rows = await client.vacancies(resume.hh_resume_id)
    now = datetime.now(timezone.utc)
    new_count = 0
    for row in rows:
        vacancy_id = str(row["hh_vacancy_id"])
        match = await session.scalar(select(VacancyMatch).where(VacancyMatch.hh_vacancy_id == vacancy_id))
        values = _match_values(row, now)
        if match is None:
            session.add(VacancyMatch(resume_id=resume.id, hh_vacancy_id=vacancy_id, parsed_at=now, **values))
            new_count += 1
        else:
            for key, value in values.items():
                setattr(match, key, value)
    resume.last_vacancy_check_at = now
    await session.commit()
    return new_count


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
