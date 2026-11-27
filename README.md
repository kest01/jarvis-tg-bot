# Telegram AI Assistant

Personal Telegram bot acting as an AI assistant. Talks to multiple models through
[routerai.ru](https://routerai.ru) (OpenAI-compatible), switches models per chat,
accepts voice and images, and — on stage 2 — performs actions: posting to configured
chats and scheduling reminders.

Python 3.12 · aiogram 3 · OpenAI SDK · SQLite · Docker on [Amvera](https://amvera.ru)

## Stage 1 — dialogue

- Multi-turn conversation with history kept per chat.
- `/model` — inline keyboard to switch models; choice stored per chat.
- Text, images (vision-capable models), voice (ffmpeg → STT → text).
- Configurable system prompt, editable with `/prompt`.
- `/reset`, `/usage`, daily spend cap, allowlist of users.

## Stage 2 — agent

- Tool calling loop (max 4 iterations), only for models with the `tools` capability.
- `send_to_chat` — post to a chat by alias (`family`, `work`, …), never by raw id.
- `schedule_message`, `list_scheduled`, `cancel_scheduled` — durable reminders.
- Every side effect requires an inline-button confirmation.
- `/targets`, `/tasks`, `/cancel`, full audit in `tool_audit`.

## Architecture

```
bot/handlers   aiogram: commands, text, media, keyboards
services       scenarios: dialog, prompt, transcription, agent, scheduler
infra          adapters behind ports: llm, stt, db, tg
```

Imports flow downward only. Handlers know nothing about the LLM; services know
nothing about aiogram. External calls sit behind `Protocol` in `infra/*/base.py`,
which is what makes the whole thing testable offline.

Full requirements: [`SPEC.md`](SPEC.md). Rules for contributors and agents:
[`AGENTS.md`](AGENTS.md), [`.roo/rules/01-arch.md`](.roo/rules/01-arch.md).

## Quick start

```bash
cp .env.example .env          # fill TELEGRAM_BOT_TOKEN, ALLOWED_USER_IDS,
                              # ROUTERAI_API_KEY, DEFAULT_MODEL
uv sync
uv run python -m app          # requires ffmpeg in PATH
```

`.env.example` keys: `TELEGRAM_BOT_TOKEN`, `ALLOWED_USER_IDS`, `ROUTERAI_API_KEY`,
`ROUTERAI_BASE_URL`, `DEFAULT_MODEL`, `DB_PATH`, `STT_PROVIDER`, `TARGET_CHATS`,
`MAX_RUB_PER_DAY`. The full table lives in `SPEC.md` §9.

## Deployment (Amvera)

Long polling, no domain or TLS needed. Docker image, persistent disk mounted at `/data`.

```bash
git remote add amvera https://git.amvera.ru/<user>/<project>
git push amvera master
```

The SQLite file lives at `/data/app.db` — anything outside `/data` is wiped on rebuild.
Daily `VACUUM INTO /data/backups/` keeps three snapshots.

## Project layout

```
app/            entrypoint, config, DI
bot/handlers/   commands, chat, voice, model menu
services/       dialog, prompt, transcription, scheduler, agent/
infra/          llm/, stt/, db/, tg/
prompts/        default_system.md
tests/          fakes.py, unit tests
```

## Testing

```bash
uv run pytest
```

Tests run offline: `FakeLLM` and `FakeTranscriber` implement the same protocols as the
real adapters, so no API key and no network are needed.

## Status

Stage 1 in development. Stage 2 designed, not implemented. No web UI, no Postgres,
no streaming — by decision, see `SPEC.md` §1.2.