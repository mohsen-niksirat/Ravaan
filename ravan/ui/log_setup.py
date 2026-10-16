"""Logging configuration for Ravan with capped rotating file handler."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from ravan.core.config import config_dir


def setup_logging(level: int = logging.INFO) -> None:
    """Initialize structured logging to rotating log file and console."""
    log_dir = config_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "ravan.log"

    root = logging.getLogger()
    root.setLevel(level)

    for h in list(root.handlers):
        root.removeHandler(h)

    # 2 MB max size, 3 backup rotations (ravan.log, ravan.log.1, ...)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    root.addHandler(stream_handler)
