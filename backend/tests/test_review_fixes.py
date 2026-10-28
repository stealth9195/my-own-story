"""최종 검토에서 나온 문제 재현 테스트."""

import io
import json
import sys

import httpx

from app.catalog import load_catalog
from app.llm.client import OpenAICompatClient
from app.story.safety import load_banned_words
from app.story.validator import validate_segment
from conftest import FakeLLM, segment_json

cat = load_catalog()
banned = load_banned_words()
GOOD = segment_json()


def test_json_followed_by_text_with_braces():
    r = validate_segment(GOOD + "\n참고: {pages}는 3개", "intro", cat, banned)
    assert r.ok


def test_text_with_braces_before_json():
    r = validate_segment("형식 {pages}: " + GOOD, "intro", cat, banned)
    assert r.ok


def test_null_optional_fields_use_defaults():
    data = json.loads(GOOD)
    p = data["pages"][0]
    p["scene"]["characters"] = None
    p["scene"]["objects"] = None
    p["scene"]["time"] = None
    p["mood"] = None
    r = validate_segment(json.dumps(data, ensure_ascii=False), "intro", cat, banned)
    assert r.ok
    assert r.segment.pages[0].scene.characters == []
    assert r.segment.pages[0].scene.time == "day"
    assert r.segment.pages[0].mood == "calm"


def test_missing_scene_is_schema_error_not_json():
    data = json.loads(GOOD)
    data["pages"][0]["scene"] = None
    r = validate_segment(json.dumps(data, ensure_ascii=False), "intro", cat, banned)
    assert r.errors == ["schema"]


def test_merge_system_puts_system_prompt_into_user_message():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    client = OpenAICompatClient("https://x/v1", "k", "gemma", merge_system=True,
                                transport=httpx.MockTransport(handler))
    client.complete([{"role": "system", "content": "규칙"}, {"role": "user", "content": "질문"}])
    msgs = seen["body"]["messages"]
    assert [m["role"] for m in msgs] == ["user"]
    assert msgs[0]["content"].startswith("규칙") and "질문" in msgs[0]["content"]


def test_story_records_cards_and_judge_text_shows_them():
    from eval.judge import story_to_text
    from eval.story_runner import run_story

    case = {"id": "c01", "cards": ["rabbit", "rose"], "picks": [0, 0, 0]}
    end = segment_json(pages=4, choices=())
    story = run_story(case, FakeLLM("m", [GOOD, GOOD, end]), cat, banned, 2, "v1")
    assert story["cards"] == ["rabbit", "rose"]
    assert "아이가 고른 카드: 토끼, 장미" in story_to_text(story)


def test_corrupt_result_file_is_regenerated(tmp_path):
    from eval.run_generate import run_model

    (tmp_path / "c01.json").write_text('{"status": "do', encoding="utf-8")
    case = {"id": "c01", "cards": ["rabbit"], "picks": [0, 0]}
    end = segment_json(pages=4, choices=())
    llm = FakeLLM("m", [GOOD, GOOD, end])
    run_model([case], llm, tmp_path, cat, banned, choice_count=2, version="v1")
    assert json.loads((tmp_path / "c01.json").read_text(encoding="utf-8"))["status"] == "done"


def test_tts_google_gets_google_key_in_header(monkeypatch, tmp_path):
    import eval.tts_check as t

    sent = []
    monkeypatch.setattr(t, "OUT_DIR", tmp_path)
    monkeypatch.setenv("GOOGLE_TTS_API_KEY", "GKEY")
    monkeypatch.setenv("AZURE_SPEECH_KEY", "AKEY")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "koreacentral")

    def fake_post(url, **kw):
        sent.append((url, kw.get("headers", {})))
        if "googleapis" in url:
            import base64
            return httpx.Response(200, json={"audioContent": base64.b64encode(b"mp3").decode()},
                                  request=httpx.Request("POST", url))
        return httpx.Response(200, content=b"mp3", request=httpx.Request("POST", url))

    monkeypatch.setattr(t.httpx, "post", fake_post)
    t.main([])
    google_calls = [(u, h) for u, h in sent if "googleapis" in u]
    assert google_calls
    assert all(h.get("X-Goog-Api-Key") == "GKEY" and "key=" not in u for u, h in google_calls)


def test_setup_console_switches_stdout_to_utf8(monkeypatch):
    from eval.console import setup_console

    fake = io.TextIOWrapper(io.BytesIO(), encoding="cp949")
    monkeypatch.setattr(sys, "stdout", fake)
    setup_console()
    assert sys.stdout.encoding.lower().replace("-", "") == "utf8"
