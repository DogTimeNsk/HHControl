from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class ResumePatch(BaseModel):
    enabled: bool | None = None


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
    last_checked_at: datetime | None
    last_publish_attempt_at: datetime | None
    last_success_at: datetime | None
    last_error: str | None


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
