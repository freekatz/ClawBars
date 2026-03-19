"""Structured logging configuration for ClawBars backend."""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import settings


class JSONFormatter(logging.Formatter):
    """Output logs as single-line JSON for structured log aggregation."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            log_entry["exc"] = self.formatException(record.exc_info)
        # Extra fields attached via `logger.info("msg", extra={...})`
        for key in ("request_id", "method", "path", "status", "duration_ms", "user_id", "agent_id"):
            val = getattr(record, key, None)
            if val is not None:
                log_entry[key] = val
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging() -> None:
    """Configure root logger: stdout always, optional rotating file when LOG_DIR is set."""
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    formatter = JSONFormatter()

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    # Stdout (Docker/console)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    root.addHandler(stdout_handler)

    # Optional file logging (e.g. LOG_DIR=/app/logs in Docker)
    log_dir = (settings.log_dir or "").strip()
    if log_dir:
        path = Path(log_dir)
        path.mkdir(parents=True, exist_ok=True)
        log_file = path / "app.log"
        try:
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=settings.log_max_bytes,
                backupCount=settings.log_backup_count,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)
        except OSError:
            root.warning("Could not create log file at %s, file logging disabled", log_file)

    # Quieten noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.debug else logging.WARNING
    )
