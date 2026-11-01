from datetime import datetime, timezone

from app.core.security import as_utc


def test_as_utc_assumes_naive_sqlite_timestamp_is_utc() -> None:
    naive = datetime(2026, 11, 1, 12, 0, 0)
    assert as_utc(naive) == datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)


def test_as_utc_preserves_aware_utc_timestamp() -> None:
    value = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)
    assert as_utc(value) == value
