"""Application settings loaded from environment variables (SPEC §9)."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass, field

DEFAULT_ROUTERAI_BASE_URL = "https://routerai.ru/api/v1"


class ConfigError(ValueError):
    """Raised when a required variable is missing or a value is malformed."""


def _required(env: Mapping[str, str], name: str) -> str:
    value = env.get(name, "").strip()
    if not value:
        raise ConfigError(f"{name} is required")
    return value


def _int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc
    if value < 1:
        raise ConfigError(f"{name} must be >= 1, got {value}")
    return value


def _allowed_user_ids(raw: str) -> frozenset[int]:
    try:
        ids = frozenset(int(part) for part in raw.split(",") if part.strip())
    except ValueError as exc:
        raise ConfigError("ALLOWED_USER_IDS must be a comma-separated list of integers") from exc
    if not ids:
        raise ConfigError("ALLOWED_USER_IDS must contain at least one user id")
    return ids


def _target_chats(raw: str) -> dict[str, int]:
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigError("TARGET_CHATS must be valid JSON") from exc
    if not isinstance(data, dict) or not all(
        isinstance(alias, str) and isinstance(chat_id, int) and not isinstance(chat_id, bool)
        for alias, chat_id in data.items()
    ):
        raise ConfigError("TARGET_CHATS must be a JSON object mapping alias to integer chat id")
    return dict(data)


def _log_level(raw: str) -> str:
    level = raw.strip().upper() or "INFO"
    if level not in logging.getLevelNamesMapping():
        raise ConfigError(f"LOG_LEVEL is not a valid logging level: {raw!r}")
    return level


@dataclass(frozen=True, slots=True)
class Settings:
    """Typed runtime configuration. Secrets come only from the environment."""

    telegram_bot_token: str
    allowed_user_ids: frozenset[int]
    routerai_api_key: str
    default_model: str
    routerai_base_url: str = DEFAULT_ROUTERAI_BASE_URL
    db_path: str = "/data/app.db"
    max_db_size_mb: int = 4096
    target_chats: dict[str, int] = field(default_factory=dict)
    max_tokens_default: int = 1500
    max_rub_per_day: int = 100
    rate_limit_seconds: int = 3
    context_token_budget: int = 24000
    summary_trigger_messages: int = 40
    retention_days_history: int = 180
    retention_days_audit: int = 90
    scheduler_tick_seconds: int = 20
    log_level: str = "INFO"

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> Settings:
        """Build settings from a mapping (normally `os.environ`).

        Inputs: environment mapping.
        Output: validated `Settings`.
        Failure: raises `ConfigError` when a required variable is missing or a value is invalid.
        """
        return cls(
            telegram_bot_token=_required(env, "TELEGRAM_BOT_TOKEN"),
            allowed_user_ids=_allowed_user_ids(_required(env, "ALLOWED_USER_IDS")),
            routerai_api_key=_required(env, "ROUTERAI_API_KEY"),
            default_model=_required(env, "DEFAULT_MODEL"),
            routerai_base_url=env.get("ROUTERAI_BASE_URL", "").strip() or DEFAULT_ROUTERAI_BASE_URL,
            db_path=env.get("DB_PATH", "").strip() or "/data/app.db",
            max_db_size_mb=_int(env, "MAX_DB_SIZE_MB", 4096),
            target_chats=_target_chats(env.get("TARGET_CHATS", "")),
            max_tokens_default=_int(env, "MAX_TOKENS_DEFAULT", 1500),
            max_rub_per_day=_int(env, "MAX_RUB_PER_DAY", 100),
            rate_limit_seconds=_int(env, "RATE_LIMIT_SECONDS", 3),
            context_token_budget=_int(env, "CONTEXT_TOKEN_BUDGET", 24000),
            summary_trigger_messages=_int(env, "SUMMARY_TRIGGER_MESSAGES", 40),
            retention_days_history=_int(env, "RETENTION_DAYS_HISTORY", 180),
            retention_days_audit=_int(env, "RETENTION_DAYS_AUDIT", 90),
            scheduler_tick_seconds=_int(env, "SCHEDULER_TICK_SECONDS", 20),
            log_level=_log_level(env.get("LOG_LEVEL", "")),
        )
