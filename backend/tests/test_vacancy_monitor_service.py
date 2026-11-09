from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models.entities import Resume, VacancyMatch
from app.services.vacancy_monitor_service import _should_collect_vacancy, collect_vacancies


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as value:
        resume = Resume(hh_resume_id="hh-1", title="Test", enabled=False, managed=True,
                        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
        value.add(resume)
        await value.commit()
        yield value, resume
    await engine.dispose()


@pytest.mark.asyncio
async def test_collect_vacancies_only_persists_new_hh_ids(session) -> None:
    db, resume = session
    client = AsyncMock()
    client.vacancies.return_value = [{
        "hh_vacancy_id": "123", "title": "Python developer",
        "vacancy_url": "https://hh.ru/vacancy/123", "employer_name": "Company",
        "employer_url": "https://hh.ru/employer/1", "salary_from": 100_000,
        "salary_to": 150_000, "salary_currency": "RUB", "city": "Москва",
    }]

    assert await collect_vacancies(db, resume, client) == 1
    client.vacancies.return_value[0]["salary_to"] = 999_999
    assert await collect_vacancies(db, resume, client) == 0
    matches = (await db.scalars(select(VacancyMatch))).all()
    assert len(matches) == 1
    assert matches[0].salary_to == 150_000
    assert resume.last_vacancy_check_at is not None


@pytest.mark.asyncio
async def test_collect_vacancies_respects_per_resume_response_limit(session) -> None:
    db, resume = session
    resume.vacancy_response_limit_enabled = True
    resume.vacancy_response_limit = 30
    client = AsyncMock()
    client.vacancies.return_value = [
        {"hh_vacancy_id": "under", "title": "Under limit", "vacancy_url": "https://hh.ru/vacancy/under", "total_responses_count": 29},
        {"hh_vacancy_id": "at", "title": "At limit", "vacancy_url": "https://hh.ru/vacancy/at", "total_responses_count": 30},
        {"hh_vacancy_id": "unknown", "title": "Unknown", "vacancy_url": "https://hh.ru/vacancy/unknown"},
    ]

    assert await collect_vacancies(db, resume, client) == 1
    matches = (await db.scalars(select(VacancyMatch))).all()
    assert [match.hh_vacancy_id for match in matches] == ["under"]
    assert _should_collect_vacancy({"responses_count": 29, "total_responses_count": 30}, resume) is False


@pytest.mark.asyncio
async def test_collect_vacancies_allows_the_same_vacancy_for_each_resume(session) -> None:
    db, resume = session
    second_resume = Resume(
        hh_resume_id="hh-2", title="Second", enabled=False, managed=True,
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
    )
    db.add(second_resume)
    await db.commit()
    client = AsyncMock()
    client.vacancies.return_value = [{
        "hh_vacancy_id": "123", "title": "Python developer", "vacancy_url": "https://hh.ru/vacancy/123",
    }]

    assert await collect_vacancies(db, resume, client) == 1
    assert await collect_vacancies(db, second_resume, client) == 1
    matches = (await db.scalars(select(VacancyMatch).order_by(VacancyMatch.resume_id))).all()
    assert [(match.resume_id, match.hh_vacancy_id) for match in matches] == [
        (resume.id, "123"), (second_resume.id, "123"),
    ]
