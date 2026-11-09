from datetime import datetime, timezone

from app.browser.publication import publication_availability, publication_availability_from_state


def test_future_time_in_publication_card_is_unavailable_but_not_assigned_a_timezone() -> None:
    availability = publication_availability(
        ["Поднятие резюме", "Можно завтра в\xa000:45"],
        automatic_renewal_link=True,
    )
    assert availability.can_publish is False
    assert availability.message == "Можно завтра в 00:45"
    assert availability.next_publish_at is None


def test_resume_state_uses_hh_epoch_timestamp() -> None:
    availability = publication_availability_from_state({
        "profile": {"nextTouchAt": 1793657176055, "toUpdate": {"value": 10}},
    })
    assert availability is not None
    assert availability.can_publish is False
    assert availability.next_publish_at == datetime.fromtimestamp(1793657176.055, tz=timezone.utc)


def test_resume_state_marks_zero_remaining_time_as_available() -> None:
    availability = publication_availability_from_state({"toUpdate": {"value": 0}})
    assert availability is not None
    assert availability.can_publish is True


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
