from datetime import datetime, timedelta, timezone

from app.models.entities import Resume
from app.scheduler.worker import resume_is_due


def make_resume(**values: object) -> Resume:
    now = datetime.now(timezone.utc)
    return Resume(hh_resume_id="hh-1", title="Test", enabled=True, managed=True,
                  created_at=now, updated_at=now, **values)


def test_resume_is_due_at_hh_next_touch_time() -> None:
    now = datetime(2026, 11, 3, 10, 0, tzinfo=timezone.utc)
    resume = make_resume(next_publish_at=now - timedelta(seconds=1))
    assert resume_is_due(resume, now, 60) is True


def test_resume_is_not_due_before_hh_next_touch_time() -> None:
    now = datetime(2026, 11, 3, 10, 0, tzinfo=timezone.utc)
    resume = make_resume(next_publish_at=now + timedelta(seconds=1))
    assert resume_is_due(resume, now, 60) is False


def test_unknown_hh_schedule_is_probed_at_limited_interval() -> None:
    now = datetime(2026, 11, 3, 10, 0, tzinfo=timezone.utc)
    recent = make_resume(last_checked_at=now - timedelta(minutes=59))
    old = make_resume(last_checked_at=now - timedelta(minutes=60))
    assert resume_is_due(recent, now, 60) is False
    assert resume_is_due(old, now, 60) is True
