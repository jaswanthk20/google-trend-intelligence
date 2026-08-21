import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

TRENDS_DIR = Path(
    "data/processed/google_trends"
)

YOUTUBE_PROCESSED_DIR = Path(
    "data/processed/youtube"
)

YOUTUBE_RAW_DIR = Path(
    "data/raw/youtube"
)

OUTPUT_DIR = Path(
    "data/processed/combined"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# --------------------------------------------------
# 2. Find latest source files
# --------------------------------------------------

trend_files = list(
    TRENDS_DIR.glob(
        "google_trends_topic_kpis_*.csv"
    )
)

youtube_kpi_files = list(
    YOUTUBE_PROCESSED_DIR.glob(
        "youtube_topic_kpis_*.csv"
    )
)

youtube_search_files = list(
    YOUTUBE_RAW_DIR.glob(
        "youtube_topic_basket_search_*.json"
    )
)


if not trend_files:
    raise FileNotFoundError(
        "No Google Trends topic KPI files found."
    )

if not youtube_kpi_files:
    raise FileNotFoundError(
        "No YouTube topic KPI files found."
    )

if not youtube_search_files:
    raise FileNotFoundError(
        "No YouTube topic-basket search files found."
    )


latest_trend_file = max(
    trend_files,
    key=lambda path: path.stat().st_mtime,
)

latest_youtube_kpi_file = max(
    youtube_kpi_files,
    key=lambda path: path.stat().st_mtime,
)

latest_youtube_search_file = max(
    youtube_search_files,
    key=lambda path: path.stat().st_mtime,
)


print("\nFILES USED")
print("=" * 100)

print(
    f"Google Trends KPI : {latest_trend_file}"
)

print(
    f"YouTube KPI       : {latest_youtube_kpi_file}"
)

print(
    f"YouTube search    : {latest_youtube_search_file}"
)


# --------------------------------------------------
# 3. Load Google Trends KPI table
# --------------------------------------------------

trends_df = pd.read_csv(
    latest_trend_file,
    parse_dates=[
        "latest_complete_date",
        "trends_collected_at",
    ],
)


# --------------------------------------------------
# 4. Load YouTube KPI table
# --------------------------------------------------

youtube_df = pd.read_csv(
    latest_youtube_kpi_file
)


# --------------------------------------------------
# 5. Derive YouTube collection timestamp
#    from KPI filename
# --------------------------------------------------

youtube_timestamp_match = re.search(
    r"youtube_topic_kpis_(\d{8}_\d{6})",
    latest_youtube_kpi_file.stem,
)


if not youtube_timestamp_match:
    raise ValueError(
        "Could not determine YouTube collection "
        "timestamp from KPI filename."
    )


youtube_timestamp_string = (
    youtube_timestamp_match.group(1)
)


youtube_collected_at = pd.to_datetime(
    youtube_timestamp_string,
    format="%Y%m%d_%H%M%S",
    utc=True,
)


# --------------------------------------------------
# 6. Load raw YouTube topic-search metadata
# --------------------------------------------------

with open(
    latest_youtube_search_file,
    "r",
    encoding="utf-8",
) as file:

    youtube_search_data = json.load(
        file
    )


request_metadata = (
    youtube_search_data.get(
        "request_metadata",
        {}
    )
)

topic_responses = (
    youtube_search_data.get(
        "topic_responses",
        {}
    )
)


youtube_window_start = pd.to_datetime(
    request_metadata.get(
        "published_after"
    ),
    utc=True,
    errors="coerce",
)


youtube_window_end = pd.to_datetime(
    request_metadata.get(
        "published_before"
    ),
    utc=True,
    errors="coerce",
)


# --------------------------------------------------
# 7. Rebuild YouTube supply diagnostic
# --------------------------------------------------

supply_records = []


for topic, response in (
    topic_responses.items()
):

    items = response.get(
        "items",
        []
    )

    page_info = response.get(
        "pageInfo",
        {}
    )


    supply_records.append(
        {
            "topic":
                topic,

            "returned_sample_count":
                len(items),

            "estimated_indexed_results":
                page_info.get(
                    "totalResults"
                ),

            "has_more_pages":
                "nextPageToken"
                in response,
        }
    )


supply_df = pd.DataFrame(
    supply_records
)


supply_df[
    "estimated_indexed_results"
] = pd.to_numeric(
    supply_df[
        "estimated_indexed_results"
    ],
    errors="coerce",
)


max_estimated_results = (
    supply_df[
        "estimated_indexed_results"
    ].max()
)


supply_df[
    "relative_supply_index"
] = (
    supply_df[
        "estimated_indexed_results"
    ]
    / max_estimated_results
    * 100
)


supply_df[
    "relative_supply_index"
] = (
    supply_df[
        "relative_supply_index"
    ]
    .round(2)
)


# --------------------------------------------------
# 8. Validate topic grain before joining
# --------------------------------------------------

print("\nSOURCE GRAIN VALIDATION")
print("=" * 100)

print(
    "Trends topics:",
    trends_df[
        "topic"
    ].nunique()
)

print(
    "YouTube KPI topics:",
    youtube_df[
        "topic"
    ].nunique()
)

print(
    "YouTube supply topics:",
    supply_df[
        "topic"
    ].nunique()
)


print(
    "Duplicate Trends topics:",
    trends_df[
        "topic"
    ].duplicated().sum()
)

print(
    "Duplicate YouTube KPI topics:",
    youtube_df[
        "topic"
    ].duplicated().sum()
)

print(
    "Duplicate supply topics:",
    supply_df[
        "topic"
    ].duplicated().sum()
)


# --------------------------------------------------
# 9. Check topic-set consistency
# --------------------------------------------------

trend_topics = set(
    trends_df[
        "topic"
    ]
)

youtube_topics = set(
    youtube_df[
        "topic"
    ]
)

supply_topics = set(
    supply_df[
        "topic"
    ]
)


all_topics_match = (
    trend_topics
    == youtube_topics
    == supply_topics
)


print("\nTOPIC SETS MATCH")
print("=" * 100)

print(
    all_topics_match
)


if not all_topics_match:

    print(
        "\nTrends only:",
        trend_topics
        - youtube_topics
    )

    print(
        "YouTube only:",
        youtube_topics
        - trend_topics
    )

    raise RuntimeError(
        "Topic sets do not match across sources."
    )


# --------------------------------------------------
# 10. Join Trends + YouTube performance
# --------------------------------------------------

combined_df = trends_df.merge(
    youtube_df,
    on="topic",
    how="inner",
    validate="one_to_one",
)


# --------------------------------------------------
# 11. Add YouTube supply diagnostic
# --------------------------------------------------

combined_df = combined_df.merge(
    supply_df,
    on="topic",
    how="left",
    validate="one_to_one",
)


# --------------------------------------------------
# 12. Add source timing context
# --------------------------------------------------

combined_df[
    "youtube_collected_at"
] = youtube_collected_at


combined_df[
    "youtube_window_start"
] = youtube_window_start


combined_df[
    "youtube_window_end"
] = youtube_window_end


combined_df[
    "analysis_generated_at"
] = datetime.now(
    timezone.utc
)


# --------------------------------------------------
# 13. Validate final dataset
# --------------------------------------------------

print("\nCOMBINED DATASET SHAPE")
print("=" * 100)

print(
    combined_df.shape
)


print("\nMISSING TOPIC-LEVEL VALUES")
print("=" * 100)

print(
    combined_df.isna().sum()
)


print("\nDUPLICATE TOPICS")
print("=" * 100)

print(
    combined_df[
        "topic"
    ]
    .duplicated()
    .sum()
)


# --------------------------------------------------
# 14. Create focused analysis view
# --------------------------------------------------

analysis_columns = [
    "topic",

    # Google Trends demand
    "latest_interest_score",
    "recent_7d_avg",
    "previous_7d_avg",
    "change_points",
    "momentum",

    # YouTube supply proxy
    "estimated_indexed_results",
    "relative_supply_index",

    # YouTube actual sample performance
    "median_views",
    "median_views_per_hour",
    "median_visible_interactions_per_100_views",
    "interaction_coverage_pct",
    "english_content_pct",
]


analysis_view = combined_df[
    analysis_columns
].copy()


analysis_view = (
    analysis_view
    .sort_values(
        "recent_7d_avg",
        ascending=False,
    )
    .reset_index(
        drop=True
    )
)


print("\nCROSS-SOURCE TOPIC ANALYSIS")
print("=" * 170)

print(
    analysis_view.to_string(
        index=False
    )
)


# --------------------------------------------------
# 15. Save complete combined dataset
# --------------------------------------------------

generated_timestamp = datetime.now(
    timezone.utc
).strftime(
    "%Y%m%d_%H%M%S"
)


output_file = (
    OUTPUT_DIR
    / (
        "cross_source_topic_analysis_"
        f"{generated_timestamp}.csv"
    )
)


combined_df.to_csv(
    output_file,
    index=False,
)


print("\nCOMBINED DATA SAVED")
print("=" * 100)

print(
    output_file
)