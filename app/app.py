"""Composition root: the only place where layers are wired together.

Runs aiogram long polling and shuts down cleanly on SIGINT/SIGTERM.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import signal
import sys

import structlog
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import ConfigError, Settings
from app.logging_setup import configure_logging
from bot.handlers.root import build_router

log = structlog.get_logger(__name__)


def _install_signal_handlers(stop: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:  # Windows event loop does not support add_signal_handler
            signal.signal(sig, lambda _signum, _frame: loop.call_soon_threadsafe(stop.set))


async def run(settings: Settings) -> None:
    """Run long polling until a shutdown signal arrives or polling fails.

    Inputs: validated settings.
    Output: none; returns after shutdown.
    Failure: exceptions raised by polling propagate after the bot session is closed.
    """
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()
    dispatcher.include_router(build_router())

    stop = asyncio.Event()
    _install_signal_handlers(stop)

    polling = asyncio.create_task(dispatcher.start_polling(bot, handle_signals=False))
    stopper = asyncio.create_task(stop.wait())
    try:
        await asyncio.wait({polling, stopper}, return_when=asyncio.FIRST_COMPLETED)
    finally:
        log.info("shutdown_started")
        polling.cancel()
        stopper.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await polling
        await bot.session.close()
        log.info("shutdown_complete")


def main() -> None:
    """Load configuration, configure logging and start the bot.

    Exits with a message on stderr when configuration is invalid.
    """
    try:
        settings = Settings.from_env(os.environ)
    except ConfigError as exc:
        sys.exit(f"configuration error: {exc}")

    configure_logging(settings.log_level)
    log.info("starting", default_model=settings.default_model)
    asyncio.run(run(settings))
