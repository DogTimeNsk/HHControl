import asyncio
import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import get_settings
from app.scheduler.worker import run_scheduled_publish, run_scheduled_vacancy_collection


async def main() -> None:
    settings = get_settings()
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(run_scheduled_publish, "interval", minutes=settings.publish_check_interval_minutes,
                      id="publish_resumes", max_instances=1, coalesce=True)
    scheduler.add_job(run_scheduled_vacancy_collection, "interval", minutes=60,
                      id="collect_vacancies", max_instances=1, coalesce=True,
                      next_run_time=datetime.now(timezone.utc) + timedelta(minutes=2))
    scheduler.start()
    logging.info("Scheduler started: publish_check=%s minutes", settings.publish_check_interval_minutes)
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
