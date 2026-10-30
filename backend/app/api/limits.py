"""하루·한 달 한도를 서버 메모리에서 센다. 서버가 다시 켜지면 0부터 다시 센다.
실제 한도는 Gemini·Typecast 가 따로 막으므로(429·402), 여기서 넘쳐도 과금은 없고 그 구간이 글만 나온다."""

import threading
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo

KST = timezone(timedelta(hours=9))
PACIFIC = ZoneInfo("America/Los_Angeles")  # Gemini 무료 한도는 태평양 시간 자정(KST 16~17시)에 초기화
GEMINI_DAILY_CALLS = 10      # TTS 모델마다 하루 10회
TYPECAST_MONTHLY_CHARS = 15000
AZURE_DAILY_CHARS = 15000    # Azure 무료 월 50만 자를 하루로 나눈 것보다 조금 적게
TTS_TRIES_PER_SEGMENT = 2    # 첫 시도 + 다시 시도
GENERATIONS_PER_SEGMENT = 2  # 같은 구간을 다시 요청해 LLM 한도를 다 쓰지 못하게


class Limits:
    def __init__(self, per_user: int, total: int, clock: Callable[[], datetime] = lambda: datetime.now(KST)):
        self.per_user = per_user
        self.total = total
        self._clock = clock
        self._counts: defaultdict[tuple, int] = defaultdict(int)
        self._lock = threading.Lock()  # FastAPI 가 동기 엔드포인트를 여러 스레드에서 실행

    def _day(self) -> str:
        return self._clock().astimezone(KST).strftime("%Y-%m-%d")

    def _month(self) -> str:
        return self._clock().astimezone(KST).strftime("%Y-%m")

    def try_start_story(self, anon_id: str) -> Literal["ok", "user_limit", "total_limit"]:
        day = self._day()
        with self._lock:
            if self._counts[(day, "user", anon_id)] >= self.per_user:
                return "user_limit"
            if self._counts[(day, "total")] >= self.total:
                return "total_limit"
            self._counts[(day, "user", anon_id)] += 1
            self._counts[(day, "total")] += 1
            return "ok"

    def cancel_start(self, anon_id: str) -> None:
        """첫 구간을 못 만들었으면 센 것을 되돌린다. 배포 사고(2026-10-31): 글 만들기가 매번 실패했는데
        다시하기 세 번에 하루 3편을 다 써 '내일 또 만나요'가 떴다"""
        day = self._day()
        with self._lock:
            for key in ((day, "user", anon_id), (day, "total")):
                self._counts[key] = max(0, self._counts[key] - 1)

    def _gemini_key(self, model: str) -> tuple:
        return (self._clock().astimezone(PACIFIC).strftime("%Y-%m-%d"), "gemini", model)

    def gemini_left(self, model: str) -> int:
        if self._counts[self._gemini_key(model) + ("used_up",)]:
            return 0
        return GEMINI_DAILY_CALLS - self._counts[self._gemini_key(model)]

    def mark_gemini_used_up(self, model: str) -> None:
        """Google 이 '오늘 한도를 다 썼다'(429 하루 한도)고 하면 그 모델은 오늘 더 쓰지 않는다.
        서버를 다시 켜면 메모리 계산이 0부터라 실제 사용량과 어긋날 수 있어서 (2026-10-30)"""
        with self._lock:
            self._counts[self._gemini_key(model) + ("used_up",)] = 1

    def gemini_used_up(self, model: str) -> bool:
        return bool(self._counts[self._gemini_key(model) + ("used_up",)])

    def reserve_gemini(self, model: str, calls: int) -> None:
        with self._lock:
            self._counts[self._gemini_key(model)] += calls

    def typecast_left(self) -> int:
        return TYPECAST_MONTHLY_CHARS - self._counts[(self._month(), "typecast")]

    def reserve_typecast(self, chars: int) -> None:
        with self._lock:
            self._counts[(self._month(), "typecast")] += chars

    # 시연용 ElevenLabs: 유료 크레딧을 한꺼번에 다 쓰지 않게 하루 글자 수 상한 (설정 ELEVENLABS_DAILY_CHARS)
    def elevenlabs_left(self, daily_chars: int) -> int:
        return daily_chars - self._counts[(self._day(), "elevenlabs")]

    def reserve_elevenlabs(self, chars: int) -> None:
        with self._lock:
            self._counts[(self._day(), "elevenlabs")] += chars

    def azure_left(self) -> int:
        return AZURE_DAILY_CHARS - self._counts[(self._day(), "azure")]

    def reserve_azure(self, chars: int) -> None:
        with self._lock:
            self._counts[(self._day(), "azure")] += chars

    def _allow(self, key: tuple, cap: int) -> bool:
        with self._lock:
            if self._counts[key] >= cap:
                return False
            self._counts[key] += 1
            return True

    def tts_requests(self, story_id: str, index: int) -> int:
        return self._counts[(self._day(), "tts", story_id, index)]

    def allow_tts(self, story_id: str, index: int) -> bool:
        return self._allow((self._day(), "tts", story_id, index), TTS_TRIES_PER_SEGMENT)

    def allow_generate(self, story_id: str, index: int) -> bool:
        return self._allow((self._day(), "generate", story_id, index), GENERATIONS_PER_SEGMENT)
