from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]

# 구간별 허용 페이지 수 (최소, 최대). 도입은 3페이지를 요청하고 2~4를 허용한다.
PAGE_RANGES: dict[str, tuple[int, int]] = {
    "intro": (2, 4),
    "middle": (3, 4),
    "ending": (4, 5),
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    choice_count: int = Field(default=4, ge=2, le=5)
    prompt_version: str = "v8"
    max_page_chars: int = 150

    # 서비스 API: 구간 서명 비밀값, TTS 키, 하루 한도(KST), 허용할 프론트 주소
    story_secret: str
    gemini_api_key: str = ""
    typecast_api_key: str = ""
    daily_stories_per_user: int = 3
    daily_stories_total: int = 30
    cors_origins: list[str] = ["http://localhost:5173"]

    primary_base_url: str
    primary_api_key: str
    primary_model: str
    primary_json_mode: bool = True

    secondary_base_url: str | None = None
    secondary_api_key: str | None = None
    secondary_model: str | None = None
    secondary_json_mode: bool = True
