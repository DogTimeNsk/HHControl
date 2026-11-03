import secrets
import logging
import json
import httpx
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.config import get_settings
from app.core.security import as_utc, decrypt, encrypt, encryption_key, is_valid_fernet_key, verify_password
from app.db.session import get_session
from app.models.entities import AdminUser, BrowserCredential, OAuthCredential, OAuthState, PublishEvent, Resume, VacancyMatch
from app.schemas.api import EventOut, LoginRequest, ManualResumeCreate, ResumeOut, ResumePatch, VacancyCollectionOut, VacancyMatchOut
from app.services.hh_client import HHClient, HHError
from app.services.browser_control import BrowserControlClient, BrowserControlError
from app.services.publish_service import publish_resume
from app.services.resume_service import parse_datetime, sync_resumes
from app.services.vacancy_monitor_service import collect_vacancies

router = APIRouter(prefix="/api")
settings = get_settings()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/setup/status")
async def setup_status(_: AdminUser = Depends(require_admin)) -> dict[str, object]:
    """Return actionable configuration problems before a user action fails."""
    issues: list[dict[str, str]] = []
    if settings.app_session_secret == "change-me-before-production":
        issues.append({"code": "app_session_secret", "message": "Не задан APP_SESSION_SECRET.",
                       "help": "Укажите длинное случайное значение в .env и перезапустите сервисы."})
    if not settings.token_encryption_key:
        issues.append({"code": "token_encryption_key", "message": "Не задан TOKEN_ENCRYPTION_KEY.",
                       "help": "Сгенерируйте Fernet-ключ и сохраните его в .env."})
    elif not is_valid_fernet_key(settings.token_encryption_key):
        issues.append({"code": "token_encryption_key", "message": "TOKEN_ENCRYPTION_KEY имеет неверный формат.",
                       "help": "Используйте: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\". Сохраните полученный ключ в .env и перезапустите сервисы."})
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            response = await client.get(f"{settings.browser_control_url}/health")
        response.raise_for_status()
    except httpx.HTTPError:
        issues.append({"code": "browser", "message": "Browser-сервис недоступен.",
                       "help": "Проверьте docker compose logs browser и дождитесь запуска контейнера."})
    return {"ready": not issues, "issues": issues}


@router.post("/auth/login")
async def login(payload: LoginRequest, request: Request, session: AsyncSession = Depends(get_session)) -> dict[str, bool]:
    user = await session.scalar(select(AdminUser).where(AdminUser.username == payload.username))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверное имя или пароль")
    request.session["admin_id"] = user.id
    return {"ok": True}


@router.post("/auth/logout")
async def logout(request: Request) -> Response:
    request.session.clear()
    return Response(status_code=204)


@router.get("/auth/me")
async def me(user: AdminUser = Depends(require_admin)) -> dict[str, str]:
    return {"username": user.username}


@router.get("/oauth/connect")
async def oauth_connect(_: AdminUser = Depends(require_admin), session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    if not all([settings.hh_client_id, settings.hh_client_secret, settings.hh_oauth_redirect_uri]):
        raise HTTPException(503, "OAuth не настроен")
    state = secrets.token_urlsafe(32)
    session.add(OAuthState(state=state, expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)))
    await session.commit()
    params = urlencode({"response_type": "code", "client_id": settings.hh_client_id,
                         "redirect_uri": settings.hh_oauth_redirect_uri, "state": state,
                         # HH accounts may have both employer and applicant
                         # contexts; this application only works with resumes.
                         "role": "applicant", "force_role": "true",
                         "skip_choose_account": "true"})
    return {"authorization_url": f"{settings.hh_oauth_base_url}/authorize?{params}"}


@router.get("/oauth/callback")
async def oauth_callback(code: str, state: str, session: AsyncSession = Depends(get_session)) -> Response:
    stored = await session.scalar(select(OAuthState).where(OAuthState.state == state))
    if not stored or as_utc(stored.expires_at) < datetime.now(timezone.utc):
        raise HTTPException(400, "Недействительный или истёкший OAuth state")
    await session.delete(stored)
    try:
        token = await HHClient(settings).exchange_code(code)
        await HHClient(settings, token.access_token).ensure_applicant()
    except HHError as exc:
        logger.warning("HH OAuth connection rejected: status=%s message=%s", exc.status_code, str(exc)[:500])
        raise HTTPException(403 if exc.status_code == 403 else 502, str(exc)) from exc
    key = encryption_key(settings.token_encryption_key, settings.app_session_secret)
    credential = await session.get(OAuthCredential, 1)
    if credential is None:
        credential = OAuthCredential(id=1, access_token_encrypted=encrypt(token.access_token, key),
                                    refresh_token_encrypted=encrypt(token.refresh_token, key) if token.refresh_token else None,
                                    expires_at=token.expires_at, updated_at=datetime.now(timezone.utc))
        session.add(credential)
    else:
        credential.access_token_encrypted = encrypt(token.access_token, key)
        credential.refresh_token_encrypted = (encrypt(token.refresh_token, key) if token.refresh_token
                                              else credential.refresh_token_encrypted)
        credential.expires_at, credential.updated_at = token.expires_at, datetime.now(timezone.utc)
    await session.commit()
    return Response("<script>window.close()</script>Авторизация завершена. Это окно можно закрыть.", media_type="text/html")


async def hh_client(session: AsyncSession) -> HHClient:
    credential = await session.get(OAuthCredential, 1)
    if not credential:
        raise HTTPException(409, "Сначала подключите аккаунт hh.ru")
    key = encryption_key(settings.token_encryption_key, settings.app_session_secret)
    if credential.expires_at and as_utc(credential.expires_at) <= datetime.now(timezone.utc):
        if not credential.refresh_token_encrypted:
            raise HTTPException(401, "Авторизация HH истекла: подключите аккаунт заново")
        try:
            token = await HHClient(settings).refresh(decrypt(credential.refresh_token_encrypted, key))
        except HHError as exc:
            raise HTTPException(401, f"Не удалось обновить авторизацию HH: {exc}") from exc
        credential.access_token_encrypted = encrypt(token.access_token, key)
        credential.refresh_token_encrypted = encrypt(token.refresh_token, key) if token.refresh_token else None
        credential.expires_at, credential.updated_at = token.expires_at, datetime.now(timezone.utc)
        await session.commit()
    return HHClient(settings, decrypt(credential.access_token_encrypted, key))


@router.get("/connection")
async def connection(_: AdminUser = Depends(require_admin), session: AsyncSession = Depends(get_session)) -> dict[str, bool]:
    return {"connected": bool(await session.get(OAuthCredential, 1))}


@router.delete("/connection", status_code=204)
async def disconnect(_: AdminUser = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    """Forget local HH credentials without changing anything on hh.ru."""
    credential = await session.get(OAuthCredential, 1)
    if credential:
        await session.delete(credential)
        await session.commit()


@router.get("/browser/session")
async def browser_session(_: AdminUser = Depends(require_admin), session: AsyncSession = Depends(get_session)) -> dict[str, bool]:
    from app.models.entities import BrowserCredential
    return {"saved": bool(await session.get(BrowserCredential, 1))}


@router.post("/browser/session/save")
async def save_browser_session(_: AdminUser = Depends(require_admin), session: AsyncSession = Depends(get_session)) -> dict[str, bool]:
    from app.models.entities import BrowserCredential
    if not settings.token_encryption_key or not is_valid_fernet_key(settings.token_encryption_key):
        raise HTTPException(409, "Сначала задайте корректный TOKEN_ENCRYPTION_KEY в .env")
    try:
        state = await BrowserControlClient(settings).export_session()
    except BrowserControlError as exc:
        raise HTTPException(503, str(exc)) from exc
    # Playwright state contains session cookies; it is encrypted before SQLite.
    key = encryption_key(settings.token_encryption_key, settings.app_session_secret)
    serialized = encrypt(json.dumps(state), key)
    credential = await session.get(BrowserCredential, 1)
    if credential is None:
        session.add(BrowserCredential(id=1, storage_state_encrypted=serialized, updated_at=datetime.now(timezone.utc)))
    else:
        credential.storage_state_encrypted, credential.updated_at = serialized, datetime.now(timezone.utc)
    await session.commit()
    return {"saved": True}


@router.post("/browser/open")
async def open_browser(_: AdminUser = Depends(require_admin)) -> dict[str, bool]:
    try:
        await BrowserControlClient(settings).open_hh()
    except BrowserControlError as exc:
        raise HTTPException(503, str(exc)) from exc
    return {"opened": True}


@router.get("/browser/access", status_code=204)
async def authorize_browser_access(_: AdminUser = Depends(require_admin)) -> Response:
    """Internal Nginx auth subrequest for noVNC assets and its WebSocket."""
    return Response(status_code=204)


@router.delete("/browser/session", status_code=204)
async def delete_browser_session(_: AdminUser = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    from app.models.entities import BrowserCredential
    credential = await session.get(BrowserCredential, 1)
    if credential:
        await session.delete(credential)
        await session.commit()


@router.get("/resumes", response_model=list[ResumeOut])
async def list_resumes(_: AdminUser = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    return (await session.scalars(select(Resume).where(Resume.managed.is_(True)).order_by(Resume.title))).all()


@router.post("/resumes/sync", response_model=list[ResumeOut])
async def synchronize(_: AdminUser = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    try:
        if await session.get(BrowserCredential, 1):
            items = await BrowserControlClient(settings).resumes()
        else:
            items = await (await hh_client(session)).my_resumes()
        return await sync_resumes(session, items)
    except BrowserControlError as exc:
        logger.warning("Browser resume synchronization failed: %s", exc)
        raise HTTPException(503, str(exc)) from exc
    except HHError as exc:
        logger.warning("Resume synchronization failed: status=%s message=%s", exc.status_code, str(exc)[:500])
        # Preserve an explicit HH permission refusal instead of presenting it
        # as an upstream gateway failure.
        status_code = 403 if exc.status_code == 403 else 502
        raise HTTPException(status_code, str(exc)) from exc


@router.post("/resumes/manual", response_model=ResumeOut, status_code=201)
async def add_resume_manually(payload: ManualResumeCreate, _: AdminUser = Depends(require_admin),
                              session: AsyncSession = Depends(get_session)):
    hh_resume_id = payload.hh_resume_id
    try:
        browser_items = await BrowserControlClient(settings).resumes()
        item = next((entry for entry in browser_items if entry["id"] == hh_resume_id), None)
        if item is None:
            raise HTTPException(404, "Резюме не найдено в открытом личном кабинете HH")
        status_payload = {"title": item["title"], "status": {"id": "unknown"}}
    except BrowserControlError:
        client = await hh_client(session)
        # This is the actual ownership/access check. It must succeed before a
        # local entry is created, so a mistyped or foreign ID is never managed.
        try:
            status_payload = await client.resume_status(hh_resume_id)
        except HHError as exc:
            logger.warning("Manual resume connection failed: status=%s message=%s", exc.status_code, str(exc)[:500])
            raise HTTPException(403 if exc.status_code == 403 else 502, str(exc)) from exc
    except HHError as exc:
        logger.warning("Manual resume connection failed: status=%s message=%s", exc.status_code, str(exc)[:500])
        raise HTTPException(403 if exc.status_code == 403 else 502, str(exc)) from exc

    resume = await session.scalar(select(Resume).where(Resume.hh_resume_id == hh_resume_id))
    now = datetime.now(timezone.utc)
    status = (status_payload.get("status") or {}).get("id")
    if resume is None:
        title = status_payload.get("title") or f"Резюме {hh_resume_id}"
        resume = Resume(hh_resume_id=hh_resume_id, title=title, enabled=False, managed=True,
                        status=status, next_publish_at=None, created_at=now, updated_at=now)
        session.add(resume)
    else:
        resume.managed = True
        resume.status = status
        resume.updated_at = now
    resume.last_checked_at = now
    resume.next_publish_at = parse_datetime(status_payload.get("next_publish_at"))
    await session.commit()
    await session.refresh(resume)
    return resume


@router.patch("/resumes/{resume_id}", response_model=ResumeOut)
async def patch_resume(resume_id: int, payload: ResumePatch, _: AdminUser = Depends(require_admin),
                       session: AsyncSession = Depends(get_session)):
    resume = await session.get(Resume, resume_id)
    if not resume:
        raise HTTPException(404, "Резюме не найдено")
    if payload.enabled is not None:
        resume.enabled = payload.enabled
    if payload.vacancy_monitoring_enabled is not None:
        resume.vacancy_monitoring_enabled = payload.vacancy_monitoring_enabled
    await session.commit()
    await session.refresh(resume)
    return resume


@router.post("/resumes/{resume_id}/ats-check", response_model=ResumeOut)
async def check_ats(resume_id: int, _: AdminUser = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    resume = await session.get(Resume, resume_id)
    if not resume:
        raise HTTPException(404, "Резюме не найдено")
    if not await session.get(BrowserCredential, 1):
        raise HTTPException(409, "Сначала войдите в hh.ru и сохраните Browser session")
    try:
        resume.ats_achievements = await BrowserControlClient(settings).ats_check(resume.hh_resume_id)
    except BrowserControlError as exc:
        raise HTTPException(503, str(exc)) from exc
    resume.ats_checked_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(resume)
    return resume


@router.delete("/resumes/{resume_id}", status_code=204)
async def remove_resume(resume_id: int, _: AdminUser = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    resume = await session.get(Resume, resume_id)
    if not resume:
        raise HTTPException(404, "Резюме не найдено")
    # This is a local unmanage operation: HH data and the publication audit stay intact.
    resume.managed, resume.enabled = False, False
    await session.commit()


@router.post("/resumes/{resume_id}/publish", response_model=EventOut)
async def publish(resume_id: int, _: AdminUser = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    resume = await session.get(Resume, resume_id)
    if not resume:
        raise HTTPException(404, "Резюме не найдено")
    if await session.get(BrowserCredential, 1):
        try:
            result = await BrowserControlClient(settings).publish(resume.hh_resume_id)
        except BrowserControlError as exc:
            raise HTTPException(503, str(exc)) from exc
        now = datetime.now(timezone.utc)
        event = PublishEvent(resume_id=resume.id, started_at=now, finished_at=now, operation="publish",
                             result=result["result"], http_status=None, message=result["message"])
        session.add(event)
        resume.last_publish_attempt_at = now
        resume.last_checked_at = now
        resume.next_publish_at = parse_datetime(result.get("next_publish_at"))
        resume.publish_available = result.get("can_publish") if isinstance(result.get("can_publish"), bool) else None
        if result["result"] == "success":
            resume.last_success_at, resume.last_error = now, None
        await session.commit()
        return event
    return await publish_resume(session, resume, await hh_client(session))


@router.get("/resumes/{resume_id}/history", response_model=list[EventOut])
async def history(resume_id: int, _: AdminUser = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    return (await session.scalars(select(PublishEvent).where(PublishEvent.resume_id == resume_id)
                                  .order_by(PublishEvent.started_at.desc()))).all()


@router.get("/resumes/{resume_id}/vacancies", response_model=list[VacancyMatchOut])
async def vacancy_matches(resume_id: int, _: AdminUser = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    resume = await session.get(Resume, resume_id)
    if not resume:
        raise HTTPException(404, "Резюме не найдено")
    return (await session.scalars(select(VacancyMatch).where(VacancyMatch.resume_id == resume_id)
                                  .order_by(VacancyMatch.parsed_at.desc()))).all()


@router.post("/resumes/{resume_id}/vacancies/collect", response_model=VacancyCollectionOut)
async def collect_vacancy_matches(resume_id: int, _: AdminUser = Depends(require_admin),
                                  session: AsyncSession = Depends(get_session)):
    resume = await session.get(Resume, resume_id)
    if not resume or not resume.managed:
        raise HTTPException(404, "Резюме не найдено")
    if not await session.get(BrowserCredential, 1):
        raise HTTPException(409, "Сначала войдите в hh.ru и сохраните Browser session")
    from app.scheduler.worker import acquire_lock, release_lock
    if not await acquire_lock():
        raise HTTPException(409, "Сейчас выполняется другая задача планировщика")
    try:
        try:
            new_count = await collect_vacancies(session, resume, BrowserControlClient(settings))
        except BrowserControlError as exc:
            resume.last_error = str(exc)
            await session.commit()
            raise HTTPException(503, str(exc)) from exc
    finally:
        await release_lock()
    return VacancyCollectionOut(new_count=new_count)


@router.get("/events", response_model=list[EventOut])
async def events(_: AdminUser = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    return (await session.scalars(select(PublishEvent).order_by(PublishEvent.started_at.desc()).limit(50))).all()


@router.get("/scheduler/status")
async def scheduler_status(_: AdminUser = Depends(require_admin), session: AsyncSession = Depends(get_session)) -> dict[str, str | int | None]:
    from app.models.entities import AppSetting
    lock = await session.get(AppSetting, "scheduler_lock")
    return {"interval_hours": settings.scheduler_interval_hours, "lock_until": lock.value if lock else None}


@router.post("/scheduler/run")
async def scheduler_run(_: AdminUser = Depends(require_admin)) -> dict[str, int | str]:
    from app.scheduler.worker import run_scheduled_publish
    return await run_scheduled_publish()
