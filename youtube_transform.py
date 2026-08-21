import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

RAW_DATA_DIR = Path("data/raw/youtube")
PROCESSED_DATA_DIR = Path("data/processed/youtube")

PROCESSED_DATA_DIR.mkdir(
    parents=True,
    exist_ok=True
)

SEARCH_QUERY = "AI agents"
REGION_CODE = "CA"
SEARCH_ORDER = "date"


# --------------------------------------------------
# 2. Find latest raw files
# --------------------------------------------------

search_files = list(
    RAW_DATA_DIR.glob(
        "youtube_search_ai_agents_*.json"
    )
)

detail_files = list(
    RAW_DATA_DIR.glob(
        "youtube_video_details_*.json"
    )
)

if not search_files:
    raise FileNotFoundError(
        "No YouTube search files found."
    )

if not detail_files:
    raise FileNotFoundError(
        "No YouTube video detail files found."
    )


latest_search_file = max(
    search_files,
    key=lambda path: path.stat().st_mtime
)

latest_detail_file = max(
    detail_files,
    key=lambda path: path.stat().st_mtime
)


print("\nFILES USED")
print("=" * 70)

print(f"Search file : {latest_search_file}")
print(f"Details file: {latest_detail_file}")


# --------------------------------------------------
# 3. Load raw JSON
# --------------------------------------------------

with open(
    latest_search_file,
    "r",
    encoding="utf-8"
) as file:
    search_response = json.load(file)


with open(
    latest_detail_file,
    "r",
    encoding="utf-8"
) as file:
    details_response = json.load(file)


# --------------------------------------------------
# 4. Helper: convert ISO 8601 duration to seconds
#
# Examples:
# PT38S    -> 38
# PT1M     -> 60
# PT1M18S  -> 78
# PT2H5M3S -> 7503
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
        duration
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
# 5. Extract video IDs discovered by search
# --------------------------------------------------

searched_video_ids = []

for item in search_response.get(
    "items",
    []
):
    video_id = (
        item.get("id", {})
        .get("videoId")
    )

    if video_id:
        searched_video_ids.append(
            video_id
        )


# --------------------------------------------------
# 6. Derive collection timestamp from raw snapshot
# --------------------------------------------------

details_filename = latest_detail_file.stem

timestamp_match = re.search(
    r"youtube_video_details_(\d{8}_\d{6})",
    details_filename
)

if not timestamp_match:
    raise ValueError(
        "Could not determine collection timestamp "
        "from video-details filename."
    )

collection_timestamp_string = (
    timestamp_match.group(1)
)

collected_at = pd.to_datetime(
    collection_timestamp_string,
    format="%Y%m%d_%H%M%S",
    utc=True
)

# --------------------------------------------------
# 7. Transform video details
# --------------------------------------------------

records = []

for item in details_response.get(
    "items",
    []
):

    video_id = item.get("id")

    # Only use videos discovered by our search request
    if video_id not in searched_video_ids:
        continue

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
        snippet.get("publishedAt"),
        utc=True,
        errors="coerce"
    )


    duration_seconds = (
        duration_to_seconds(
            content_details.get(
                "duration"
            )
        )
    )


    view_count = pd.to_numeric(
        statistics.get("viewCount"),
        errors="coerce"
    )

    like_count = pd.to_numeric(
        statistics.get("likeCount"),
        errors="coerce"
    )

    comment_count = pd.to_numeric(
        statistics.get("commentCount"),
        errors="coerce"
    )


    caption_raw = content_details.get(
        "caption"
    )

    if caption_raw is None:
        caption = None
    else:
        caption = (
            str(caption_raw)
            .lower()
            == "true"
        )


    if pd.isna(published_at):
      video_age_hours = None
    else:
       age_delta = (collected_at - published_at)

       video_age_hours = (age_delta.total_seconds()/ 3600)

    records.append(
        {
            "video_id": video_id,

            "title": snippet.get(
                "title"
            ),

            "channel_id": snippet.get(
                "channelId"
            ),

            "channel_title": snippet.get(
                "channelTitle"
            ),

            "published_at": published_at,

            "category_id": snippet.get(
                "categoryId"
            ),

            "default_language": snippet.get(
                "defaultLanguage"
            ),

            "default_audio_language": snippet.get(
                "defaultAudioLanguage"
            ),

            "definition": content_details.get(
                "definition"
            ),

            "caption": caption,

            "duration_seconds": duration_seconds,

            "view_count": view_count,

            "like_count": like_count,

            "comment_count": comment_count,

            "search_query": SEARCH_QUERY,

            "region_code": REGION_CODE,

            "search_order": SEARCH_ORDER,

            "collected_at": collected_at,

            "video_age_hours": video_age_hours,
        }
    )


# --------------------------------------------------
# 8. Create cleaned DataFrame
# --------------------------------------------------

youtube_clean_df = pd.DataFrame(
    records
)


# --------------------------------------------------
# 9. Convert nullable numeric columns
# --------------------------------------------------

numeric_columns = [
    "duration_seconds",
    "view_count",
    "like_count",
    "comment_count",
]

for column in numeric_columns:
    youtube_clean_df[column] = (
        youtube_clean_df[column]
        .astype("Int64")
    )


youtube_clean_df[
    "video_age_hours"
] = (
    youtube_clean_df[
        "video_age_hours"
    ]
    .astype("Float64")
)

# --------------------------------------------------
# 10. Derive exploratory attention metric
# --------------------------------------------------

youtube_clean_df[
    "views_per_hour_since_publish"
] = pd.NA


eligible_mask = (
    youtube_clean_df[
        "video_age_hours"
    ] >= 1
)


youtube_clean_df.loc[
    eligible_mask,
    "views_per_hour_since_publish"
] = (
    youtube_clean_df.loc[
        eligible_mask,
        "view_count"
    ]
    /
    youtube_clean_df.loc[
        eligible_mask,
        "video_age_hours"
    ]
)


youtube_clean_df[
    "views_per_hour_since_publish"
] = (
    pd.to_numeric(
        youtube_clean_df[
            "views_per_hour_since_publish"
        ],
        errors="coerce"
    )
    .astype("Float64")
)

# --------------------------------------------------
# 11. Basic validation
# --------------------------------------------------

print("\nCLEAN DATASET SHAPE")
print("=" * 70)
print(
    youtube_clean_df.shape
)


print("\nDATA TYPES")
print("=" * 70)
print(
    youtube_clean_df.dtypes
)


print("\nMISSING VALUES")
print("=" * 70)
print(
    youtube_clean_df.isna().sum()
)


print("\nDUPLICATE VIDEO IDS")
print("=" * 70)

duplicate_count = (
    youtube_clean_df[
        "video_id"
    ]
    .duplicated()
    .sum()
)

print(duplicate_count)


print("\nCLEAN ANALYTICS VIEW")
print("=" * 70)

display_columns = [
    "video_id",
    "title",
    "duration_seconds",
    "view_count",
    "like_count",
    "comment_count",
    "video_age_hours",
]

print(
    youtube_clean_df[
        display_columns
    ].to_string(
        index=False
    )
)


# --------------------------------------------------
# 12. Save processed CSV
# --------------------------------------------------

timestamp = collected_at.strftime(
    "%Y%m%d_%H%M%S"
)

output_file = (
    PROCESSED_DATA_DIR
    / f"youtube_cleaned_{timestamp}.csv"
)


youtube_clean_df.to_csv(
    output_file,
    index=False
)


print("\nCLEAN DATA SAVED")
print("=" * 70)
print(output_file)