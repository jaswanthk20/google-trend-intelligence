import json
from pathlib import Path

import pandas as pd


RAW_DATA_DIR = Path("data/raw/youtube")


# --------------------------------------------------
# 1. Find latest search file
# --------------------------------------------------

search_files = list(
    RAW_DATA_DIR.glob("youtube_search_ai_agents_*.json")
)

if not search_files:
    raise FileNotFoundError(
        "No YouTube search JSON files found."
    )

latest_search_file = max(
    search_files,
    key=lambda path: path.stat().st_mtime
)


# --------------------------------------------------
# 2. Find latest video-details file
# --------------------------------------------------

detail_files = list(
    RAW_DATA_DIR.glob("youtube_video_details_*.json")
)

if not detail_files:
    raise FileNotFoundError(
        "No YouTube video-details JSON files found."
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
# 3. Load both raw JSON files
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
# 4. Build search-result records
# --------------------------------------------------

search_records = []

for position, item in enumerate(
    search_response.get("items", []),
    start=1
):

    snippet = item.get("snippet", {})

    search_records.append(
        {
            "video_id": item.get(
                "id",
                {}
            ).get("videoId"),

            "search_position": position,

            "search_title": snippet.get(
                "title"
            ),

            "search_channel_id": snippet.get(
                "channelId"
            ),

            "search_channel_title": snippet.get(
                "channelTitle"
            ),

            "search_published_at": snippet.get(
                "publishedAt"
            ),

            "search_description": snippet.get(
                "description"
            ),

            "search_live_broadcast_content": snippet.get(
                "liveBroadcastContent"
            ),
        }
    )


search_df = pd.DataFrame(search_records)


# --------------------------------------------------
# 5. Build video-detail records
# --------------------------------------------------

detail_records = []

for item in details_response.get(
    "items",
    []
):

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

    detail_records.append(
        {
            "video_id": item.get("id"),

            "detail_title": snippet.get(
                "title"
            ),

            "detail_channel_id": snippet.get(
                "channelId"
            ),

            "detail_channel_title": snippet.get(
                "channelTitle"
            ),

            "detail_published_at": snippet.get(
                "publishedAt"
            ),

            "category_id": snippet.get(
                "categoryId"
            ),

            "default_language": snippet.get(
                "defaultLanguage"
            ),

            "default_audio_language": snippet.get(
                "defaultAudioLanguage"
            ),

            "duration_raw": content_details.get(
                "duration"
            ),

            "definition": content_details.get(
                "definition"
            ),

            "caption_raw": content_details.get(
                "caption"
            ),

            "licensed_content": content_details.get(
                "licensedContent"
            ),

            "view_count_raw": statistics.get(
                "viewCount"
            ),

            "like_count_raw": statistics.get(
                "likeCount"
            ),

            "favorite_count_raw": statistics.get(
                "favoriteCount"
            ),

            "comment_count_raw": statistics.get(
                "commentCount"
            ),
        }
    )


details_df = pd.DataFrame(
    detail_records
)


# --------------------------------------------------
# 6. Merge search + detail records
# --------------------------------------------------

youtube_df = search_df.merge(
    details_df,
    on="video_id",
    how="left",
    validate="one_to_one"
)


# --------------------------------------------------
# 7. Basic DataFrame exploration
# --------------------------------------------------

print("\nDATAFRAME SHAPE")
print("=" * 70)
print(youtube_df.shape)


print("\nCOLUMN NAMES")
print("=" * 70)

for column in youtube_df.columns:
    print(column)


print("\nDATA TYPES")
print("=" * 70)
print(youtube_df.dtypes)


print("\nMISSING VALUES")
print("=" * 70)
print(
    youtube_df.isna().sum()
)


print("\nUNIQUE VIDEO IDS")
print("=" * 70)
print(
    youtube_df["video_id"].nunique()
)


print("\nDUPLICATE VIDEO IDS")
print("=" * 70)

print(
    youtube_df[
        youtube_df.duplicated(
            subset=["video_id"],
            keep=False
        )
    ]
)


print("\nSELECTED ANALYTICS VIEW")
print("=" * 70)

selected_columns = [
    "video_id",
    "search_position",
    "detail_title",
    "detail_channel_title",
    "detail_published_at",
    "duration_raw",
    "view_count_raw",
    "like_count_raw",
    "comment_count_raw",
]

print(
    youtube_df[
        selected_columns
    ].to_string(
        index=False
    )
)