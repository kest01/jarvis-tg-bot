# SPEC — Telegram AI Assistant (routerai.ru)

Version 1.0. Source of truth for requirements. If code diverges from SPEC, the code is wrong.
Deviations are recorded as ADRs in `docs/adr/NNNN-*.md`.

## 1. Purpose

Personal Telegram bot: dialogue with a selectable LLM via routerai.ru (OpenAI-compatible API),
voice input, and (stage 2) actions in the outside world.

- **Users:** single owner; access limited by `ALLOWED_USER_IDS`. Everyone else is ignored and costs nothing.
- **Out of scope:** multi-tenancy, billing, web UI, inline mode, RAG/vector memory,
  streaming, custom model routing.

## 2. Stage 1 — dialogue

| ID | Requirement |
|---|---|
| FR-1.1 | Text messages in private and group chats, answered by the selected model with history. |
| FR-1.2 | Default model from `DEFAULT_MODEL`; `/model` switches via inline keyboard, stored per chat (`chats.model_code`). |
| FR-1.6 | `/reset` starts a new `session_id` and clears `summary`; old messages are kept. |
| FR-1.7 | System prompt in `chats.system_prompt` (default `prompts/default_system.md`), edited via `/prompt`, every change logged in `prompt_versions`. |
| FR-1.8 | Context always includes an environment block: current date/time with user's UTC offset, user name, chat id, model. |
| FR-1.9 | Replies split at paragraph boundaries to fit the Telegram message limit; HTML formatting. |
| FR-1.10 | `/usage` shows requests, tokens, cost for today and 30 days. Requests are rejected above `MAX_RUB_PER_DAY`. |

**Acceptance:** context holds ≥ 20 turns and survives restart; `/model` takes effect on the next reply;
30 s voice message is transcribed, and STT failure yields a clear error without crashing;
photo to non-vision model is refused without an API call; `/reset` clears context but not DB history;
`/prompt` edits apply immediately and are versioned; non-allowlisted users get no reply and no `usage` rows;
`SIGTERM` exits cleanly with `wal_checkpoint(TRUNCATE)`.

## 3. Stage 2 — agent

| ID | Requirement |
|---|---|
| FR-2.1 | Tool registry and tool-calling loop (max 4 iterations). Tools are sent only to models with `tools` capability. |
| FR-2.2 | `send_to_chat` posts to a chat by **alias** from `chat_targets`. Raw `chat_id` from the model is never accepted. |
| FR-2.3 | `schedule_message` creates a delayed message in `scheduled_messages`. |
| FR-2.4 | `list_scheduled` and `cancel_scheduled` manage pending items. |
| FR-2.5 | Tools with `requires_confirmation = true` run only after inline-button confirmation; requests stored in `pending_actions`. |
| FR-2.6 | Background ticker every `SCHEDULER_TICK_SECONDS` atomically claims due rows and sends them; survives restarts, no duplicates. |
| FR-2.7 | Unknown or disabled alias is rejected. |
| FR-2.8 | Every tool call is written to `tool_audit`. |

**Acceptance:** "add buying a phone to the to-do list" → confirmation → message appears in target chat;
"remind me at 17:00 to turn off the stove" → scheduled, sent at 17:00 ± tick, not lost or duplicated after restart;
non-tool models answer normally; cancel sends nothing; invented alias is refused.

## 4. Commands

| Command | Stage | Behavior |
|---|---|---|
| `/start`, `/help` | 1 | Greeting, help, current model. |
| `/model` | 1 | Model keyboard, current marked. |
| `/reset` | 1 | New session. |
| `/cancel` | 2 | Cancel current pending action. |

Unknown commands: one short hint, no spam.

## 5. Data rules

Single SQLite DB at `DB_PATH` (default `/data/app.db`); WAL, `busy_timeout`, `foreign_keys=ON`.
Tables: `chats`, `messages`, `chat_targets`, `pending_actions`, `tool_audit`.

- No binary data in the DB: only text and Telegram `file_id`. `messages.content_json` holds OpenAI-format content parts.
- Timestamps: ISO-8601 UTC strings; TZ conversion only at the edges.
- Portable SQLAlchemy only: no `rowid`, `json_extract`, `strftime`.
- Index `messages(chat_id, id DESC)`; scheduler index on `(status, run_at_utc)`.

## 6. Ports (`Protocol` in `infra/*/base.py`)

- `LLMClient.complete(model, messages, tools, max_tokens, temperature) -> LLMReply(content, tool_calls, tokens_in, tokens_out, raw)`; `list_models()`.
- `Transcriber.transcribe(audio, filename) -> Transcript(text, language, duration_sec)`.
- `Tool`: `name`, `description`, `parameters` (JSON Schema), `requires_confirmation`,
  `requires_capability`, `execute(ctx, **kwargs) -> ToolResult(ok, summary, data)`.

Adapters: `infra/llm/routerai.py` (`AsyncOpenAI`), `infra/stt/yandex.py`, `infra/stt/whisper_api.py`.
Fakes: `tests/fakes.py`.

## 7. Tools (stage 2)

- `send_to_chat(target: str, text: str)`
- `schedule_message(target: str, text: str, run_at: ISO-8601 with offset)`
- `list_scheduled()` — current chat
- `cancel_scheduled(id: int)`
- `get_current_time()` — service tool

Validation in code, not in the prompt: `run_at` in the future and ≤ 365 days, alias exists and enabled,
text ≤ 3800 chars. Errors return to the model as `tool` messages.

## 8. Context assembly

1. System part = `system_prompt` + `## Environment` block + optional `## Summary` from `chats.summary`.
2. Take current-session messages newest-first until `max_context_messages` (30) or
   `CONTEXT_TOKEN_BUDGET` (24000) is reached. Token estimate: `ceil(len/3) + 200` per non-text part.
3. Restore chronological order; `tool` role messages are excluded from later requests.
4. If the session exceeds `SUMMARY_TRIGGER_MESSAGES` (40), fold out-of-window messages into
   `chats.summary` (overwrite), best-effort; failures are logged, never block the reply.

## 9. Configuration (env)

| Variable | Required | Default |
|---|---|---|
| `TELEGRAM_BOT_TOKEN`, `ALLOWED_USER_IDS` (CSV), `ROUTERAI_API_KEY`, `DEFAULT_MODEL` | yes | — |
| `ROUTERAI_BASE_URL` | no | `https://routerai.ru/api/v1` |
| `DB_PATH` / `MAX_DB_SIZE_MB` | no | `/data/app.db` / `4096` |
| `TARGET_CHATS` (JSON alias → chat id; seeds `chat_targets`) | no | `{}` |
| `MAX_TOKENS_DEFAULT` / `MAX_RUB_PER_DAY` | no | `1500` / `100` |
| `RATE_LIMIT_SECONDS` | no | `3` |
| `CONTEXT_TOKEN_BUDGET` / `SUMMARY_TRIGGER_MESSAGES` | no | `24000` / `40` |
| `RETENTION_DAYS_HISTORY` / `RETENTION_DAYS_AUDIT` | no | `180` / `90` |
| `SCHEDULER_TICK_SECONDS` / `LOG_LEVEL` | no | `20` / `INFO` |

Secrets only in env; `.env` is gitignored; `.env.example` has empty values.

## 10. Non-functional

- **Restart-safe:** no meaningful in-memory state. On SIGTERM: stop polling, cancel tasks,
  `wal_checkpoint(TRUNCATE)`, dispose engine.
- **Cost:** every LLM call recorded in `usage`; missing prices → cost NULL, tokens still counted.
- **Errors:** short Russian message to the user, structured JSON log (`structlog`) with
  `chat_id`, `tool`, `model`, duration. A handler failure never stops polling.
- **Logs:** stdout only; secrets masked.
- **Latency:** typing indicator before the LLM call; timeouts: LLM 120 s, STT 60 s.
- **Telegram limits:** file ≤ 20 MB, audio ≤ 300 s, replies ≤ 4096 chars per message.
- **Retention (daily):** delete `messages` older than `RETENTION_DAYS_HISTORY`, `usage`/`tool_audit`
  older than `RETENTION_DAYS_AUDIT`; weekly `VACUUM` if `freelist_count / page_count` > 0.2.
- **Backup (daily):** `VACUUM INTO '/data/backups/app-YYYYMMDD.db'`, keep 3.
- **Deploy:** Docker on Amvera, long polling, persistent disk at `/data`.

## 11. Glossary

- **Port:** `Protocol` describing an external dependency.
- **Adapter:** implementation of a port.
- **Service:** orchestration code in `services/`.
- **Capability:** model flag (`vision`, `tools`, `audio_in`) in `models.capabilities`.