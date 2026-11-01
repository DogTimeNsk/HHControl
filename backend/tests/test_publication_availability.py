from datetime import datetime
from zoneinfo import ZoneInfo

from app.browser.publication import publication_availability


MOSCOW = ZoneInfo("Europe/Moscow")


def test_future_time_in_publication_card_is_unavailable_and_parsed() -> None:
    availability = publication_availability(
        ["Поднятие резюме", "Можно завтра в\xa000:45"],
        automatic_renewal_link=True,
        now=datetime(2026, 11, 1, 12, 0, tzinfo=MOSCOW),
    )
    assert availability.can_publish is False
    assert availability.message == "Можно завтра в 00:45"
    assert availability.next_publish_at == datetime(2026, 11, 2, 0, 45, tzinfo=MOSCOW)


def test_hh_pro_automatic_renewal_link_marks_manual_publication_unavailable() -> None:
    availability = publication_availability(["Поднятие резюме"], automatic_renewal_link=True)
    assert availability.can_publish is False
    assert availability.next_publish_at is None


def test_missing_restrictions_allows_button_lookup() -> None:
    availability = publication_availability(["Поднятие резюме"], automatic_renewal_link=False)
    assert availability.can_publish is True


def test_can_publish_now_is_not_treated_as_a_restriction() -> None:
    availability = publication_availability(["Можно сейчас"], automatic_renewal_link=False)
    assert availability.can_publish is True


def test_automatic_renewal_link_overrides_can_publish_now_text() -> None:
    availability = publication_availability(["Можно сейчас"], automatic_renewal_link=True)
    assert availability.can_publish is False
