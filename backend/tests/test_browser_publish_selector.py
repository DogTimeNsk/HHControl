from pathlib import Path


def test_publish_uses_the_resume_page_raise_button() -> None:
    control = (Path(__file__).parents[1] / "app" / "browser" / "control.py").read_text()
    assert "[data-qa='resume-update-button']" in control
    assert "resume-update-button-text" not in control
