import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

RAW_DATA_DIR = Path(
    "data/raw/youtube"
)

BATCH_SIZE = 50


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
# 3. Find latest topic-basket search file
# --------------------------------------------------

search_files = list(
    RAW_DATA_DIR.glob(
        "youtube_topic_basket_search_*.json"
    )
)

if not search_files:
    raise FileNotFoundError(
        "No YouTube topic-basket search files found."
    )


latest_search_file = max(
    search_files,
    key=lambda path: path.stat().st_mtime
)


print("\nSOURCE SEARCH FILE")
print("=" * 70)

print(
    latest_search_file
)


# --------------------------------------------------
# 4. Load raw topic-basket search response
# --------------------------------------------------

with open(
    latest_search_file,
    "r",
    encoding="utf-8",
) as file:

    search_data = json.load(
        file
    )


topic_responses = (
    search_data.get(
        "topic_responses",
        {}
    )
)


# --------------------------------------------------
# 5. Build video-to-topic mapping
# --------------------------------------------------

video_to_topics = {}


for topic, response in (
    topic_responses.items()
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


        if video_id not in video_to_topics:
            video_to_topics[
                video_id
            ] = []


        if topic not in video_to_topics[
            video_id
        ]:
            video_to_topics[
                video_id
            ].append(
                topic
            )


video_ids = list(
    video_to_topics.keys()
)


print("\nVIDEO DISCOVERY SUMMARY")
print("=" * 70)

print(
    "Unique video IDs:",
    len(video_ids)
)


# --------------------------------------------------
# 6. Create batches of up to 50 video IDs
# --------------------------------------------------

video_batches = [
    video_ids[
        start:
        start + BATCH_SIZE
    ]
    for start in range(
        0,
        len(video_ids),
        BATCH_SIZE
    )
]


print(
    "Number of detail batches:",
    len(video_batches)
)


print(
    "Batch sizes:",
    [
        len(batch)
        for batch
        in video_batches
    ]
)


# --------------------------------------------------
# 7. Connect to YouTube
# --------------------------------------------------

youtube = build(
    "youtube",
    "v3",
    developerKey=API_KEY,
)


# --------------------------------------------------
# 8. Request video details in batches
# --------------------------------------------------

batch_responses = []


for batch_number, batch in enumerate(
    video_batches,
    start=1,
):

    print(
        f"\nFetching batch "
        f"{batch_number}/"
        f"{len(video_batches)} "
        f"({len(batch)} videos)"
    )


    try:

        request = (
            youtube
            .videos()
            .list(
                part=(
                    "snippet,"
                    "statistics,"
                    "contentDetails"
                ),
                id=",".join(
                    batch
                ),
            )
        )


        response = (
            request.execute()
        )


    except HttpError as error:

        print(
            "\nYouTube API request failed."
        )

        print(
            f"Batch: {batch_number}"
        )

        print(error)

        raise


    batch_responses.append(
        response
    )


# --------------------------------------------------
# 9. Combine returned videos
# --------------------------------------------------

all_video_items = []


for response in batch_responses:

    all_video_items.extend(
        response.get(
            "items",
            []
        )
    )


returned_video_ids = {
    item.get("id")
    for item
    in all_video_items
    if item.get("id")
}


missing_video_ids = [
    video_id
    for video_id
    in video_ids
    if video_id
    not in returned_video_ids
]


# --------------------------------------------------
# 10. Save complete raw enrichment artifact
# --------------------------------------------------

collected_at = datetime.now(
    timezone.utc
)


timestamp = (
    collected_at.strftime(
        "%Y%m%d_%H%M%S"
    )
)


output_data = {

    "request_metadata": {

        "source_search_file":
            str(
                latest_search_file
            ),

        "collected_at":
            collected_at.isoformat(),

        "requested_video_count":
            len(video_ids),

        "returned_video_count":
            len(all_video_items),

        "batch_size":
            BATCH_SIZE,

        "batch_count":
            len(video_batches),
    },

    "video_topics":
        video_to_topics,

    "items":
        all_video_items,
}


output_file = (
    RAW_DATA_DIR
    / (
        "youtube_topic_basket_details_"
        f"{timestamp}.json"
    )
)


with open(
    output_file,
    "w",
    encoding="utf-8",
) as file:

    json.dump(
        output_data,
        file,
        indent=2,
        ensure_ascii=False,
    )


# --------------------------------------------------
# 11. Validate response
# --------------------------------------------------

print("\nDETAIL ENRICHMENT SUMMARY")
print("=" * 70)

print(
    "Videos requested :",
    len(video_ids)
)

print(
    "Videos returned  :",
    len(all_video_items)
)

print(
    "Videos missing   :",
    len(missing_video_ids)
)


if missing_video_ids:

    print(
        "\nMissing video IDs:"
    )

    for video_id in (
        missing_video_ids
    ):
        print(
            video_id
        )


# --------------------------------------------------
# 12. Inspect first returned video
# --------------------------------------------------

if all_video_items:

    first_video = (
        all_video_items[0]
    )

    print("\nFIRST VIDEO")
    print("=" * 70)

    print(
        "Video ID:",
        first_video.get(
            "id"
        )
    )


    print(
        "Topics:",
        video_to_topics.get(
            first_video.get(
                "id"
            ),
            [],
        )
    )


    snippet = (
        first_video.get(
            "snippet",
            {}
        )
    )

    statistics = (
        first_video.get(
            "statistics",
            {}
        )
    )

    content_details = (
        first_video.get(
            "contentDetails",
            {}
        )
    )


    print(
        "Title:",
        snippet.get(
            "title"
        )
    )

    print(
        "Channel:",
        snippet.get(
            "channelTitle"
        )
    )

    print(
        "Published:",
        snippet.get(
            "publishedAt"
        )
    )

    print(
        "Duration:",
        content_details.get(
            "duration"
        )
    )

    print(
        "Views:",
        statistics.get(
            "viewCount"
        )
    )

    print(
        "Likes:",
        statistics.get(
            "likeCount"
        )
    )

    print(
        "Comments:",
        statistics.get(
            "commentCount"
        )
    )


print("\nRAW DETAILS SAVED")
print("=" * 70)

print(
    output_file
)