from app.browser.parsing import resume_id_from_url


def test_extracts_real_hh_resume_id() -> None:
    identifier = "b5acd3beff02da10270039ed1f354b59523239"
    assert resume_id_from_url(f"https://hh.ru/resume/{identifier}?from=menu") == identifier


def test_ignores_hh_resume_edit_route() -> None:
    assert resume_id_from_url("https://hh.ru/resume/edit") is None
