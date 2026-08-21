"""Pipeline orchestration and command-line entry point.

This is the only module that knows about all three layers. It creates the
RunContext, calls sources/, hands payloads to storage.py, and decides what a
partial failure means.

Usage:
    python -m trend_intel.pipeline --source all
    python -m trend_intel.pipeline --source trends
    python -m trend_intel.pipeline --source youtube

The transform stage is added in Step B; today this collects and persists raw
payloads, which is the stage that proves both APIs are reachable.
"""

import argparse
import logging
import sys
from dataclasses import dataclass, field

from . import config, storage
from .logging_setup import configure_logging, get_logger
from .run_context import RunContext
from .sources import trends as trends_source
from .sources import youtube as youtube_source

logger = get_logger(__name__)


@dataclass
class RunResult:
    """What a run actually accomplished. Returned so callers can act on it."""

    context: RunContext
    sources_succeeded: list[str] = field(default_factory=list)
    sources_failed: dict[str, str] = field(default_factory=dict)
    artifacts: list[str] = field(default_factory=list)

    @property
    def is_total_failure(self) -> bool:
        return not self.sources_succeeded


# --------------------------------------------------
# 1. Google Trends
# --------------------------------------------------

def collect_trends(context: RunContext, result: RunResult) -> None:
    """Fetch and persist the raw Google Trends basket."""
    payload = trends_source.fetch_topic_basket(context)

    # The wide frame is indexed by date, so the index must be written out.
    raw_file = storage.write_raw_dataframe(
        payload.frame,
        source="google_trends",
        name="topic_basket",
        context=context,
        include_index=True,
    )

    meta_file = storage.write_raw_json(
        {
            "request_metadata": payload.request_metadata,
            "records": payload.frame.reset_index().to_dict(orient="records"),
        },
        source="google_trends",
        name="topic_basket",
        context=context,
    )

    result.artifacts.extend([str(raw_file), str(meta_file)])


# --------------------------------------------------
# 2. YouTube
# --------------------------------------------------

def collect_youtube(context: RunContext, result: RunResult) -> None:
    """Fetch and persist raw YouTube search results and video statistics."""
    client = youtube_source.build_client()

    search_payload = youtube_source.search_topics(context, client=client)

    search_file = storage.write_raw_json(
        {
            "request_metadata": search_payload.request_metadata,
            "topic_responses": search_payload.topic_responses,
        },
        source="youtube",
        name="topic_basket_search",
        context=context,
    )

    details_payload = youtube_source.fetch_video_details(
        context, search_payload, client=client
    )

    details_file = storage.write_raw_json(
        {
            "request_metadata": details_payload.request_metadata,
            "video_topics": details_payload.video_topics,
            "items": details_payload.items,
        },
        source="youtube",
        name="topic_basket_details",
        context=context,
    )

    result.artifacts.extend([str(search_file), str(details_file)])


# --------------------------------------------------
# 3. Orchestration
# --------------------------------------------------

# Trends is scraped and genuinely flaky, so a failure there is tolerated.
# YouTube is an official API: if it fails, something is actually wrong
# (bad key, exhausted quota) and the run should be marked failed.
TOLERATED_FAILURES = {
    "trends": (trends_source.TrendsUnavailable,),
    "youtube": (),
}

COLLECTORS = {
    "trends": collect_trends,
    "youtube": collect_youtube,
}


def run(sources: list[str]) -> RunResult:
    """Execute one full pipeline run across the requested sources."""
    context = RunContext.create()
    configure_logging(run_id=context.run_id)

    logger.info("=" * 70)
    logger.info("Run started")
    logger.info("  run_id       : %s", context.run_id)
    logger.info("  collected_at : %s", context.collected_at.isoformat())
    logger.info("  sources      : %s", ", ".join(sources))
    logger.info("  topics       : %s", ", ".join(config.TOPICS))
    logger.info("  region       : %s", config.REGION_CODE)
    logger.info("  data dir     : %s", config.DATA_DIR)
    logger.info("=" * 70)

    result = RunResult(context=context)

    for source in sources:
        try:
            COLLECTORS[source](context, result)
            result.sources_succeeded.append(source)

        except TOLERATED_FAILURES[source] as error:
            # Degrade, do not die. The other source's data is still worth having.
            logger.warning(
                "Source %r failed but is non-fatal; continuing. Reason: %s",
                source, error,
            )
            result.sources_failed[source] = str(error)

        except Exception as error:  # noqa: BLE001 - logged then re-raised below
            logger.error("Source %r failed fatally: %s", source, error, exc_info=True)
            result.sources_failed[source] = str(error)

    logger.info("=" * 70)
    logger.info("Run finished: %d succeeded, %d failed",
                len(result.sources_succeeded), len(result.sources_failed))
    for artifact in result.artifacts:
        logger.info("  artifact: %s", artifact)
    logger.info("  run_id: %s", context.run_id)
    logger.info("=" * 70)

    return result


# --------------------------------------------------
# 4. Command-line interface
# --------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m trend_intel.pipeline",
        description="Collect live Google Trends and YouTube data for the topic basket.",
    )
    parser.add_argument(
        "--source",
        choices=["trends", "youtube", "all"],
        default="all",
        help="Which source(s) to collect. Default: all.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )

    args = parser.parse_args(argv)

    sources = ["trends", "youtube"] if args.source == "all" else [args.source]

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    result = run(sources)

    # Non-zero exit on total failure so Cloud Scheduler marks the job failed
    # in Phase 2 rather than reporting a green run that collected nothing.
    return 1 if result.is_total_failure else 0


if __name__ == "__main__":
    sys.exit(main())
