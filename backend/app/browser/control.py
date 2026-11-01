"""Control plane for the headed Playwright browser shown through noVNC."""
from pathlib import Path
import logging

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
    page = await page_for_user()
    await page.goto("https://hh.ru/", wait_until="domcontentloaded")


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
    # HH exposes this QA attribute on the actual applicant-resume action.
    # Clicking the nested span bubbles to its clickable parent.
    button = page.locator("[data-qa='resume-update-button-text']").first
    if await button.count() == 0 or not await button.is_enabled():
        candidates = await page.locator("button, [role='button']").all_inner_texts()
        logger.warning("HH publish control not found: resume_id=%s controls=%s", resume_id, candidates[:20])
        return {"result": "skipped", "message": "Кнопка поднятия не найдена или пока недоступна в личном кабинете HH", "can_publish": False, "next_publish_at": None}
    await button.click()
    await page.wait_for_timeout(1200)
    logger.info("HH publish control clicked: resume_id=%s", resume_id)
    return {"result": "success", "message": "Команда обновления отправлена через личный кабинет HH", "can_publish": True, "next_publish_at": None}
