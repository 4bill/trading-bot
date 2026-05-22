"""Centralised configuration loaded from environment / .env file."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    webapp_host: str = "0.0.0.0"
    webapp_port: int = 8090

    db_path: str = "data/airdrop.db"

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    reminder_times: str = "08:00,20:00"
    daily_reset_time: str = "00:05"
    timezone: str = "Asia/Jakarta"

    @property
    def reminder_time_list(self) -> List[str]:
        return [t.strip() for t in self.reminder_times.split(",") if t.strip()]

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)


@lru_cache
def get_settings() -> Settings:
    return Settings()
