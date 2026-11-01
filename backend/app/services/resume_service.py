from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Resume
from app.browser.parsing import RESUME_ID_RE


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


async def sync_resumes(session: AsyncSession, items: list[dict[str, Any]]) -> list[Resume]:
    existing = {resume.hh_resume_id: resume for resume in (await session.scalars(select(Resume))).all()}
    now = datetime.now(timezone.utc)
    result: list[Resume] = []
    for item in items:
        hh_id = str(item["id"])
        resume = existing.get(hh_id)
        if resume is None:
            resume = Resume(hh_resume_id=hh_id, title=item.get("title", "Без названия"), enabled=False,
                            managed=True, created_at=now, updated_at=now)
            session.add(resume)
        else:
            resume.title = item.get("title", resume.title)
            resume.managed = True
            resume.updated_at = now
        resume.published_at = parse_datetime(item.get("updated_at") or item.get("published_at"))
        resume.next_publish_at = parse_datetime(item.get("next_publish_at"))
        result.append(resume)
    # Clean up historical scraper artifacts such as the /resume/edit route,
    # without deleting their audit history.
    for resume in existing.values():
        if not RESUME_ID_RE.fullmatch(resume.hh_resume_id):
            resume.managed = False
            resume.enabled = False
    await session.commit()
    return result
