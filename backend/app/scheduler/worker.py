from datetime import datetime, timezone

from sqlalchemy import select, text

from app.api.routes import hh_client
from app.core.config import get_settings
from app.core.security import lock_until
from app.db.session import SessionLocal
from app.models.entities import AppSetting, BrowserCredential, PublishEvent, Resume
from app.services.browser_control import BrowserControlClient, BrowserControlError
from app.services.publish_service import publish_resume
from app.services.resume_service import parse_datetime
from app.services.vacancy_monitor_service import collect_vacancies


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


async def run_scheduled_publish() -> dict[str, int | str]:
    if not await acquire_lock():
        return {"status": "already_running", "processed": 0}
    try:
        async with SessionLocal() as session:
            resumes = (await session.scalars(select(Resume).where(Resume.enabled.is_(True), Resume.managed.is_(True)))).all()
            browser_mode = bool(await session.get(BrowserCredential, 1))
            client = None if browser_mode else await hh_client(session)
            for resume in resumes:
                if browser_mode:
                    now = datetime.now(timezone.utc)
                    try:
                        result = await BrowserControlClient(get_settings()).publish(resume.hh_resume_id)
                        event = PublishEvent(resume_id=resume.id, started_at=now, finished_at=now, operation="publish", result=result["result"], http_status=None, message=result["message"])
                        resume.last_checked_at = now
                        resume.next_publish_at = parse_datetime(result.get("next_publish_at"))
                        resume.publish_available = result.get("can_publish") if isinstance(result.get("can_publish"), bool) else None
                        if result["result"] == "success":
                            resume.last_success_at, resume.last_error = now, None
                    except BrowserControlError as exc:
                        event = PublishEvent(resume_id=resume.id, started_at=now, finished_at=datetime.now(timezone.utc), operation="publish", result="failed", http_status=None, message=str(exc))
                        resume.last_error = str(exc)
                    session.add(event)
                    resume.last_publish_attempt_at = now
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
