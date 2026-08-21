import json
import re
from pathlib import Path

import pandas as pd


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

RAW_DATA_DIR = Path(
    "data/raw/youtube"
)

PROCESSED_DATA_DIR = Path(
    "data/processed/youtube"
)

PROCESSED_DATA_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# --------------------------------------------------
# 2. Find latest topic-basket details file
# --------------------------------------------------

detail_files = list(
    RAW_DATA_DIR.glob(
        "youtube_topic_basket_details_*.json"
    )
)

if not detail_files:
    raise FileNotFoundError(
        "No YouTube topic-basket details files found."
    )


latest_detail_file = max(
    detail_files,
    key=lambda path: path.stat().st_mtime
)


print("\nDETAIL FILE USED")
print("=" * 70)
print(latest_detail_file)


# --------------------------------------------------
# 3. Load raw enrichment artifact
# --------------------------------------------------

with open(
    latest_detail_file,
    "r",
    encoding="utf-8",
) as file:

    detail_data = json.load(file)


request_metadata = detail_data.get(
    "request_metadata",
    {}
)

video_topics = detail_data.get(
    "video_topics",
    {}
)

video_items = detail_data.get(
    "items",
    []
)


# --------------------------------------------------
# 4. Parse collection timestamp
# --------------------------------------------------

collected_at = pd.to_datetime(
    request_metadata.get(
        "collected_at"
    ),
    utc=True,
    errors="coerce",
)

if pd.isna(collected_at):
    raise ValueError(
        "Could not parse details collection timestamp."
    )


timestamp_string = (
    collected_at.strftime(
        "%Y%m%d_%H%M%S"
    )
)


# --------------------------------------------------
# 5. Helper: ISO 8601 duration -> seconds
# --------------------------------------------------

def duration_to_seconds(duration):

    if not duration:
        return None

    pattern = (
        r"PT"
        r"(?:(\d+)H)?"
        r"(?:(\d+)M)?"
        r"(?:(\d+)S)?"
    )

    match = re.fullmatch(
        pattern,
        duration,
    )

    if not match:
        return None

    hours = int(
        match.group(1) or 0
    )

    minutes = int(
        match.group(2) or 0
    )

    seconds = int(
        match.group(3) or 0
    )

    return (
        hours * 3600
        + minutes * 60
        + seconds
    )


# --------------------------------------------------
# 6. Build one row per video snapshot
# --------------------------------------------------

video_records = []


for item in video_items:

    snippet = item.get(
        "snippet",
        {}
    )

    statistics = item.get(
        "statistics",
        {}
    )

    content_details = item.get(
        "contentDetails",
        {}
    )


    published_at = pd.to_datetime(
        snippet.get(
            "publishedAt"
        ),
        utc=True,
        errors="coerce",
    )


    if pd.isna(published_at):
        video_age_hours = None

    else:
        age_delta = (
            collected_at
            - published_at
        )

        video_age_hours = (
            age_delta.total_seconds()
            / 3600
        )


    caption_raw = (
        content_details.get(
            "caption"
        )
    )

    if caption_raw is None:
        caption = None
    else:
        caption = (
            str(
                caption_raw
            ).lower()
            == "true"
        )


    video_records.append(
        {
            "video_id":
                item.get("id"),

            "title":
                snippet.get(
                    "title"
                ),

            "channel_id":
                snippet.get(
                    "channelId"
                ),

            "channel_title":
                snippet.get(
                    "channelTitle"
                ),

            "published_at":
                published_at,

            "category_id":
                snippet.get(
                    "categoryId"
                ),

            "default_language":
                snippet.get(
                    "defaultLanguage"
                ),

            "default_audio_language":
                snippet.get(
                    "defaultAudioLanguage"
                ),

            "duration_seconds":
                duration_to_seconds(
                    content_details.get(
                        "duration"
                    )
                ),

            "definition":
                content_details.get(
                    "definition"
                ),

            "caption":
                caption,

            "licensed_content":
                content_details.get(
                    "licensedContent"
                ),

            "view_count":
                statistics.get(
                    "viewCount"
                ),

            "like_count":
                statistics.get(
                    "likeCount"
                ),

            "comment_count":
                statistics.get(
                    "commentCount"
                ),

            "collected_at":
                collected_at,

            "video_age_hours":
                video_age_hours,
        }
    )


videos_df = pd.DataFrame(
    video_records
)


# --------------------------------------------------
# 7. Convert numeric columns
# --------------------------------------------------

integer_columns = [
    "duration_seconds",
    "view_count",
    "like_count",
    "comment_count",
]


for column in integer_columns:

    videos_df[column] = (
        pd.to_numeric(
            videos_df[column],
            errors="coerce",
        )
        .astype("Int64")
    )


videos_df[
    "video_age_hours"
] = (
    pd.to_numeric(
        videos_df[
            "video_age_hours"
        ],
        errors="coerce",
    )
    .astype("Float64")
)


# --------------------------------------------------
# 8. Derive exploratory attention metric
# --------------------------------------------------

videos_df[
    "views_per_hour_since_publish"
] = pd.NA


eligible_mask = (
    videos_df[
        "video_age_hours"
    ] >= 1
)


videos_df.loc[
    eligible_mask,
    "views_per_hour_since_publish"
] = (
    videos_df.loc[
        eligible_mask,
        "view_count"
    ]
    /
    videos_df.loc[
        eligible_mask,
        "video_age_hours"
    ]
)


videos_df[
    "views_per_hour_since_publish"
] = (
    pd.to_numeric(
        videos_df[
            "views_per_hour_since_publish"
        ],
        errors="coerce",
    )
    .astype("Float64")
)


# --------------------------------------------------
# 9. Build video-topic bridge table
# --------------------------------------------------

topic_records = []


for video_id, topics in (
    video_topics.items()
):

    for topic in topics:

        topic_records.append(
            {
                "video_id":
                    video_id,

                "topic":
                    topic,

                "details_collected_at":
                    collected_at,
            }
        )


video_topics_df = pd.DataFrame(
    topic_records
)


# --------------------------------------------------
# 10. Validation
# --------------------------------------------------

video_duplicate_count = (
    videos_df
    .duplicated(
        subset=[
            "video_id",
            "collected_at",
        ]
    )
    .sum()
)


topic_duplicate_count = (
    video_topics_df
    .duplicated(
        subset=[
            "video_id",
            "topic",
            "details_collected_at",
        ]
    )
    .sum()
)


unmatched_topic_ids = (
    set(
        video_topics_df[
            "video_id"
        ]
    )
    -
    set(
        videos_df[
            "video_id"
        ]
    )
)


# --------------------------------------------------
# 11. Display video snapshot validation
# --------------------------------------------------

print("\nVIDEO SNAPSHOT SHAPE")
print("=" * 70)

print(
    videos_df.shape
)


print("\nVIDEO SNAPSHOT DATA TYPES")
print("=" * 70)

print(
    videos_df.dtypes
)


print("\nVIDEO SNAPSHOT MISSING VALUES")
print("=" * 70)

print(
    videos_df.isna().sum()
)


print("\nDUPLICATE VIDEO SNAPSHOT GRAIN")
print("=" * 70)

print(
    video_duplicate_count
)


# --------------------------------------------------
# 12. Display bridge-table validation
# --------------------------------------------------

print("\nVIDEO-TOPIC SHAPE")
print("=" * 70)

print(
    video_topics_df.shape
)


print("\nDUPLICATE VIDEO-TOPIC GRAIN")
print("=" * 70)

print(
    topic_duplicate_count
)


print("\nUNMATCHED VIDEO IDS")
print("=" * 70)

print(
    len(
        unmatched_topic_ids
    )
)


# --------------------------------------------------
# 13. Topic relationship counts
# --------------------------------------------------

print("\nVIDEO RELATIONSHIPS BY TOPIC")
print("=" * 70)

print(
    video_topics_df[
        "topic"
    ]
    .value_counts()
    .to_string()
)


# --------------------------------------------------
# 14. Videos assigned to multiple topics
# --------------------------------------------------

topic_counts_per_video = (
    video_topics_df
    .groupby(
        "video_id"
    )
    .size()
)


multi_topic_videos = (
    topic_counts_per_video[
        topic_counts_per_video > 1
    ]
)


print("\nMULTI-TOPIC VIDEOS")
print("=" * 70)

print(
    "Count:",
    len(
        multi_topic_videos
    )
)


if not multi_topic_videos.empty:

    multi_topic_ids = (
        multi_topic_videos
        .index
        .tolist()
    )


    print(
        video_topics_df[
            video_topics_df[
                "video_id"
            ].isin(
                multi_topic_ids
            )
        ]
        .sort_values(
            [
                "video_id",
                "topic",
            ]
        )
        .to_string(
            index=False
        )
    )


# --------------------------------------------------
# 15. Sample analytics view
# --------------------------------------------------

print("\nVIDEO SNAPSHOT SAMPLE")
print("=" * 70)

sample_columns = [
    "video_id",
    "title",
    "duration_seconds",
    "view_count",
    "like_count",
    "comment_count",
    "video_age_hours",
    "views_per_hour_since_publish",
]


print(
    videos_df[
        sample_columns
    ]
    .head(10)
    .to_string(
        index=False
    )
)


# --------------------------------------------------
# 16. Save processed datasets
# --------------------------------------------------

videos_output_file = (
    PROCESSED_DATA_DIR
    / (
        "youtube_video_snapshots_"
        f"{timestamp_string}.csv"
    )
)


topics_output_file = (
    PROCESSED_DATA_DIR
    / (
        "youtube_video_topics_"
        f"{timestamp_string}.csv"
    )
)


videos_df.to_csv(
    videos_output_file,
    index=False,
)


video_topics_df.to_csv(
    topics_output_file,
    index=False,
)


print("\nPROCESSED DATA SAVED")
print("=" * 70)

print(
    f"Videos: {videos_output_file}"
)

print(
    f"Topics: {topics_output_file}"
)