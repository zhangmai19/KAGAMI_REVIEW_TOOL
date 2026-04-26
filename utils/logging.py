"""Logging utilities with rich console support."""

import logging
from typing import Optional

from rich.logging import RichHandler


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """Get a configured logger with rich formatting."""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    log_level = level or logging.INFO
    logger.setLevel(log_level)

    handler = RichHandler(
        show_time=True,
        show_path=False,
        markup=True,
    )
    handler.setLevel(log_level)

    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
