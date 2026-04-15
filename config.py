from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"))

@dataclass(frozen=True)
class Settings:
    openweather_api_key: str
    openweather_base_url: str
    http_timeout_seconds: float


def get_settings() -> Settings:
    openweather_api_key = os.getenv("OPENWEATHER_API_KEY", "").strip()
    if not openweather_api_key:
        raise RuntimeError("Missing OPENWEATHER_API_KEY in environment/.env")

    openweather_base_url = os.getenv(
        "OPENWEATHER_BASE_URL", "https://api.openweathermap.org/data/2.5"
    ).strip()

    http_timeout_seconds_str = os.getenv("HTTP_TIMEOUT_SECONDS", "10").strip()
    try:
        http_timeout_seconds = float(http_timeout_seconds_str)
    except ValueError as exc:
        raise RuntimeError("HTTP_TIMEOUT_SECONDS must be a number") from exc

    if http_timeout_seconds <= 0:
        raise RuntimeError("HTTP_TIMEOUT_SECONDS must be > 0")

    return Settings(
        openweather_api_key=openweather_api_key,
        openweather_base_url=openweather_base_url,
        http_timeout_seconds=http_timeout_seconds,
    )
