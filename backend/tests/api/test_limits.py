from datetime import datetime, timedelta, timezone

from app.api.limits import Limits

KST = timezone(timedelta(hours=9))


class Clock:
    def __init__(self, now: datetime):
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def test_user_limit():
    limits = Limits(per_user=3, total=30, clock=Clock(datetime(2026, 10, 29, 12, tzinfo=KST)))
    assert [limits.try_start_story("a") for _ in range(4)] == ["ok", "ok", "ok", "user_limit"]
    assert limits.try_start_story("b") == "ok"


def test_total_limit():
    limits = Limits(per_user=3, total=2, clock=Clock(datetime(2026, 10, 29, 12, tzinfo=KST)))
    assert [limits.try_start_story(i) for i in "abc"] == ["ok", "ok", "total_limit"]


def test_resets_at_kst_midnight():
    clock = Clock(datetime(2026, 10, 29, 23, 59, tzinfo=KST))
    limits = Limits(per_user=3, total=30, clock=clock)
    for _ in range(3):
        limits.try_start_story("a")
    assert limits.try_start_story("a") == "user_limit"
    # UTC 로 주어도 KST 날짜 기준 (KST 10/30 00:00 = UTC 10/29 15:00)
    clock.now = datetime(2026, 10, 29, 15, 0, tzinfo=timezone.utc)
    assert limits.try_start_story("a") == "ok"


def test_gemini_reserve():
    limits = Limits(per_user=3, total=30, clock=Clock(datetime(2026, 10, 29, 12, tzinfo=KST)))
    limits.reserve_gemini("m", 5)
    assert limits.gemini_left("m") == 5
    assert limits.gemini_left("other") == 10


def test_typecast_monthly():
    clock = Clock(datetime(2026, 10, 31, 12, tzinfo=KST))
    limits = Limits(per_user=3, total=30, clock=clock)
    limits.reserve_typecast(15000)
    assert limits.typecast_left() == 0
    clock.now = datetime(2026, 11, 1, 0, 0, tzinfo=KST)
    assert limits.typecast_left() == 15000


def test_allow_tts_twice():
    limits = Limits(per_user=3, total=30, clock=Clock(datetime(2026, 10, 29, 12, tzinfo=KST)))
    assert [limits.allow_tts("a", 0) for _ in range(3)] == [True, True, False]
    assert limits.allow_tts("a", 1) is True


def test_gemini_resets_at_pacific_midnight():
    # Gemini 무료 한도는 태평양 시간 자정에 초기화된다 (KST 16~17시)
    clock = Clock(datetime(2026, 10, 30, 10, tzinfo=KST))   # PDT 10/29 18:00
    limits = Limits(per_user=3, total=30, clock=clock)
    limits.reserve_gemini("m", 10)
    clock.now = datetime(2026, 10, 30, 15, tzinfo=KST)      # PDT 10/29 23:00
    assert limits.gemini_left("m") == 0
    clock.now = datetime(2026, 10, 30, 17, tzinfo=KST)      # PDT 10/30 01:00
    assert limits.gemini_left("m") == 10


def test_allow_generate_twice_per_segment():
    limits = Limits(per_user=3, total=30, clock=Clock(datetime(2026, 10, 29, 12, tzinfo=KST)))
    assert [limits.allow_generate("a", 1) for _ in range(3)] == [True, True, False]
    assert limits.allow_generate("a", 2) is True
