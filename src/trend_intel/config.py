"""Central configuration.

Every value can be overridden by an environment variable. This is what lets
the identical code run on a laptop (values from a .env file) and inside a
Cloud Function (values from the deployment's environment) with no code change.
"""

import os
from pathlib import Path

from dotenv import load_dotenv


# --------------------------------------------------
# 1. Load .env if one exists
# --------------------------------------------------

# Walk up from this file to the project root so the .env is found no matter
# which directory the script was launched from.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")


# --------------------------------------------------
# 2. Helpers for reading typed values from the environment
# --------------------------------------------------

def _get_str(name: str, default: str) -> str:
    value = os.getenv(name)
    return value.strip() if value and value.strip() else default


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value or not value.strip():
        return default
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(
            f"{name} must be an integer, got {value!r}"
        ) from error


def _get_list(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if not value or not value.strip():
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


# --------------------------------------------------
# 3. The topic basket
# --------------------------------------------------

# These five topics are requested as ONE Google Trends comparison so their
# interest scores are indexed against each other on a shared 0-100 scale.
# Requesting them separately would give five independent scales that cannot
# be compared, which is the single most common Google Trends mistake.
TOPICS: list[str] = _get_list(
    "TREND_INTEL_TOPICS",
    [
        "AI agents",
        "Agentic AI",
        "Vibe coding",
        "Model Context Protocol",
        "Multimodal AI",
    ],
)

# Google Trends caps a single comparison request at five terms.
MAX_TOPICS_PER_TRENDS_REQUEST = 5


# --------------------------------------------------
# 4. Source parameters
# --------------------------------------------------

REGION_CODE: str = _get_str("TREND_INTEL_REGION", "CA")

TRENDS_TIMEFRAME: str = _get_str("TREND_INTEL_TIMEFRAME", "today 3-m")
TRENDS_LANGUAGE: str = _get_str("TREND_INTEL_TRENDS_LANGUAGE", "en-CA")
TRENDS_SEARCH_TYPE: str = "web"          # gprop="" in the pytrends API
TRENDS_MAX_ATTEMPTS: int = _get_int("TREND_INTEL_TRENDS_MAX_ATTEMPTS", 4)

YOUTUBE_WINDOW_DAYS: int = _get_int("TREND_INTEL_YOUTUBE_WINDOW_DAYS", 7)
YOUTUBE_SEARCH_ORDER: str = "date"
YOUTUBE_MAX_RESULTS_PER_TOPIC: int = 50   # API hard maximum for search.list
YOUTUBE_DETAILS_BATCH_SIZE: int = 50      # API hard maximum for videos.list


# --------------------------------------------------
# 5. YouTube quota arithmetic - READ BEFORE CHANGING THE SCHEDULE
# --------------------------------------------------
#
# A new Google Cloud project gets 10,000 YouTube Data API units per day.
# The quota resets at midnight US Pacific time, NOT at midnight UTC - which
# is why a job that looks fine at 00:30 UTC can still return 403
# quotaExceeded.
#
#   search.list  = 100 units per call   -> one call per topic
#   videos.list  =   1 unit  per call   -> one call per 50 video IDs
#
# With 5 topics returning ~250 unique videos:
#
#   5 searches x 100 units  =  500
#   5 batches  x   1 unit   =    5
#                             -----
#   cost per pipeline run   =  505 units
#
# Safe schedules:
#   once daily    ->    505 units/day
#   every 6 hours ->  2,020 units/day   <- what Phase 2 will use
#   every 3 hours ->  4,040 units/day
#
# UNSAFE:
#   hourly        -> 12,120 units/day   -> blows the quota mid-afternoon
#
# If the basket grows, the search cost grows by 100 units per topic added.
YOUTUBE_DAILY_QUOTA_UNITS = 10_000
YOUTUBE_SEARCH_COST_UNITS = 100
YOUTUBE_DETAILS_COST_UNITS = 1


def estimated_quota_cost(topic_count: int, video_count: int) -> int:
    """Units one full run will consume. Logged so quota use is never a surprise."""
    search_batches = topic_count
    detail_batches = -(-video_count // YOUTUBE_DETAILS_BATCH_SIZE)  # ceiling division
    return (
        search_batches * YOUTUBE_SEARCH_COST_UNITS
        + detail_batches * YOUTUBE_DETAILS_COST_UNITS
    )


# --------------------------------------------------
# 6. Output location
# --------------------------------------------------

# Cloud Functions have a read-only filesystem except for /tmp, so Phase 2
# will set this to /tmp before handing the data on to BigQuery.
DATA_DIR: Path = Path(_get_str("TREND_INTEL_DATA_DIR", str(PROJECT_ROOT / "data")))

RAW_DIR: Path = DATA_DIR / "raw"
PROCESSED_DIR: Path = DATA_DIR / "processed"


# --------------------------------------------------
# 7. Secrets
# --------------------------------------------------

def get_youtube_api_key() -> str:
    """Read the YouTube API key, failing with an actionable message if absent.

    Deliberately a function rather than a module constant: importing this
    module must never explode just because a key is missing, otherwise the
    Google Trends half of the pipeline cannot run on its own.
    """
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "YOUTUBE_API_KEY is not set. Copy .env.example to .env and add "
            "your key from console.cloud.google.com > APIs & Services > Credentials."
        )
    return api_key
