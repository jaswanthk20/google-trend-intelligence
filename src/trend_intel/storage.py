"""All writes to disk go through here.

Isolating persistence in one module means Phase 3 can add a
write_to_bigquery() alongside these functions without touching a single
transform or source. Nothing else in the package is allowed to call
open() or DataFrame.to_csv() directly.

Filenames embed the run's timestamp slug so runs never overwrite each other,
and every raw artifact carries run_id/collected_at inside it so a file that
gets renamed or moved is still traceable.
"""

import json
from pathlib import Path
from typing import Any

import pandas as pd

from . import config
from .logging_setup import get_logger
from .run_context import RunContext

logger = get_logger(__name__)


# --------------------------------------------------
# 1. Path construction
# --------------------------------------------------

def raw_path(source: str, name: str, context: RunContext, suffix: str) -> Path:
    """Path for an unmodified source payload, e.g. data/raw/youtube/search_<ts>.json."""
    directory = config.RAW_DIR / source
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{name}_{context.timestamp_slug}{suffix}"


def processed_path(source: str, name: str, context: RunContext) -> Path:
    """Path for a cleaned table, e.g. data/processed/youtube/video_snapshots_<ts>.csv."""
    directory = config.PROCESSED_DIR / source
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{name}_{context.timestamp_slug}.csv"


# --------------------------------------------------
# 2. Writers
# --------------------------------------------------

def write_raw_json(
    payload: dict[str, Any],
    source: str,
    name: str,
    context: RunContext,
) -> Path:
    """Persist a raw API response verbatim, with lineage metadata attached.

    Raw payloads are kept unmodified on purpose. When a transform turns out to
    be wrong three weeks from now, the raw file lets you re-derive the correct
    answer without re-spending API quota.
    """
    enriched = {"run_metadata": context.as_metadata(), **payload}

    path = raw_path(source, name, context, ".json")
    with open(path, "w", encoding="utf-8") as file:
        json.dump(enriched, file, indent=2, ensure_ascii=False, default=str)

    logger.info("Wrote raw %s/%s (%s)", source, name, _describe_size(path))
    return path


def write_raw_dataframe(
    frame: pd.DataFrame,
    source: str,
    name: str,
    context: RunContext,
    include_index: bool = False,
) -> Path:
    """Persist a raw tabular response, e.g. the wide Google Trends frame."""
    path = raw_path(source, name, context, ".csv")
    frame.to_csv(path, index=include_index)

    logger.info(
        "Wrote raw %s/%s (%d rows, %s)", source, name, len(frame), _describe_size(path)
    )
    return path


def write_table(
    frame: pd.DataFrame,
    source: str,
    name: str,
    context: RunContext,
) -> Path:
    """Persist a cleaned, analysis-ready table.

    Raises on an empty frame. A pipeline that silently writes zero rows is
    worse than one that fails, because the dashboard downstream just shows
    yesterday's numbers and nobody notices for a week.
    """
    if frame.empty:
        raise ValueError(
            f"Refusing to write an empty table: {source}/{name}. "
            "The source returned no usable rows."
        )

    path = processed_path(source, name, context)
    frame.to_csv(path, index=False)

    logger.info("Wrote table %s/%s (%d rows)", source, name, len(frame))
    return path


# --------------------------------------------------
# 3. Helpers
# --------------------------------------------------

def _describe_size(path: Path) -> str:
    kilobytes = path.stat().st_size / 1024
    if kilobytes < 1024:
        return f"{kilobytes:.1f} KB"
    return f"{kilobytes / 1024:.1f} MB"
