# Architecture rules — binding for all agents

Read `SPEC.md` first. It is the source of truth for requirements, data, ports, tools, config
and non-functional limits. This file defines only architectural constraints and implementation
rules; it does not restate SPEC. Deviations require an ADR in `docs/adr/NNNN-*.md`.

## 1. Layers and import direction

Imports flow strictly downward:

```
bot/handlers  →  services  →  infra
```

- `bot/handlers/*` — aiogram only: parse update, call service, send reply.
  **Forbidden:** `openai`, `httpx`, `sqlalchemy`, `infra.*`.
- `services/*` — business logic. **Forbidden:** `aiogram` and any concrete adapter.
  Only ports (`infra/*/base.py`) and `config`.
- `infra/*` — adapters, DB. **Forbidden:** `services`, `bot`.
- Sole assembly point: `app/app.py`.

If a task "needs" a forbidden import, add a port — do not break the layer.

## 2. External dependencies live behind ports

Every outbound call (LLM, STT, Telegram files, DB) has a `Protocol` in `infra/*/base.py`
(SPEC §6), an adapter next to it, and a fake in `tests/fakes.py`. `services` know only the protocol.

## 3. Forbidden without explicit user approval

- New dependencies: `langchain`, `llama-index`, `redis`, `celery`, `apscheduler`,
  `fastapi`, `django`, any ORM other than SQLAlchemy, any HTTP client other than `httpx`.
- Switching DB to Postgres/MySQL.
- Webhooks, running a web server.
- Editing `amvera.yml`, `Dockerfile`, `.env*`; deploying.
- Sending to an arbitrary `chat_id` supplied by the model (FR-2.2).

## 4. LLM usage

- Single client: `AsyncOpenAI` in `infra/llm/routerai.py`, `base_url` from `ROUTERAI_BASE_URL`.
  No direct `httpx` calls to model APIs.
- Always pass `max_tokens` (SPEC §6).
- Usage recording is best-effort: a failure is logged and never fails the reply.
- A tool with `requires_confirmation = true` is any tool that sends, pays, or mutates external
  state (FR-2.5).

## 5. Tools

- New tool = new class in `services/agent/tools/<name>.py` + registration in
  `services/agent/registry.py`. `dialog.py` and `loop.py` must not change.
- Tool shape (SPEC §6) and argument validation rules (SPEC §7) apply. Validation is done in code.
- Tool errors are returned to the model as `tool` messages; nothing raises into the handler.
- When the loop limit (FR-2.1) is reached, the user gets a flat "couldn't complete" message.

## 6. Persistence

- SQLAlchemy 2.0 async. One engine, created in `app/app.py`.
- Connection pragmas, set before the first table: `journal_mode=WAL`, `synchronous=NORMAL`,
  `busy_timeout=5000`, `foreign_keys=ON`, `auto_vacuum=INCREMENTAL`.
- Transactions are short. No long-running work inside a session.
- No unbounded reads: always `LIMIT` on message history.

## 7. Errors and logging

Requirements (user-facing messages, structured logs, masking, polling survival) are defined in
SPEC §10. No additional rules here.

## 8. Code style

- Python 3.12, full type hints, `async def` for all I/O.
- `ruff` + `black`, line length 100.
- Public functions in `services` have docstrings stating inputs, outputs, and failure modes.
- No dead code, no commented-out blocks, no `TODO` without a SPEC reference.

## 9. Tests

- Every service has a test that runs without network and without Telegram.
- Adapters are exercised against `fakes.py`, not the real API.
- Time-dependent logic is tested with `freezegun`.
- A change that cannot be tested is a design smell — add a port boundary first.

## 10. Agent workflow

- One task = one layer or one tool. Never "build the bot".
- Do not refactor unrelated files in the same change.
- Do not invent requirements. If SPEC is silent, ask; do not decide.
- Do not add config flags, columns, or dependencies "for the future".
