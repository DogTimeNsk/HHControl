from app.browser.control import _vacancy_row


def test_vacancy_row_reads_hh_initial_state_fields() -> None:
    row = _vacancy_row({
        "vacancyId": 123, "name": "Python developer", "links": {"desktop": "https://hh.ru/vacancy/123"},
        "company": {"id": 5, "visibleName": "Company", "employersNegativeAttribute": {"hasBreaches": True}},
        "address": {"city": "Москва"},
        "compensation": {"from": 100_000, "to": 150_000, "currencyCode": "RUR", "gross": False},
        "responsesCount": 10, "totalResponsesCount": 20, "online_users_count": 3,
        "userTestPresent": True, "userTestId": "test-1", "acceptTemporary": False,
        "workFormats": [{"workFormatsElement": ["REMOTE", "HYBRID"]}],
        "vacancyProperties": {"properties": [{"property": [{"propertyType": "HH_ANTIFRAUD_SUSPICIOUS_VACANCY"}]}]},
    })

    assert row["hh_vacancy_id"] == "123"
    assert row["salary_gross"] is False
    assert row["work_formats"] == ["REMOTE", "HYBRID"]
    assert row["company_negative_attributes"] == {"hasBreaches": True}
    assert row["vacancy_properties"] == [{"propertyType": "HH_ANTIFRAUD_SUSPICIOUS_VACANCY"}]
