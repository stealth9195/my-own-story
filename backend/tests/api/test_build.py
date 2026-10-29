from app.config import Settings
from app.main import build_clients


def settings(**kw) -> Settings:
    return Settings(primary_base_url="https://p", primary_api_key="k", primary_model="m1",
                    story_secret="s" * 32, _env_file=None, **kw)


def test_timeouts_from_settings():
    primary, secondary = build_clients(settings(primary_timeout=20, secondary_base_url="https://s",
                                                secondary_api_key="k", secondary_model="m2",
                                                secondary_timeout=25))
    assert primary._http.timeout.read == 20 and secondary._http.timeout.read == 25
    assert (primary.model, secondary.model) == ("m1", "m2")


def test_default_timeout_and_no_secondary():
    primary, secondary = build_clients(settings())
    assert primary._http.timeout.read == 60 and secondary is None
