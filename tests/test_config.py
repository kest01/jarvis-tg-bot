import pytest

from app.config import ConfigError, Settings

BASE_ENV: dict[str, str] = {
    "TELEGRAM_BOT_TOKEN": "token",
    "ALLOWED_USER_IDS": "1, 2",
    "ROUTERAI_API_KEY": "key",
    "DEFAULT_MODEL": "some-model",
}


def test_defaults_are_applied() -> None:
    settings = Settings.from_env(BASE_ENV)

    assert settings.allowed_user_ids == frozenset({1, 2})
    assert settings.routerai_base_url == "https://routerai.ru/api/v1"
    assert settings.db_path == "/data/app.db"
    assert settings.max_tokens_default == 1500
    assert settings.scheduler_tick_seconds == 20
    assert settings.log_level == "INFO"
    assert settings.target_chats == {}


@pytest.mark.parametrize(
    "missing", ["TELEGRAM_BOT_TOKEN", "ALLOWED_USER_IDS", "ROUTERAI_API_KEY", "DEFAULT_MODEL"]
)
def test_required_variables_are_enforced(missing: str) -> None:
    env = {key: value for key, value in BASE_ENV.items() if key != missing}

    with pytest.raises(ConfigError, match=missing):
        Settings.from_env(env)


def test_target_chats_parsed_from_json() -> None:
    env = {**BASE_ENV, "TARGET_CHATS": '{"family": -100123, "work": -100456}'}

    assert Settings.from_env(env).target_chats == {"family": -100123, "work": -100456}


@pytest.mark.parametrize("raw", ["not json", "[1, 2]", '{"family": "-100"}', '{"x": true}'])
def test_target_chats_rejects_invalid_values(raw: str) -> None:
    with pytest.raises(ConfigError, match="TARGET_CHATS"):
        Settings.from_env({**BASE_ENV, "TARGET_CHATS": raw})


@pytest.mark.parametrize("raw", ["abc", "1,x", " , "])
def test_allowlist_rejects_invalid_values(raw: str) -> None:
    with pytest.raises(ConfigError, match="ALLOWED_USER_IDS"):
        Settings.from_env({**BASE_ENV, "ALLOWED_USER_IDS": raw})


def test_invalid_log_level_is_rejected() -> None:
    with pytest.raises(ConfigError, match="LOG_LEVEL"):
        Settings.from_env({**BASE_ENV, "LOG_LEVEL": "LOUD"})


def test_non_positive_integer_is_rejected() -> None:
    with pytest.raises(ConfigError, match="MAX_RUB_PER_DAY"):
        Settings.from_env({**BASE_ENV, "MAX_RUB_PER_DAY": "0"})
