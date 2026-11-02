from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models.entities import Resume, VacancyMatch
from app.services.vacancy_monitor_service import collect_vacancies


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
    assert await collect_vacancies(db, resume, client) == 0
    matches = (await db.scalars(select(VacancyMatch))).all()
    assert len(matches) == 1
    assert matches[0].salary_to == 150_000
    assert resume.last_vacancy_check_at is not None
