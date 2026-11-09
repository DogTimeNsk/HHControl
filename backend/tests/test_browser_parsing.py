from app.browser.parsing import resume_id_from_url
from app.browser.control import _additional_search_page_urls


def test_extracts_real_hh_resume_id() -> None:
    identifier = "b5acd3beff02da10270039ed1f354b59523239"
    assert resume_id_from_url(f"https://hh.ru/resume/{identifier}?from=menu") == identifier


def test_ignores_hh_resume_edit_route() -> None:
    assert resume_id_from_url("https://hh.ru/resume/edit") is None


def test_limits_vacancy_search_to_first_four_pages() -> None:
    links = [
        f"https://hh.ru/search/vacancy?resume=resume&search_session_id=session&page={page}"
        for page in (0, 1, 2, 3, 4, 21)
    ]

    assert _additional_search_page_urls(links) == links[1:4]
