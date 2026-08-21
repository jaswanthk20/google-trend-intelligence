import json
from pathlib import Path

import pandas as pd


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

RAW_DATA_DIR = Path(
    "data/raw/youtube"
)


# --------------------------------------------------
# 2. Find latest topic-basket search file
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


print("\nSEARCH FILE USED")
print("=" * 70)
print(latest_search_file)


# --------------------------------------------------
# 3. Load raw search bundle
# --------------------------------------------------

with open(
    latest_search_file,
    "r",
    encoding="utf-8",
) as file:

    search_data = json.load(file)


topic_responses = search_data.get(
    "topic_responses",
    {}
)


# --------------------------------------------------
# 4. Build topic-level diagnostics
# --------------------------------------------------

records = []


for topic, response in topic_responses.items():

    items = response.get(
        "items",
        []
    )

    page_info = response.get(
        "pageInfo",
        {}
    )


    video_ids = []

    for item in items:

        video_id = (
            item.get("id", {})
            .get("videoId")
        )

        if video_id:
            video_ids.append(
                video_id
            )


    returned_count = len(
        items
    )

    unique_sample_videos = len(
        set(video_ids)
    )

    estimated_results = (
        page_info.get(
            "totalResults"
        )
    )

    has_more_pages = (
        "nextPageToken"
        in response
    )


    records.append(
        {
            "topic": topic,

            "returned_sample_count":
                returned_count,

            "unique_sample_videos":
                unique_sample_videos,

            "estimated_indexed_results":
                estimated_results,

            "has_more_pages":
                has_more_pages,
        }
    )


diagnostic_df = pd.DataFrame(
    records
)


# --------------------------------------------------
# 5. Add relative supply proxy
# --------------------------------------------------

max_estimated = (
    diagnostic_df[
        "estimated_indexed_results"
    ].max()
)


diagnostic_df[
    "relative_supply_index"
] = (
    diagnostic_df[
        "estimated_indexed_results"
    ]
    / max_estimated
    * 100
)


# --------------------------------------------------
# 6. Sort by estimated indexed results
# --------------------------------------------------

diagnostic_df = (
    diagnostic_df
    .sort_values(
        "estimated_indexed_results",
        ascending=False
    )
    .reset_index(
        drop=True
    )
)


diagnostic_df[
    "relative_supply_index"
] = (
    diagnostic_df[
        "relative_supply_index"
    ]
    .round(2)
)


# --------------------------------------------------
# 7. Display
# --------------------------------------------------

print("\nYOUTUBE SUPPLY DIAGNOSTIC")
print("=" * 90)

print(
    diagnostic_df.to_string(
        index=False
    )
)


print("\nIMPORTANT")
print("=" * 90)

print(
    "returned_sample_count is limited by our API request size."
)

print(
    "estimated_indexed_results is an approximate YouTube search estimate,"
)

print(
    "not an exact video count."
)

print(
    "relative_supply_index is therefore also a comparative proxy,"
)

print(
    "not an absolute measure of content supply."
)