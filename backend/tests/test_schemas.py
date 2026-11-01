import pytest
from pydantic import ValidationError

from app.schemas.api import ManualResumeCreate


def test_manual_resume_id_is_trimmed_and_validated() -> None:
    assert ManualResumeCreate(hh_resume_id="  a1B2c3  ").hh_resume_id == "a1B2c3"


@pytest.mark.parametrize("value", ["", "resume-id", "x" * 129])
def test_manual_resume_id_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValidationError):
        ManualResumeCreate(hh_resume_id=value)
