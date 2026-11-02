import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import get_settings
from app.scheduler.worker import run_scheduled_publish, run_scheduled_vacancy_collection


async def main() -> None:
    settings = get_settings()
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(run_scheduled_publish, "interval", hours=settings.scheduler_interval_hours,
                      id="publish_resumes", max_instances=1, coalesce=True)
    scheduler.add_job(run_scheduled_vacancy_collection, "interval", minutes=60,
                      id="collect_vacancies", max_instances=1, coalesce=True)
    scheduler.start()
    logging.info("Scheduler started: interval=%s hours", settings.scheduler_interval_hours)
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
