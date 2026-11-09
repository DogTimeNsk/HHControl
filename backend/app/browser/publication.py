"""Interpret the publication availability shown in an HH resume page."""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class PublicationAvailability:
    can_publish: bool
    message: str
    next_publish_at: datetime | None = None


def publication_availability(texts: list[str], *, automatic_renewal_link: bool) -> PublicationAvailability:
    """Return HH's current manual-publication state from stable visible texts.

    HH's CSS class names are versioned and change frequently, so this deliberately
    uses the human-facing content of the "Поднятие резюме" card and its QA-marked
    HH.pro link instead.
    """
    normalized = [" ".join(text.replace("\xa0", " ").split()) for text in texts]
    available_text = next((text for text in normalized if text.startswith("Можно ")), None)
    if available_text:
        # A visible phrase such as “Можно завтра в 10:00” has no timezone.
        # Keep it as information, but never invent an absolute timestamp.
        if available_text.casefold() == "можно сейчас":
            return PublicationAvailability(True, available_text)
        return PublicationAvailability(False, available_text)
    if automatic_renewal_link:
        return PublicationAvailability(
            False,
            "Ручное поднятие сейчас недоступно; HH предлагает подключить автоматическое поднятие",
        )
    return PublicationAvailability(True, "Доступность поднятия не ограничена в карточке HH")


def publication_availability_from_state(state: dict[str, Any]) -> PublicationAvailability | None:
    """Read HH's absolute next-update timestamp from resume hydration state."""
    next_touch_at = _find_value(state, "nextTouchAt")
    to_update = _find_value(state, "toUpdate")
    to_update_value = to_update.get("value") if isinstance(to_update, dict) else None
    if not isinstance(next_touch_at, (int, float)) and not isinstance(to_update_value, (int, float)):
        return None
    next_publish_at = (
        datetime.fromtimestamp(next_touch_at / 1000, tz=timezone.utc)
        if isinstance(next_touch_at, (int, float)) else None
    )
    can_publish = to_update_value == 0
    return PublicationAvailability(
        can_publish=can_publish,
        message="Поднятие доступно сейчас" if can_publish else "Поднятие пока недоступно в HH",
        next_publish_at=next_publish_at,
    )


def _find_value(value: object, key: str) -> object | None:
    if isinstance(value, dict):
        if key in value:
            return value[key]
        for child in value.values():
            found = _find_value(child, key)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_value(child, key)
            if found is not None:
                return found
    return None
