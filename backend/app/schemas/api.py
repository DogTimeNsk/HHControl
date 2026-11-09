from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_serializer


def utc_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


class LoginRequest(BaseModel):
    username: str
    password: str


class ResumePatch(BaseModel):
    enabled: bool | None = None
    vacancy_monitoring_enabled: bool | None = None
    vacancy_response_limit_enabled: bool | None = None
    vacancy_response_limit: int | None = Field(default=None, ge=1, le=1_000_000)


class ManualResumeCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    hh_resume_id: str = Field(pattern=r"^[A-Za-z0-9]{1,128}$")

class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    hh_resume_id: str
    title: str
    enabled: bool
    status: str | None
    published_at: datetime | None
    next_publish_at: datetime | None
    publish_available: bool | None
    ats_achievements: bool | None
    ats_checked_at: datetime | None
    last_checked_at: datetime | None
    last_publish_attempt_at: datetime | None
    last_success_at: datetime | None
    last_error: str | None
    vacancy_monitoring_enabled: bool
    vacancy_response_limit_enabled: bool
    vacancy_response_limit: int
    last_vacancy_check_at: datetime | None

    @field_serializer("published_at", "next_publish_at", "ats_checked_at", "last_checked_at",
                      "last_publish_attempt_at", "last_success_at", "last_vacancy_check_at", when_used="unless-none")
    def serialize_timestamps(self, value: datetime) -> str:
        return utc_timestamp(value)


class VacancyMatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    hh_vacancy_id: str
    title: str
    vacancy_url: str
    employer_name: str | None
    employer_url: str | None
    salary_from: int | None
    salary_to: int | None
    salary_currency: str | None
    salary_gross: bool | None
    city: str | None
    responses_count: int | None
    total_responses_count: int | None
    online_users_count: int | None
    user_test_present: bool | None
    user_test_id: str | None
    accept_temporary: bool | None
    work_formats: list[str]
    company_negative_attributes: dict[str, Any] | None
    vacancy_properties: list[dict[str, Any]]
    parsed_at: datetime
    last_seen_at: datetime

    @field_serializer("parsed_at", "last_seen_at")
    def serialize_timestamps(self, value: datetime) -> str:
        return utc_timestamp(value)


class VacancyCollectionOut(BaseModel):
    new_count: int


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    resume_id: int
    started_at: datetime
    finished_at: datetime | None
    operation: str
    result: str
    http_status: int | None
    message: str

    @field_serializer("started_at", "finished_at", when_used="unless-none")
    def serialize_timestamps(self, value: datetime) -> str:
        return utc_timestamp(value)
