"""YouTube Data API v3 collection.

Two calls, in order:

  1. search.list  - one call per topic, finds videos published in the window.
                    Costs 100 quota units each. Returns only IDs and snippets;
                    critically, it does NOT return view or like counts.
  2. videos.list  - one call per 50 video IDs, fetches statistics for the
                    videos found in step 1. Costs 1 unit each.

Step 2 exists because search.list simply does not carry statistics. Anyone who
skips it ends up with a "YouTube performance" dataset that has no performance
in it. Batching by 50 is an API hard limit, not a tuning choice.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .. import config
from ..logging_setup import get_logger
from ..run_context import RunContext

logger = get_logger(__name__)


class YouTubeQuotaExceeded(RuntimeError):
    """The project's daily YouTube API quota is spent.

    Typed separately because the fix is 'wait until midnight Pacific', not
    'retry now'. Retrying a quota error just burns more of tomorrow's budget.
    """


@dataclass
class SearchPayload:
    """Raw search.list responses for the whole basket."""

    request_metadata: dict[str, Any]
    topic_responses: dict[str, Any] = field(default_factory=dict)

    def video_ids_by_topic(self) -> dict[str, list[str]]:
        """Map each video ID to the topics whose search returned it.

        A video can legitimately match several topics, which is why the
        video/topic relationship is a bridge table rather than a column.
        """
        mapping: dict[str, list[str]] = {}
        for topic, response in self.topic_responses.items():
            for item in response.get("items", []):
                video_id = item.get("id", {}).get("videoId")
                if not video_id:
                    continue
                topics = mapping.setdefault(video_id, [])
                if topic not in topics:
                    topics.append(topic)
        return mapping


@dataclass
class DetailsPayload:
    """Raw videos.list responses."""

    request_metadata: dict[str, Any]
    video_topics: dict[str, list[str]]
    items: list[dict[str, Any]]


# --------------------------------------------------
# 1. Client
# --------------------------------------------------

def build_client(api_key: str | None = None):
    """Construct the YouTube API client.

    cache_discovery=False suppresses a spurious warning and avoids writing a
    cache file, which matters on the read-only filesystem of a Cloud Function.
    """
    return build(
        "youtube",
        "v3",
        developerKey=api_key or config.get_youtube_api_key(),
        cache_discovery=False,
    )


# --------------------------------------------------
# 2. Search window
# --------------------------------------------------

def complete_day_window(
    context: RunContext,
    days: int | None = None,
) -> tuple[str, str]:
    """The last N COMPLETE UTC days, as RFC 3339 strings.

    Snapping to midnight rather than 'now minus 7 days' matters: a window that
    ends at the current instant includes a partial day whose video count is
    lower purely because the day is not over. That artefact would show up in
    the dashboard as a fake decline every single run.
    """
    days = days or config.YOUTUBE_WINDOW_DAYS

    window_end = context.collected_at.replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    window_start = window_end - timedelta(days=days)

    return (
        window_start.isoformat().replace("+00:00", "Z"),
        window_end.isoformat().replace("+00:00", "Z"),
    )


# --------------------------------------------------
# 3. Search
# --------------------------------------------------

def search_topics(
    context: RunContext,
    client=None,
    topics: list[str] | None = None,
    region_code: str | None = None,
) -> SearchPayload:
    """Run one search.list per topic. Costs 100 quota units per topic."""
    topics = topics or config.TOPICS
    region_code = region_code or config.REGION_CODE
    client = client or build_client()

    published_after, published_before = complete_day_window(context)

    logger.info(
        "Searching YouTube: %d topics, region=%s, window=%s to %s (%d quota units)",
        len(topics),
        region_code,
        published_after,
        published_before,
        len(topics) * config.YOUTUBE_SEARCH_COST_UNITS,
    )

    payload = SearchPayload(
        request_metadata={
            "topics": topics,
            "region_code": region_code,
            "search_order": config.YOUTUBE_SEARCH_ORDER,
            "published_after": published_after,
            "published_before": published_before,
            "max_results_per_topic": config.YOUTUBE_MAX_RESULTS_PER_TOPIC,
        }
    )

    for topic in topics:
        response = _execute(
            client.search().list(
                part="snippet",
                q=topic,
                type="video",
                maxResults=config.YOUTUBE_MAX_RESULTS_PER_TOPIC,
                order=config.YOUTUBE_SEARCH_ORDER,
                regionCode=region_code,
                relevanceLanguage="en",
                publishedAfter=published_after,
                publishedBefore=published_before,
            ),
            description=f"search.list for {topic!r}",
        )

        payload.topic_responses[topic] = response

        returned = len(response.get("items", []))
        estimated = response.get("pageInfo", {}).get("totalResults")
        logger.info(
            "  %-24s returned %2d videos (~%s indexed)", topic, returned, estimated
        )

    unique_videos = len(payload.video_ids_by_topic())
    logger.info("Search complete: %d unique videos across the basket", unique_videos)

    if unique_videos == 0:
        raise RuntimeError(
            "YouTube search returned no videos for any topic. Check that the "
            "region code and publish window are correct."
        )

    return payload


# --------------------------------------------------
# 4. Details
# --------------------------------------------------

def fetch_video_details(
    context: RunContext,
    search_payload: SearchPayload,
    client=None,
) -> DetailsPayload:
    """Fetch statistics for every discovered video. Costs 1 unit per 50 IDs."""
    client = client or build_client()

    video_topics = search_payload.video_ids_by_topic()
    video_ids = list(video_topics.keys())

    batches = [
        video_ids[start : start + config.YOUTUBE_DETAILS_BATCH_SIZE]
        for start in range(0, len(video_ids), config.YOUTUBE_DETAILS_BATCH_SIZE)
    ]

    logger.info(
        "Fetching details for %d videos in %d batches (%d quota units)",
        len(video_ids),
        len(batches),
        len(batches) * config.YOUTUBE_DETAILS_COST_UNITS,
    )

    items: list[dict[str, Any]] = []

    for batch_number, batch in enumerate(batches, start=1):
        response = _execute(
            client.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(batch),
            ),
            description=f"videos.list batch {batch_number}/{len(batches)}",
        )
        items.extend(response.get("items", []))

    returned_ids = {item.get("id") for item in items if item.get("id")}
    missing_ids = [video_id for video_id in video_ids if video_id not in returned_ids]

    if missing_ids:
        # Normal and expected: videos deleted or made private between the
        # search call and the details call minutes later. Worth logging, not
        # worth failing over.
        logger.warning(
            "%d of %d videos returned no details (deleted or made private)",
            len(missing_ids),
            len(video_ids),
        )

    logger.info("Detail enrichment complete: %d videos with statistics", len(items))

    return DetailsPayload(
        request_metadata={
            "requested_video_count": len(video_ids),
            "returned_video_count": len(items),
            "missing_video_ids": missing_ids,
            "batch_size": config.YOUTUBE_DETAILS_BATCH_SIZE,
            "batch_count": len(batches),
            **search_payload.request_metadata,
        },
        video_topics=video_topics,
        items=items,
    )


# --------------------------------------------------
# 5. Error handling
# --------------------------------------------------

def _execute(request, description: str) -> dict[str, Any]:
    """Run one API request, translating quota errors into a typed exception."""
    try:
        return request.execute()

    except HttpError as error:
        reason = _extract_reason(error)

        if reason in {"quotaExceeded", "dailyLimitExceeded"}:
            raise YouTubeQuotaExceeded(
                f"YouTube daily quota exhausted during {description}. "
                f"Quota resets at midnight US Pacific time, not UTC. "
                f"One full pipeline run costs about "
                f"{config.estimated_quota_cost(len(config.TOPICS), 250)} units "
                f"of the {config.YOUTUBE_DAILY_QUOTA_UNITS} daily allowance."
            ) from error

        if reason == "keyInvalid":
            raise RuntimeError(
                f"YouTube rejected the API key during {description}. Check "
                f"YOUTUBE_API_KEY in .env, and that the key's API restrictions "
                f"include YouTube Data API v3."
            ) from error

        logger.error("%s failed: %s", description, error)
        raise


def _extract_reason(error: HttpError) -> str:
    """Pull the machine-readable reason string out of a Google API error."""
    try:
        details = error.error_details
        if details and isinstance(details, list):
            return details[0].get("reason", "")
    except Exception:  # noqa: BLE001 - error shape varies by API
        pass
    return ""
