"""Control plane for the headed Playwright browser shown through noVNC."""
from pathlib import Path
import json
import logging
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException
from playwright.async_api import BrowserContext, Error, Page, Playwright, async_playwright

from app.core.config import get_settings
from app.browser.parsing import resume_id_from_url
from app.browser.publication import publication_availability

app = FastAPI(title="HH Control browser")
settings = get_settings()
logger = logging.getLogger(__name__)
pw: Playwright | None = None
context: BrowserContext | None = None


async def start_context() -> BrowserContext:
    global pw, context
    if context is not None:
        return context
    Path(settings.browser_profile_dir).mkdir(parents=True, exist_ok=True)
    if pw is None:
        pw = await async_playwright().start()
    context = await pw.chromium.launch_persistent_context(
        settings.browser_profile_dir, headless=False, viewport={"width": 1440, "height": 900}
    )
    context.on("close", lambda: globals().__setitem__("context", None))
    return context


async def page_for_user() -> Page:
    """Return a page, recreating Chromium after it was closed in noVNC."""
    global context
    active_context = await start_context()
    try:
        return active_context.pages[0] if active_context.pages else await active_context.new_page()
    except Error:
        context = None
        active_context = await start_context()
        return active_context.pages[0] if active_context.pages else await active_context.new_page()


@app.on_event("startup")
async def startup() -> None:
    # Do not navigate the page here. This is the same visible page controlled
    # through noVNC; a user navigation can abort Page.goto and must never make
    # the entire browser service fail its startup lifecycle.
    await page_for_user()


@app.on_event("shutdown")
async def shutdown() -> None:
    if context:
        await context.close()
    if pw:
        await pw.stop()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/session/export")
async def export_session() -> dict[str, object]:
    if not context:
        raise HTTPException(503, "Browser is not ready")
    return {"storage_state": await context.storage_state()}


@app.post("/session/open-hh")
async def open_hh() -> dict[str, str]:
    if not context:
        raise HTTPException(503, "Browser is not ready")
    page = context.pages[0] if context.pages else await context.new_page()
    await page.goto("https://hh.ru/", wait_until="domcontentloaded")
    return {"status": "opened"}


@app.get("/resumes")
async def resumes() -> dict[str, list[dict[str, str]]]:
    page = await page_for_user()
    await page.goto("https://hh.ru/applicant/resumes", wait_until="domcontentloaded")
    await page.wait_for_timeout(1000)
    links = await page.locator("a[href*='/resume/']").evaluate_all(
        "els => els.map(a => ({href: a.href, title: a.innerText.trim()}))"
    )
    items: dict[str, dict[str, str]] = {}
    for link in links:
        resume_id = resume_id_from_url(link["href"])
        if resume_id:
            items[resume_id] = {"id": resume_id, "title": link["title"] or f"Резюме {resume_id}"}
    return {"items": list(items.values())}


@app.post("/resumes/{resume_id}/publish")
async def publish(resume_id: str) -> dict[str, str | bool | None]:
    page = await page_for_user()
    await page.goto(f"https://hh.ru/resume/{resume_id}", wait_until="domcontentloaded")
    await page.wait_for_timeout(800)
    availability = publication_availability(
        await page.locator("[data-qa='cell-text-content']").all_inner_texts(),
        automatic_renewal_link=await page.locator("[data-qa='resumeservice-button__renewresume']").count() > 0,
    )
    if not availability.can_publish:
        logger.info("HH publication unavailable: resume_id=%s message=%s", resume_id, availability.message)
        return {
            "result": "skipped",
            "message": availability.message,
            "can_publish": False,
            "next_publish_at": availability.next_publish_at.isoformat() if availability.next_publish_at else None,
        }
    # This is the actual "Поднять в поиске" button on the resume page.
    # Use HH's QA attribute rather than versioned Magritte CSS classes.
    button = page.locator("[data-qa='resume-update-button']").first
    if await button.count() == 0 or not await button.is_enabled():
        candidates = await page.locator("button, [role='button']").all_inner_texts()
        logger.warning("HH publish control not found: resume_id=%s controls=%s", resume_id, candidates[:20])
        return {"result": "skipped", "message": "Кнопка поднятия не найдена или пока недоступна в личном кабинете HH", "can_publish": False, "next_publish_at": None}
    await button.click()
    await page.wait_for_timeout(1200)
    logger.info("HH publish control clicked: resume_id=%s", resume_id)
    return {"result": "success", "message": "Команда обновления отправлена через личный кабинет HH", "can_publish": True, "next_publish_at": None}


@app.get("/resumes/{resume_id}/vacancies")
async def vacancies(resume_id: str) -> dict[str, list[dict[str, object]]]:
    """Collect all pages of HH's resume-based, new remote-vacancy search."""
    page = await page_for_user()
    query = [
        ("enable_snippets", "true"), ("label", "not_from_agency"),
        ("ored_clusters", "true"), ("resume", resume_id),
        ("search_field", "name"), ("search_field", "description"),
        ("search_period", "1"), ("work_format", "REMOTE"),
        ("order_by", "publication_time"), ("items_on_page", "50"),
    ]
    base_url = f"https://hh.ru/search/vacancy?{urlencode(query)}"
    await page.goto(base_url, wait_until="domcontentloaded")
    await page.wait_for_timeout(800)
    try:
        rows = await _vacancy_rows(page)
    except (Error, ValueError) as exc:
        logger.warning("HH vacancy search cannot be parsed: resume_id=%s error=%s", resume_id, exc)
        raise HTTPException(502, "HH не отдал список вакансий; проверьте browser session или CAPTCHA") from exc
    page_links = await page.locator("[data-qa='pager-page']").evaluate_all(
        "els => els.map(a => a.href)"
    )
    for page_url in dict.fromkeys(page_links):
        if "page=0" in page_url:
            continue
        await page.goto(page_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(500)
        try:
            rows.extend(await _vacancy_rows(page))
        except (Error, ValueError) as exc:
            logger.warning("HH vacancy search page cannot be parsed: resume_id=%s error=%s", resume_id, exc)
            raise HTTPException(502, "HH не отдал одну из страниц вакансий") from exc
    unique = {str(row["hh_vacancy_id"]): row for row in rows}
    logger.info("HH vacancy search collected: resume_id=%s vacancies=%s", resume_id, len(unique))
    return {"items": list(unique.values())}


async def _vacancy_rows(page: Page) -> list[dict[str, object]]:
    state_node = page.locator("#HH-Lux-InitialState")
    try:
        await state_node.wait_for(state="attached", timeout=10_000)
        # HH keeps the state in a <template>; its payload is stored in the
        # template's DocumentFragment, not necessarily in the element's own
        # textContent. Reading it explicitly avoids silently using the
        # reduced DOM fallback for every vacancy.
        raw_state = await state_node.evaluate(
            "node => node.content ? node.content.textContent : node.textContent"
        )
        if not raw_state:
            raise ValueError("HH search state is empty")
        state = json.loads(raw_state, strict=False)
        vacancies = state.get("vacancySearchResult", {}).get("vacancies", [])
        if not isinstance(vacancies, list):
            raise ValueError("HH search state has no vacancy list")
        return [_vacancy_row(vacancy) for vacancy in vacancies if isinstance(vacancy, dict)]
    except (Error, ValueError, json.JSONDecodeError) as exc:
        # HH occasionally delays or omits its hydration state. The visible
        # cards still contain the essential data, so retain collection rather
        # than failing the whole hourly run.
        logger.warning("HH search state unavailable, falling back to DOM: %s", exc)
        return await _vacancy_rows_from_dom(page)


async def _vacancy_rows_from_dom(page: Page) -> list[dict[str, object]]:
    cards = page.locator("[data-qa='vacancy-serp__vacancy']")
    rows: list[dict[str, object]] = []
    for index in range(await cards.count()):
        card = cards.nth(index)
        title_link = card.locator("a[data-qa='serp-item__title']").first
        href = await title_link.get_attribute("href")
        title = (await title_link.inner_text()).strip()
        vacancy_id = (href or "").split("/vacancy/")[-1].split("?")[0]
        if not vacancy_id.isdigit() or not title:
            continue
        employer = card.locator("a[data-qa='vacancy-serp__vacancy-employer']").first
        employer_href = await employer.get_attribute("href") if await employer.count() else None
        salary_values = await card.locator("[class*='compensation-labels'] data").evaluate_all(
            "els => els.map(el => el.value)"
        )
        numbers = [int(value) for value in salary_values if str(value).isdigit()]
        currency = next((str(value) for value in salary_values if not str(value).isdigit()), None)
        city = card.locator("[data-qa='vacancy-serp__vacancy-address']").first
        rows.append({
            "hh_vacancy_id": vacancy_id, "title": title,
            "vacancy_url": f"https://hh.ru/vacancy/{vacancy_id}",
            "employer_name": (await employer.inner_text()).strip() if await employer.count() else None,
            "employer_url": f"https://hh.ru{employer_href}" if employer_href else None,
            "salary_from": numbers[0] if numbers else None,
            "salary_to": numbers[1] if len(numbers) > 1 else None,
            "salary_currency": currency,
            "city": (await city.inner_text()).strip() if await city.count() else None,
        })
    if rows:
        return rows
    raise ValueError("HH vacancy cards were not found; check the browser session or CAPTCHA")


def _vacancy_row(vacancy: dict[str, object]) -> dict[str, object]:
    compensation = _as_dict(vacancy.get("compensation"))
    company = _as_dict(vacancy.get("company"))
    address = _as_dict(vacancy.get("address"))
    links = _as_dict(vacancy.get("links"))
    properties = _vacancy_properties(vacancy)
    return {
        "hh_vacancy_id": str(vacancy["vacancyId"]),
        "title": str(vacancy.get("name") or "Без названия"),
        "vacancy_url": str(links.get("desktop") or f"https://hh.ru/vacancy/{vacancy['vacancyId']}"),
        "employer_name": company.get("visibleName") or company.get("name"),
        "employer_url": f"https://hh.ru/employer/{company['id']}" if company.get("id") else None,
        "salary_from": _optional_int(compensation.get("from")),
        "salary_to": _optional_int(compensation.get("to")),
        "salary_currency": compensation.get("currencyCode"),
        "salary_gross": _optional_bool(compensation.get("gross")),
        "city": address.get("city"),
        "responses_count": _optional_int(vacancy.get("responsesCount")),
        "total_responses_count": _optional_int(vacancy.get("totalResponsesCount")),
        "online_users_count": _optional_int(vacancy.get("online_users_count")),
        "user_test_present": _optional_bool(vacancy.get("userTestPresent")),
        "user_test_id": vacancy.get("userTestId"),
        "accept_temporary": _optional_bool(vacancy.get("acceptTemporary")),
        "work_formats": _work_formats(vacancy.get("workFormats")),
        "company_negative_attributes": company.get("employersNegativeAttribute"),
        "vacancy_properties": properties,
    }


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) else None


def _optional_bool(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _work_formats(value: object) -> list[str]:
    return [str(item) for group in value if isinstance(group, dict)
            for item in group.get("workFormatsElement", [])] if isinstance(value, list) else []


def _vacancy_properties(vacancy: dict[str, object]) -> list[dict[str, object]]:
    properties = _as_dict(vacancy.get("vacancyProperties")).get("properties", [])
    return [property_ for group in properties if isinstance(group, dict)
            for property_ in group.get("property", []) if isinstance(property_, dict)] if isinstance(properties, list) else []


@app.get("/resumes/{resume_id}/ats-check")
async def ats_check(resume_id: str) -> dict[str, bool]:
    """Check the employer-facing print view for HH's achievements marker."""
    page = await page_for_user()
    await page.goto(
        f"https://hh.ru/resume/{resume_id}?hhtmFrom=profile&print=true",
        wait_until="domcontentloaded",
    )
    await page.wait_for_timeout(800)
    achievements = await page.locator("[data-qa='resume-card-tag-achievements']").count() > 0
    logger.info("HH ATS achievements check: resume_id=%s achievements=%s", resume_id, achievements)
    return {"achievements": achievements}
