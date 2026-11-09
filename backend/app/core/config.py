from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:////data/hh-control.db"
    app_session_secret: str = "change-me-before-production"
    token_encryption_key: str = ""
    admin_username: str = "admin"
    publish_check_interval_minutes: int = 5
    scheduler_lock_wait_seconds: int = 600
    unknown_publish_check_interval_minutes: int = 60
    hh_client_id: str = ""
    hh_client_secret: str = ""
    hh_oauth_redirect_uri: str = ""
    hh_user_agent: str = "HH-Control/0.1 (admin@example.invalid)"
    hh_api_base_url: str = "https://api.hh.ru"
    hh_oauth_base_url: str = "https://hh.ru/oauth"
    cookie_secure: bool = False
    browser_control_url: str = "http://browser:9000"
    browser_profile_dir: str = "/browser-data/profile"
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    @property
    def sqlite_path(self) -> Path | None:
        prefix = "sqlite+aiosqlite:///"
        if self.database_url.startswith(prefix):
            return Path(self.database_url.removeprefix(prefix))
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()
