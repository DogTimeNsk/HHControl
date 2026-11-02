import httpx

from app.core.config import Settings


class BrowserControlError(Exception):
    pass


class BrowserControlClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def export_session(self) -> dict[str, object]:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(f"{self.settings.browser_control_url}/session/export")
            response.raise_for_status()
            return response.json()["storage_state"]
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise BrowserControlError("Browser session is unavailable") from exc

    async def open_hh(self) -> None:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(f"{self.settings.browser_control_url}/session/open-hh")
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise BrowserControlError("Browser is unavailable") from exc

    async def resumes(self) -> list[dict[str, str]]:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(f"{self.settings.browser_control_url}/resumes")
            response.raise_for_status()
            return response.json()["items"]
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise BrowserControlError("Не удалось получить резюме из личного кабинета") from exc

    async def publish(self, resume_id: str) -> dict[str, str | bool | None]:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(f"{self.settings.browser_control_url}/resumes/{resume_id}/publish")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise BrowserControlError("Не удалось обновить резюме в личном кабинете") from exc

    async def ats_check(self, resume_id: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(f"{self.settings.browser_control_url}/resumes/{resume_id}/ats-check")
            response.raise_for_status()
            achievements = response.json()["achievements"]
            if not isinstance(achievements, bool):
                raise ValueError("Invalid achievements value")
            return achievements
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise BrowserControlError("Не удалось проверить ATS-маркер резюме") from exc

    async def vacancies(self, resume_id: str) -> list[dict[str, object]]:
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.get(f"{self.settings.browser_control_url}/resumes/{resume_id}/vacancies")
            response.raise_for_status()
            return response.json()["items"]
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise BrowserControlError("Не удалось собрать подходящие вакансии из личного кабинета") from exc
