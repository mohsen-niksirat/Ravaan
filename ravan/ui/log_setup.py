"""Logging configuration for Ravan with capped rotating file handler and crash reporting."""

from __future__ import annotations

import logging
import os
import sys
import traceback
from collections.abc import Callable
from datetime import datetime
from logging.handlers import RotatingFileHandler

from ravan.core.config import config_dir

log = logging.getLogger(__name__)


def setup_logging(level: int = logging.INFO) -> None:
    """Initialize structured logging to rotating log file and console."""
    log_dir = config_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "ravan.log"

    root = logging.getLogger()
    root.setLevel(level)

    for h in list(root.handlers):
        root.removeHandler(h)

    # 5 MB max size, 3 backup rotations (ravan.log, ravan.log.1, ...)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
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


def open_logs_folder() -> None:
    """Open the log folder in Windows Explorer."""
    log_dir = config_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.startfile(log_dir)  # type: ignore[attr-defined]
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not open logs folder: %s", exc)


def install_crash_handler(
    on_crash: Callable[[str], None] | None = None,
    show_dialog: bool = True,
) -> None:
    """Register global sys.excepthook that records diagnostic crash report and shows dialog."""
    from ravan.ui.crash_dialog import build_diagnostic_report, show_crash_dialog

    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        crash_dir = config_dir() / "crash"
        crash_dir.mkdir(parents=True, exist_ok=True)
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        crash_file = crash_dir / f"crash_{now_str}.txt"

        last_logs: list[str] = []
        log_file = config_dir() / "logs" / "ravan.log"
        if log_file.is_file():
            try:
                lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
                last_logs = lines[-50:]
            except Exception:  # noqa: BLE001
                pass

        content = build_diagnostic_report(
            exc_type=exc_type,
            exc_value=exc_value,
            exc_tb=exc_traceback,
            recent_logs=last_logs,
        )
        try:
            crash_file.write_text(content, encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass

        tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        log.critical("Uncaught exception written to %s:\n%s", crash_file, tb_text)
        if on_crash:
            try:
                on_crash(f"Ravaan encountered an unexpected error. Report saved to {crash_file.name}")
            except Exception:  # noqa: BLE001
                pass

        if show_dialog and os.environ.get("PYTEST_CURRENT_TEST") is None:
            show_crash_dialog(report_text=content, crash_file=crash_file, interactive=True)

        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    sys.excepthook = handle_exception
