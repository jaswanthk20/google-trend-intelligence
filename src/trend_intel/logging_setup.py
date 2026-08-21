"""Logging that is readable on a laptop and parseable by Cloud Logging.

The old scripts used print(). print() works locally and is nearly useless in
the cloud: there are no levels to filter on, no timestamps, and no way to tie
a line back to the run that emitted it.

Two output modes:

  human  - aligned, coloured-free text for a terminal (the local default)
  json   - one JSON object per line with a "severity" key, which is the exact
           shape Google Cloud Logging parses into structured, filterable
           entries (the automatic choice inside Cloud Functions)
"""

import json
import logging
import os
import sys


# Google Cloud Logging reads a "severity" field. Python's level names line up
# with Cloud's severity names for everything we use.
_CLOUD_SEVERITY = {
    logging.DEBUG: "DEBUG",
    logging.INFO: "INFO",
    logging.WARNING: "WARNING",
    logging.ERROR: "ERROR",
    logging.CRITICAL: "CRITICAL",
}


class _RunIdFilter(logging.Filter):
    """Attach the current run_id to every record, so logs are traceable."""

    def __init__(self, run_id: str | None) -> None:
        super().__init__()
        self.run_id = run_id or "-"

    def filter(self, record: logging.LogRecord) -> bool:
        record.run_id = self.run_id
        return True


class _CloudJsonFormatter(logging.Formatter):
    """Emit one JSON object per line for Cloud Logging."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "severity": _CLOUD_SEVERITY.get(record.levelno, "DEFAULT"),
            "message": record.getMessage(),
            "logger": record.name,
            "run_id": getattr(record, "run_id", "-"),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def _running_in_cloud() -> bool:
    """True inside Cloud Functions / Cloud Run, which set K_SERVICE."""
    return bool(os.getenv("K_SERVICE"))


def configure_logging(run_id: str | None = None, level: int = logging.INFO) -> None:
    """Install handlers. Call once, at the start of the pipeline."""
    use_json = _running_in_cloud() or os.getenv("TREND_INTEL_JSON_LOGS") == "1"

    # The Windows console defaults to cp1252, which cannot encode emoji or
    # CJK characters. YouTube video titles routinely contain both, so logging
    # one would raise UnicodeEncodeError inside the handler. Force UTF-8.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        # Not a real stream (captured by pytest, redirected in a container).
        pass

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_RunIdFilter(run_id))

    if use_json:
        handler.setFormatter(_CloudJsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s  %(levelname)-7s [%(run_id).8s] %(message)s",
                datefmt="%H:%M:%S",
            )
        )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    # googleapiclient logs a warning about file_cache on every run that is
    # noise, not signal. Silence it without hiding real API errors.
    logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)


def get_logger(name: str) -> logging.Logger:
    """Module-level logger. Use get_logger(__name__) in every module."""
    return logging.getLogger(name)
