import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)


class HHError(Exception):
    def __init__(self, message: str, status_code: int | None = None, retry_after: int | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


@dataclass
class TokenResponse:
    access_token: str
    refresh_token: str | None
    expires_at: datetime | None


class HHClient:
    def __init__(self, settings: Settings, access_token: str | None = None) -> None:
        self.settings = settings
        self.access_token = access_token

    def _headers(self) -> dict[str, str]:
        headers = {"User-Agent": self.settings.hh_user_agent, "Accept": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
                    response = await client.request(method, url, headers=self._headers(), **kwargs)
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    raise HHError("HH API rate limit reached", 429, int(retry_after) if retry_after else None)
                if response.status_code >= 400:
                    try:
                        message = response.json().get("description") or response.text
                    except ValueError:
                        message = response.text
                    logger.warning(
                        "HH API request failed: method=%s path=%s status=%s message=%s",
                        method,
                        response.request.url.path,
                        response.status_code,
                        message[:500],
                    )
                    raise HHError(message or f"HH API returned {response.status_code}", response.status_code)
                return response
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt == 1:
                    logger.warning("HH API is unavailable: method=%s url=%s error=%s", method, url, exc)
                    raise HHError("HH API is unavailable") from exc
                await asyncio.sleep(0.5)
        raise AssertionError("unreachable")

    async def my_resumes(self) -> list[dict[str, Any]]:
        profile = await self.ensure_applicant()
        # HH supplies the canonical applicant-resumes URL in /me. Prefer it
        # over a hard-coded route to follow the token's selected account/site.
        resumes_url = profile.get("resumes_url") or f"{self.settings.hh_api_base_url}/resumes/mine"
        response = await self._request("GET", resumes_url)
        payload = response.json()
        return payload.get("items", payload if isinstance(payload, list) else [])

    async def ensure_applicant(self) -> dict[str, Any]:
        """Verify that the OAuth token belongs to a job-seeker account.

        HH deliberately returns a generic 403 for applicant-only resources, so
        `/me` gives us a safe, actionable diagnostic before calling them.
        """
        response = await self._request("GET", f"{self.settings.hh_api_base_url}/me")
        profile = response.json()
        is_applicant = profile.get("is_applicant") is True
        # Warning level is deliberate: production Uvicorn commonly hides INFO
        # from application loggers, while this diagnostic is essential for a
        # generic HH 403 response.
        logger.warning(
            "HH OAuth account: auth_type=%s is_applicant=%s is_employer=%s has_resumes_url=%s",
            profile.get("auth_type"),
            is_applicant,
            profile.get("is_employer") is True,
            bool(profile.get("resumes_url")),
        )
        if not is_applicant:
            raise HHError(
                "Подключённый HH-аккаунт не имеет роли соискателя. "
                "Войдите в HH под аккаунтом, которому принадлежат резюме.",
                403,
            )
        return profile

    async def resume_status(self, resume_id: str) -> dict[str, Any]:
        response = await self._request("GET", f"{self.settings.hh_api_base_url}/resumes/{resume_id}/status")
        return response.json()

    async def publish(self, resume_id: str) -> int:
        response = await self._request("POST", f"{self.settings.hh_api_base_url}/resumes/{resume_id}/publish")
        return response.status_code

    async def exchange_code(self, code: str) -> TokenResponse:
        return await self._token_request({"grant_type": "authorization_code", "code": code,
                                          "redirect_uri": self.settings.hh_oauth_redirect_uri})

    async def refresh(self, refresh_token: str) -> TokenResponse:
        return await self._token_request({"grant_type": "refresh_token", "refresh_token": refresh_token})

    async def _token_request(self, data: dict[str, str]) -> TokenResponse:
        data.update({"client_id": self.settings.hh_client_id, "client_secret": self.settings.hh_client_secret})
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(f"{self.settings.hh_oauth_base_url}/token", data=data,
                                             headers={"User-Agent": self.settings.hh_user_agent})
        except httpx.HTTPError as exc:
            raise HHError("Could not reach HH OAuth") from exc
        if response.status_code >= 400:
            raise HHError("OAuth token exchange failed", response.status_code)
        payload = response.json()
        expires = payload.get("expires_in")
        return TokenResponse(payload["access_token"], payload.get("refresh_token"),
                             datetime.now().astimezone() + timedelta(seconds=int(expires)) if expires else None)
