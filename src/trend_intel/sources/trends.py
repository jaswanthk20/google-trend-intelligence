"""Google Trends collection.

Google Trends has no official public API. pytrends_modern scrapes an internal
endpoint, which means this is the most fragile dependency in the project: it
can return HTTP 429 under rate limiting, or an empty frame with no error at
all. Both are handled here.

Design decision worth defending in an interview: a Trends failure is raised as
a typed TrendsUnavailable exception, and the pipeline catches it and continues
with the YouTube half of the run. A pipeline where one flaky source takes down
every other source is a badly designed pipeline.
"""

import random
import time
from dataclasses import dataclass
from typing import Any

import pandas as pd
from pytrends_modern import TrendReq

from .. import config
from ..logging_setup import get_logger
from ..run_context import RunContext

logger = get_logger(__name__)


class TrendsUnavailable(RuntimeError):
    """Google Trends could not be reached, or returned no usable data.

    Typed so the pipeline can degrade gracefully on this specific failure
    rather than swallowing every exception indiscriminately.
    """


@dataclass(frozen=True)
class TrendsPayload:
    """Raw Google Trends response plus the request that produced it."""

    frame: pd.DataFrame           # wide: one column per topic, plus isPartial
    request_metadata: dict[str, Any]


# --------------------------------------------------
# 1. Public entry point
# --------------------------------------------------

def fetch_topic_basket(
    context: RunContext,
    topics: list[str] | None = None,
    geo: str | None = None,
    timeframe: str | None = None,
) -> TrendsPayload:
    """Fetch interest-over-time for the whole basket as ONE comparison request.

    Requesting all topics together is essential, not incidental. Google Trends
    normalises interest to 0-100 within a single request, so one request gives
    five topics on a shared, comparable scale. Five separate requests would
    give five independent scales where every topic peaks at 100, making
    cross-topic comparison meaningless.
    """
    topics = topics or config.TOPICS
    geo = geo or config.REGION_CODE
    timeframe = timeframe or config.TRENDS_TIMEFRAME

    if not topics:
        raise ValueError("The topic basket is empty.")

    if len(topics) > config.MAX_TOPICS_PER_TRENDS_REQUEST:
        raise ValueError(
            f"Google Trends compares at most "
            f"{config.MAX_TOPICS_PER_TRENDS_REQUEST} terms in one request; "
            f"got {len(topics)}. Splitting the basket would break the shared "
            f"0-100 scale, so reduce the basket instead."
        )

    logger.info(
        "Fetching Google Trends: %d topics, geo=%s, timeframe=%s",
        len(topics), geo, timeframe,
    )

    frame = _fetch_with_retries(topics, geo, timeframe)

    request_metadata = {
        "topics": topics,
        "geo": geo,
        "timeframe": timeframe,
        "search_type": config.TRENDS_SEARCH_TYPE,
        "language": config.TRENDS_LANGUAGE,
        "row_count": len(frame),
    }

    logger.info(
        "Google Trends returned %d rows covering %s to %s",
        len(frame),
        frame.index.min().date(),
        frame.index.max().date(),
    )

    return TrendsPayload(frame=frame, request_metadata=request_metadata)


# --------------------------------------------------
# 2. Retry loop
# --------------------------------------------------

def _fetch_with_retries(
    topics: list[str],
    geo: str,
    timeframe: str,
) -> pd.DataFrame:
    """Attempt the fetch, backing off exponentially on failure.

    pytrends has its own internal retry, but it does not treat an empty frame
    as a failure. Empty is the most common symptom of soft rate limiting, so
    it is retried here too.
    """
    last_error: Exception | None = None

    for attempt in range(1, config.TRENDS_MAX_ATTEMPTS + 1):
        try:
            client = TrendReq(
                hl=config.TRENDS_LANGUAGE,
                tz=0,
                retries=2,
                backoff_factor=0.5,
            )

            client.build_payload(
                kw_list=topics,
                timeframe=timeframe,
                geo=geo,
                gprop="",
            )

            frame = client.interest_over_time()

            if frame.empty:
                raise TrendsUnavailable(
                    "Google Trends returned an empty frame "
                    "(usually soft rate limiting)."
                )

            missing = [topic for topic in topics if topic not in frame.columns]
            if missing:
                raise TrendsUnavailable(
                    f"Google Trends response is missing topics: {missing}"
                )

            if attempt > 1:
                logger.info("Google Trends succeeded on attempt %d", attempt)

            return frame

        except Exception as error:  # noqa: BLE001 - the scraper raises many types
            last_error = error

            if attempt == config.TRENDS_MAX_ATTEMPTS:
                break

            # Exponential backoff with jitter. The jitter matters: without it,
            # a retrying scheduled job hits the endpoint on the same rhythm
            # every time and gets rate limited identically every time.
            delay = (2 ** attempt) + random.uniform(0, 1)
            logger.warning(
                "Google Trends attempt %d/%d failed (%s). Retrying in %.1fs.",
                attempt, config.TRENDS_MAX_ATTEMPTS, error, delay,
            )
            time.sleep(delay)

    raise TrendsUnavailable(
        f"Google Trends failed after {config.TRENDS_MAX_ATTEMPTS} attempts. "
        f"Last error: {last_error}"
    ) from last_error
