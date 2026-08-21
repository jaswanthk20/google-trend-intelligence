import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

TOPICS = [
    "AI agents",
    "Agentic AI",
    "Vibe coding",
    "Model Context Protocol",
    "Multimodal AI",
]

REGION_CODE = "CA"
SEARCH_ORDER = "date"
MAX_RESULTS = 50

RAW_DATA_DIR = Path(
    "data/raw/youtube"
)

RAW_DATA_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# --------------------------------------------------
# 2. Load API key
# --------------------------------------------------

load_dotenv()

API_KEY = os.getenv(
    "YOUTUBE_API_KEY"
)

if not API_KEY:
    raise RuntimeError(
        "YOUTUBE_API_KEY was not found."
    )


# --------------------------------------------------
# 3. Define seven COMPLETE UTC days
# --------------------------------------------------

now_utc = datetime.now(
    timezone.utc
)

window_end = now_utc.replace(
    hour=0,
    minute=0,
    second=0,
    microsecond=0,
)

window_start = (
    window_end
    - timedelta(days=7)
)


published_after = (
    window_start
    .isoformat()
    .replace("+00:00", "Z")
)

published_before = (
    window_end
    .isoformat()
    .replace("+00:00", "Z")
)


print("\nYOUTUBE TOPIC BASKET SEARCH")
print("=" * 70)

print(
    f"Window start : {published_after}"
)

print(
    f"Window end   : {published_before}"
)

print(
    f"Region       : {REGION_CODE}"
)

print(
    f"Order        : {SEARCH_ORDER}"
)


# --------------------------------------------------
# 4. Connect to YouTube
# --------------------------------------------------

youtube = build(
    "youtube",
    "v3",
    developerKey=API_KEY,
)


# --------------------------------------------------
# 5. Search each topic
# --------------------------------------------------

raw_output = {
    "request_metadata": {
        "topics": TOPICS,
        "region_code": REGION_CODE,
        "search_order": SEARCH_ORDER,
        "published_after": published_after,
        "published_before": published_before,
        "max_results_per_topic": MAX_RESULTS,
    },
    "topic_responses": {},
}


summary_records = []


for topic in TOPICS:

    print(
        f"\nSearching: {topic}"
    )

    try:
        request = (
            youtube
            .search()
            .list(
                part="snippet",
                q=topic,
                type="video",
                maxResults=MAX_RESULTS,
                order=SEARCH_ORDER,
                regionCode=REGION_CODE,
                relevanceLanguage="en",
                publishedAfter=published_after,
                publishedBefore=published_before,
            )
        )

        response = (
            request.execute()
        )

    except HttpError as error:
        print(
            f"\nRequest failed for: {topic}"
        )
        print(error)
        raise


    raw_output[
        "topic_responses"
    ][topic] = response


    items = response.get(
        "items",
        []
    )

    page_info = response.get(
        "pageInfo",
        {}
    )


    returned_count = len(
        items
    )

    estimated_total_results = (
        page_info.get(
            "totalResults"
        )
    )

    has_more_results = (
        "nextPageToken"
        in response
    )


    summary_records.append(
        {
            "topic": topic,
            "returned_count": returned_count,
            "estimated_total_results":
                estimated_total_results,
            "has_more_results":
                has_more_results,
        }
    )


# --------------------------------------------------
# 6. Save COMPLETE raw response bundle
# --------------------------------------------------

collected_at = datetime.now(
    timezone.utc
)

timestamp = collected_at.strftime(
    "%Y%m%d_%H%M%S"
)


output_file = (
    RAW_DATA_DIR
    / (
        "youtube_topic_basket_search_"
        f"{timestamp}.json"
    )
)


raw_output[
    "request_metadata"
][
    "collected_at"
] = collected_at.isoformat()


with open(
    output_file,
    "w",
    encoding="utf-8",
) as file:

    json.dump(
        raw_output,
        file,
        indent=2,
        ensure_ascii=False,
    )


# --------------------------------------------------
# 7. Display search summary
# --------------------------------------------------

print("\nSEARCH SUMMARY")
print("=" * 70)

print(
    f"{'Topic':<25}"
    f"{'Returned':>10}"
    f"{'Estimated':>15}"
    f"{'More Pages':>15}"
)


for record in summary_records:

    print(
        f"{record['topic']:<25}"
        f"{record['returned_count']:>10}"
        f"{record['estimated_total_results']:>15}"
        f"{str(record['has_more_results']):>15}"
    )


# --------------------------------------------------
# 8. Check overlap across topics
# --------------------------------------------------

video_to_topics = {}


for topic, response in (
    raw_output[
        "topic_responses"
    ].items()
):

    for item in response.get(
        "items",
        []
    ):

        video_id = (
            item.get(
                "id",
                {}
            )
            .get(
                "videoId"
            )
        )

        if not video_id:
            continue


        if video_id not in (
            video_to_topics
        ):
            video_to_topics[
                video_id
            ] = []


        video_to_topics[
            video_id
        ].append(
            topic
        )


unique_video_count = len(
    video_to_topics
)


overlapping_videos = {
    video_id: topics
    for video_id, topics
    in video_to_topics.items()
    if len(topics) > 1
}


print("\nVIDEO OVERLAP")
print("=" * 70)

print(
    "Unique videos across all topics:",
    unique_video_count,
)

print(
    "Videos appearing under multiple topics:",
    len(overlapping_videos),
)


if overlapping_videos:

    print(
        "\nExamples of overlapping videos:"
    )

    for (
        video_id,
        topics
    ) in list(
        overlapping_videos.items()
    )[:10]:

        print(
            f"{video_id}: {topics}"
        )


print("\nRAW DATA SAVED")
print("=" * 70)

print(output_file)