from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
GEMINI_OPENAI_URL = "https://generativelanguage.googleapis.com/v1beta/openai"

# 구간별 허용 페이지 수 (최소, 최대). 도입은 3페이지를 요청하고 2~4를 허용한다.
PAGE_RANGES: dict[str, tuple[int, int]] = {
    "intro": (2, 4),
    "middle": (3, 4),
    "ending": (4, 5),
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    choice_count: int = Field(default=4, ge=2, le=5)
    prompt_version: str = "v9"
    max_page_chars: int = 150

    # 서비스 API: 구간 서명 비밀값, TTS 키, 하루 한도(KST), 허용할 프론트 주소
    story_secret: str = Field(min_length=32)  # 비면 누구나 서명을 만들 수 있다
    gemini_api_key: str = ""
    typecast_api_key: str = ""
    # 안내·선택지 읽기(Azure 무료 F0). 비우면 /api/speak 를 끄고 프론트는 브라우저 음성으로 읽는다
    azure_speech_key: str = ""
    azure_speech_region: str = ""
    daily_stories_per_user: int = 3
    daily_stories_total: int = 30
    cors_origins: list[str] = ["http://localhost:5173"]

    # 이야기 생성 LLM. 모두 Google 모델이라 주소는 기본값, 키는 비우면 GEMINI_API_KEY 를 쓴다
    primary_base_url: str = GEMINI_OPENAI_URL
    primary_api_key: str = ""
    primary_model: str
    primary_json_mode: bool = True
    # 응답 대기 시간(초). 넘으면 그 모델은 실패 (기본·예비는 동시에 부르고 먼저 통과한 글을 씀)
    primary_timeout: float = 60.0

    secondary_base_url: str = GEMINI_OPENAI_URL
    secondary_api_key: str = ""
    secondary_model: str | None = None
    secondary_json_mode: bool = True
    secondary_timeout: float = 60.0

    # 기본·예비와 같이 출발하는 대비 모델 (기본·예비가 모두 실패했을 때만 씀). 비우면 끔
    # Gemma 는 system 역할을 거부하므로 합쳐 보낸다
    backup_models: list[str] = []
    backup_base_url: str = GEMINI_OPENAI_URL
    backup_api_key: str = ""
    backup_json_mode: bool = True
    backup_merge_system: bool = True
    backup_timeout: float = 60.0

    @field_validator("primary_base_url", "secondary_base_url", "backup_base_url", mode="before")
    @classmethod
    def _default_url(cls, v):
        # 예전 .env.example 을 복사한 .env 의 빈 줄(PRIMARY_BASE_URL=)이 기본 주소를 지우지 않게
        return v or GEMINI_OPENAI_URL
