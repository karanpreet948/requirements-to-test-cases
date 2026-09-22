"""Centralized, configurable logging setup for the rtc package.

The CLI exposes ``--log-level`` so users can control verbosity without
touching code. Library consumers can also call :func:`configure_logging`
directly, or simply rely on Python logging defaults (this package never
calls ``logging.basicConfig`` at import time, to avoid surprising library
consumers).
"""

from __future__ import annotations

import logging
import sys

DEFAULT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configure_logging(level: str = "INFO") -> None:
    """Configure the root logger for console output.

    Parameters
    ----------
    level:
        A standard logging level name, case-insensitive
        (e.g. ``"DEBUG"``, ``"INFO"``, ``"WARNING"``, ``"ERROR"``).

    Raises
    ------
    ValueError
        If ``level`` is not a recognized logging level name.
    """
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level!r}")

    root = logging.getLogger()
    root.setLevel(numeric_level)

    # Avoid duplicate handlers if configure_logging is called more than once
    # (e.g. in tests that exercise the CLI multiple times in one process).
    root.handlers.clear()

    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter(DEFAULT_FORMAT))
    root.addHandler(handler)
