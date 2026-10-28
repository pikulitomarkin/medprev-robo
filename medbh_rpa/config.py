from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

UiBackend = Literal["auto", "uia", "playwright", "mock"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    msadmin_exe: str = Field(default="", alias="MSADMIN_EXE")
    msadmin_window_title: str = Field(default="msAdmin", alias="MSADMIN_WINDOW_TITLE")
    msadmin_user: str = Field(default="", alias="MSADMIN_USER")
    msadmin_password: str = Field(default="", alias="MSADMIN_PASSWORD")

    ui_backend: UiBackend = Field(default="mock", alias="UI_BACKEND")

    data_dir: Path = Field(default=Path("./data"), alias="DATA_DIR")
    artifacts_dir: Path = Field(default=Path("./artifacts"), alias="ARTIFACTS_DIR")

    tz: str = Field(default="America/Sao_Paulo", alias="TZ")

    google_credentials_json: str = Field(default="", alias="GOOGLE_CREDENTIALS_JSON")
    google_calendar_id: str = Field(default="", alias="GOOGLE_CALENDAR_ID")

    evolution_base_url: str = Field(default="", alias="EVOLUTION_BASE_URL")
    evolution_api_key: str = Field(default="", alias="EVOLUTION_API_KEY")
    evolution_instance: str = Field(default="", alias="EVOLUTION_INSTANCE")
    whatsapp_from: str = Field(default="", alias="WHATSAPP_FROM")

    agent_enabled: bool = Field(default=False, alias="AGENT_ENABLED")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    agent_model: str = Field(default="gpt-4.1-mini", alias="AGENT_MODEL")

    @property
    def jobs_db_path(self) -> Path:
        return self.data_dir / "jobs.sqlite3"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
