"""Structured JSON logging to stdout (SPEC §10)."""

from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(level: str) -> None:
    """Configure structlog (JSON to stdout) and route stdlib logging through stdout.

    Inputs: level name such as "INFO" (already validated by `Settings`).
    Output: none; global logging configuration is changed.
    Failure: none expected.
    """
    numeric_level = logging.getLevelNamesMapping()[level]

    logging.basicConfig(
        level=numeric_level,
        stream=sys.stdout,
        format="%(levelname)s %(name)s %(message)s",
        force=True,
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )
