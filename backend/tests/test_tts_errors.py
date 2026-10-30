"""Google 429 오류에서 어떤 한도인지(하루·분당) 뽑아 남긴다.
겪은 문제(2026-10-30): 오류 본문을 400자에서 잘라 한도 이름이 빠졌고, 하루 한도 기억이 작동하지 않았다"""
import json

import pytest

from app.api.tts_service import is_daily_quota
from app.tts import gemini


def google_429(quota_id: str) -> str:
    return json.dumps({"error": {
        "code": 429,
        "message": "You exceeded your current quota, please check your plan and billing details. " * 3,
        "status": "RESOURCE_EXHAUSTED",
        "details": [
            {"@type": "type.googleapis.com/google.rpc.QuotaFailure", "violations": [{
                "quotaMetric": "generativelanguage.googleapis.com/generate_content_free_tier_requests",
                "quotaId": quota_id, "quotaValue": "10"}]},
            {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "31s"},
        ]}})


class Resp:
    def __init__(self, text):
        self.status_code, self.text = 429, text

    def json(self):
        return json.loads(self.text)


@pytest.mark.parametrize("quota_id,daily", [
    ("GenerateRequestsPerDayPerProjectPerModel-FreeTier", True),
    ("GenerateRequestsPerMinutePerProjectPerModel-FreeTier", False),
])
def test_quota_id_is_kept_and_classified(monkeypatch, quota_id, daily):
    monkeypatch.setattr(gemini.httpx, "post", lambda *a, **k: Resp(google_429(quota_id)))
    with pytest.raises(gemini.TTSError) as info:
        gemini.synthesize("안녕", "Kore", "k")
    assert quota_id in str(info.value)
    assert "31s" in str(info.value)        # 언제 다시 되는지
    assert is_daily_quota(info.value) is daily
