"""Interpret the publication availability shown in an HH resume page."""
from dataclasses import dataclass
from datetime import datetime, timedelta
import re
from zoneinfo import ZoneInfo


HH_TIMEZONE = ZoneInfo("Europe/Moscow")
_AVAILABLE_TOMORROW_RE = re.compile(r"^Можно\s+завтра\s+в\s+(\d{1,2}):(\d{2})$", re.IGNORECASE)
_AVAILABLE_TODAY_RE = re.compile(r"^Можно\s+сегодня\s+в\s+(\d{1,2}):(\d{2})$", re.IGNORECASE)


@dataclass(frozen=True)
class PublicationAvailability:
    can_publish: bool
    message: str
    next_publish_at: datetime | None = None


def publication_availability(
    texts: list[str], *, automatic_renewal_link: bool, now: datetime | None = None
) -> PublicationAvailability:
    """Return HH's current manual-publication state from stable visible texts.

    HH's CSS class names are versioned and change frequently, so this deliberately
    uses the human-facing content of the "Поднятие резюме" card and its QA-marked
    HH.pro link instead.
    """
    now = (now or datetime.now(HH_TIMEZONE)).astimezone(HH_TIMEZONE)
    normalized = [" ".join(text.replace("\xa0", " ").split()) for text in texts]
    available_text = next((text for text in normalized if text.startswith("Можно ")), None)
    if available_text:
        next_at = _parse_available_at(available_text, now)
        if next_at:
            return PublicationAvailability(False, available_text, next_at)
    if automatic_renewal_link:
        return PublicationAvailability(
            False,
            "Ручное поднятие сейчас недоступно; HH предлагает подключить автоматическое поднятие",
        )
    if available_text:
        if available_text.casefold() == "можно сейчас":
            return PublicationAvailability(True, available_text)
        return PublicationAvailability(False, available_text)
    return PublicationAvailability(True, "Доступность поднятия не ограничена в карточке HH")


def _parse_available_at(text: str, now: datetime) -> datetime | None:
    match = _AVAILABLE_TOMORROW_RE.fullmatch(text)
    days = 1
    if match is None:
        match = _AVAILABLE_TODAY_RE.fullmatch(text)
        days = 0
    if match is None:
        return None
    hour, minute = map(int, match.groups())
    if hour > 23 or minute > 59:
        return None
    date = (now + timedelta(days=days)).date()
    return datetime(date.year, date.month, date.day, hour, minute, tzinfo=HH_TIMEZONE)
