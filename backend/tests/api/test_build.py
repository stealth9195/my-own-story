from app.config import Settings
from app.main import build_clients

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai"


def settings(**kw) -> Settings:
    kw = {"primary_model": "m1", "story_secret": "s" * 32, "gemini_api_key": "gk", **kw}
    return Settings(_env_file=None, **kw)


def test_timeouts_from_settings():
    primary, secondary, _ = build_clients(settings(primary_timeout=20, secondary_model="m2",
                                                   secondary_timeout=25))
    assert primary._http.timeout.read == 20 and secondary._http.timeout.read == 25
    assert (primary.model, secondary.model) == ("m1", "m2")


def test_default_timeout_and_no_secondary():
    primary, secondary, backups = build_clients(settings())
    assert primary._http.timeout.read == 60 and secondary is None and backups == []


def test_google_defaults_use_gemini_key():
    # 모두 Google 모델이라 주소는 기본값, 키는 GEMINI_API_KEY 하나만 넣으면 된다
    primary, secondary, backups = build_clients(settings(secondary_model="m2",
                                                         backup_models=["g1", "g2"]))
    for client in (primary, secondary, *backups):
        assert client._url == GEMINI_URL + "/chat/completions"
        assert client._http.headers["Authorization"] == "Bearer gk"


def test_backups_merge_system_for_gemma():
    # Gemma 는 system 역할을 거부한다
    _, _, backups = build_clients(settings(backup_models=["gemma-4-26b-a4b-it", "gemma-4-31b-it"]))
    assert [b.model for b in backups] == ["gemma-4-26b-a4b-it", "gemma-4-31b-it"]
    assert all(b.merge_system for b in backups)


def test_own_key_overrides_gemini_key():
    primary, _, _ = build_clients(settings(primary_api_key="own"))
    assert primary._http.headers["Authorization"] == "Bearer own"


def test_empty_base_url_uses_default():
    # 예전 .env.example 을 복사한 .env 에는 PRIMARY_BASE_URL= 처럼 빈 줄이 남아 있다
    primary, secondary, backups = build_clients(settings(primary_base_url="", secondary_base_url="",
                                                         backup_base_url="", secondary_model="m2",
                                                         backup_models=["g1"]))
    for client in (primary, secondary, *backups):
        assert client._url == GEMINI_URL + "/chat/completions"
