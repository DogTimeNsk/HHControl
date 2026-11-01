from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import PublishEvent, Resume
from app.services.hh_client import HHClient, HHError
from app.services.resume_service import parse_datetime


async def publish_resume(session: AsyncSession, resume: Resume, client: HHClient) -> PublishEvent:
    now = datetime.now(timezone.utc)
    event = PublishEvent(resume_id=resume.id, started_at=now, operation="publish", result="failed", message="")
    session.add(event)
    resume.last_publish_attempt_at = now
    try:
        status = await client.resume_status(resume.hh_resume_id)
        resume.last_checked_at = now
        resume.status = (status.get("status") or {}).get("id")
        resume.next_publish_at = parse_datetime(status.get("next_publish_at"))
        if not status.get("can_publish_or_update", False):
            event.result, event.message = "skipped", "Публикация пока недоступна в HH"
        else:
            event.http_status = await client.publish(resume.hh_resume_id)
            event.result, event.message = "success", "Резюме опубликовано или обновлено"
            resume.last_success_at, resume.last_error = now, None
    except HHError as exc:
        event.http_status, event.message, resume.last_error = exc.status_code, str(exc), str(exc)
    event.finished_at = datetime.now(timezone.utc)
    await session.commit()
    return event
