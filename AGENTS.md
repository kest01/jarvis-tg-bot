# AGENTS.md

## Project

Personal Telegram AI assistant. Python 3.12, aiogram 3, OpenAI SDK against
routerai.ru, SQLite, Docker on Amvera. Single process, long polling, three layers
(`bot/handlers` → `services` → `infra`). Stage 1 is dialogue + voice + model switching;
stage 2 is tool calling (send to chat, scheduled messages).

## Read order before writing code

1. `SPEC.md` — requirements, schema, ports, config. Source of truth.
2. `.roo/rules/01-arch.md` — binding architectural constraints.
3. `docs/adr/` — decisions already made and their rationale.
4. The file you are about to edit, and its neighbours.

## Non-negotiables

- Import direction is downward only. Handlers never touch `openai`/`sqlalchemy`;
  services never import `aiogram` or concrete adapters.
- Every external call goes through a `Protocol` in `infra/*/base.py`.
- No state in memory that must survive a restart — it goes to the DB.
- No binaries or base64 in the DB.
- No side effects from a tool without user confirmation.
- Never send to a `chat_id` the model produced; only to aliases from `chat_targets`.
- Secrets come from env. Never hardcode, never log, never commit.

## Do not

- Add dependencies, tables, columns, or config flags "proactively".
- Introduce LangChain, Redis, Celery, APScheduler, FastAPI, Postgres.
- Edit `amvera.yml`, `Dockerfile`, `.env*`. Deploying is the human's job.
- Refactor files outside the current task.
- Invent requirements. If SPEC is silent, stop and ask.

## Task shape that works

> "Implement `infra/llm/base.py` and `infra/llm/routerai.py`, plus a fake in
> `tests/fakes.py` and a test that the reply maps tokens correctly."

Not: "implement the bot". One layer, one port, or one tool per task.

## Definition of done

- [ ] Code matches SPEC; no new requirement invented.
- [ ] Layers respected; nothing imported in the wrong direction.
- [ ] Types complete; `ruff` and `black` clean.
- [ ] Test added that runs offline; fakes used for adapters.
- [ ] Errors produce a short Russian user message and a structured log line.
- [ ] No secrets, no dead code, no TODOs without a SPEC reference.

## When blocked

If the task cannot be done inside these rules, do not force it. Write a short note
describing the conflict and the smallest port or ADR that would resolve it, and ask.

Аgent speaks only English.