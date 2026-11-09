import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text

from app.api.routes import hh_client
from app.core.config import get_settings
from app.core.security import as_utc, lock_until
from app.db.session import SessionLocal
from app.models.entities import AppSetting, BrowserCredential, PublishEvent, Resume
from app.services.browser_control import BrowserControlClient, BrowserControlError
from app.services.publish_service import publish_resume
from app.services.resume_service import parse_datetime
from app.services.vacancy_monitor_service import collect_vacancies

logger = logging.getLogger(__name__)


async def acquire_lock() -> bool:
    now, until = datetime.now(timezone.utc), lock_until()
    async with SessionLocal() as session:
        setting = await session.get(AppSetting, "scheduler_lock")
        if setting is None:
            session.add(AppSetting(key="scheduler_lock", value=until.isoformat()))
            await session.commit()
            return True
        result = await session.execute(text("UPDATE app_settings SET value=:until WHERE key='scheduler_lock' AND value < :now"),
                                       {"until": until.isoformat(), "now": now.isoformat()})
        await session.commit()
        return result.rowcount == 1


async def release_lock() -> None:
    async with SessionLocal() as session:
        setting = await session.get(AppSetting, "scheduler_lock")
        if setting:
            setting.value = datetime.now(timezone.utc).isoformat()
            await session.commit()


async def acquire_lock_with_wait(wait_seconds: int) -> float | None:
    """Serialize browser work without silently dropping a scheduled publish."""
    started = datetime.now(timezone.utc)
    while True:
        if await acquire_lock():
            return (datetime.now(timezone.utc) - started).total_seconds()
        if (datetime.now(timezone.utc) - started).total_seconds() >= wait_seconds:
            return None
        await asyncio.sleep(2)


def resume_is_due(resume: Resume, now: datetime, unknown_interval_minutes: int) -> bool:
    if resume.next_publish_at:
        return as_utc(resume.next_publish_at) <= now
    if resume.last_checked_at is None:
        return True
    return as_utc(resume.last_checked_at) <= now - timedelta(minutes=unknown_interval_minutes)


def add_scheduler_event(session, resume: Resume, now: datetime, result: str, message: str) -> None:
    session.add(PublishEvent(resume_id=resume.id, started_at=now, finished_at=now,
                             operation="scheduler", result=result, http_status=None, message=message))


async def run_scheduled_publish() -> dict[str, int | str]:
    settings = get_settings()
    waited_seconds = await acquire_lock_with_wait(settings.scheduler_lock_wait_seconds)
    if waited_seconds is None:
        logger.warning("Scheduled publication gave up after waiting %s seconds for browser lock", settings.scheduler_lock_wait_seconds)
        return {"status": "deferred", "processed": 0}
    try:
        async with SessionLocal() as session:
            now = datetime.now(timezone.utc)
            all_resumes = (await session.scalars(select(Resume).where(
                Resume.enabled.is_(True), Resume.managed.is_(True)
            ))).all()
            resumes = [resume for resume in all_resumes if resume_is_due(
                resume, now, settings.unknown_publish_check_interval_minutes
            )]
            logger.info("Scheduled publication: due=%s deferred=%s waited=%.1fs", len(resumes),
                        len(all_resumes) - len(resumes), waited_seconds)
            if waited_seconds >= 5:
                for resume in resumes:
                    add_scheduler_event(session, resume, now, "deferred",
                                        f"Ожидание browser session: {waited_seconds:.0f} сек.")
            browser_mode = bool(await session.get(BrowserCredential, 1))
            client = None if browser_mode else await hh_client(session)
            for resume in resumes:
                if browser_mode:
                    attempt_at = datetime.now(timezone.utc)
                    try:
                        result = await BrowserControlClient(settings).publish(resume.hh_resume_id)
                        event = PublishEvent(resume_id=resume.id, started_at=attempt_at, finished_at=attempt_at, operation="publish", result=result["result"], http_status=None, message=result["message"])
                        resume.last_checked_at = attempt_at
                        resume.next_publish_at = parse_datetime(result.get("next_publish_at"))
                        resume.publish_available = result.get("can_publish") if isinstance(result.get("can_publish"), bool) else None
                        if result["result"] == "success":
                            resume.last_success_at, resume.last_error = attempt_at, None
                        if resume.next_publish_at:
                            add_scheduler_event(session, resume, attempt_at, "scheduled",
                                                f"HH назначил следующую проверку: {resume.next_publish_at.isoformat()}")
                    except BrowserControlError as exc:
                        event = PublishEvent(resume_id=resume.id, started_at=attempt_at, finished_at=datetime.now(timezone.utc), operation="publish", result="failed", http_status=None, message=str(exc))
                        resume.last_error = str(exc)
                    session.add(event)
                    resume.last_publish_attempt_at = attempt_at
                    await session.commit()
                else:
                    await publish_resume(session, resume, client)
            return {"status": "completed", "processed": len(resumes)}
    finally:
        await release_lock()


async def run_scheduled_vacancy_collection() -> dict[str, int | str]:
    """Run the hourly resume-based vacancy search when a browser session exists."""
    if not await acquire_lock():
        return {"status": "already_running", "processed": 0}
    try:
        async with SessionLocal() as session:
            if not await session.get(BrowserCredential, 1):
                return {"status": "browser_session_required", "processed": 0}
            resumes = (await session.scalars(select(Resume).where(
                Resume.vacancy_monitoring_enabled.is_(True), Resume.managed.is_(True)
            ))).all()
            client = BrowserControlClient(get_settings())
            processed = 0
            for resume in resumes:
                try:
                    await collect_vacancies(session, resume, client)
                    processed += 1
                except BrowserControlError as exc:
                    resume.last_error = str(exc)
                    await session.commit()
            return {"status": "completed", "processed": processed}
    finally:
        await release_lock()
