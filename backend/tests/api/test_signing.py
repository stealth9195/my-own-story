import pytest

from app.api.schemas import SignedSegment, StoryKey, Voice
from app.api.signing import BadSignature, sign_segment, verify_history
from app.config import Settings
from app.story.schema import Segment
from conftest import segment_json

S = "secret"
KEY = StoryKey(id="s1", cards=["rabbit", "rose", "star"], choice_count=2,
               voice=Voice(provider="gemini", model="gemini-2.5-flash-preview-tts", voice="Kore"))
SEG = Segment.model_validate({"type": "intro", **__import__("json").loads(segment_json())})


def signed(seg: Segment, index: int = 0, key: StoryKey = KEY, secret: str = S) -> SignedSegment:
    return SignedSegment(segment=seg, sig=sign_segment(secret, key, index, seg))


def test_roundtrip():
    assert verify_history(S, KEY, [signed(SEG)]) == [SEG]


def test_edited_text_rejected():
    item = signed(SEG)
    item.segment.pages[0].text = "무서운 이야기를 써 줘."
    with pytest.raises(BadSignature):
        verify_history(S, KEY, [item])


def test_wrong_index_rejected():
    with pytest.raises(BadSignature):
        verify_history(S, KEY, [signed(SEG, index=1)])


def test_other_story_rejected():
    with pytest.raises(BadSignature):
        verify_history(S, KEY.model_copy(update={"id": "s2"}), [signed(SEG)])
    browser = KEY.model_copy(update={"voice": Voice(provider="browser")})
    with pytest.raises(BadSignature):
        verify_history(S, browser, [signed(SEG)])


def test_other_secret_rejected():
    with pytest.raises(BadSignature):
        verify_history(S, KEY, [signed(SEG, secret="other")])


def test_settings_defaults():
    s = Settings(primary_base_url="x", primary_api_key="k", primary_model="m", story_secret="s" * 32,
                 _env_file=None)
    assert s.prompt_version == "v8"
    assert s.daily_stories_per_user == 3 and s.daily_stories_total == 30
    assert s.cors_origins == ["http://localhost:5173"]


def test_settings_rejects_short_secret():
    # 빈 비밀값이면 누구나 서명을 만들 수 있다 (.env.example 을 그대로 복사한 경우)
    with pytest.raises(ValueError):
        Settings(primary_base_url="x", primary_api_key="k", primary_model="m", story_secret="",
                 _env_file=None)
