from pathlib import Path

import pandas as pd


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

PROCESSED_DATA_DIR = Path(
    "data/processed/youtube"
)

MINIMUM_VIEWS_FOR_INTERACTION = 50


# --------------------------------------------------
# 2. Find latest datasets
# --------------------------------------------------

feature_files = list(
    PROCESSED_DATA_DIR.glob(
        "youtube_video_features_*.csv"
    )
)

topic_files = list(
    PROCESSED_DATA_DIR.glob(
        "youtube_video_topics_*.csv"
    )
)


if not feature_files:
    raise FileNotFoundError(
        "No YouTube feature files found."
    )

if not topic_files:
    raise FileNotFoundError(
        "No YouTube topic files found."
    )


latest_feature_file = max(
    feature_files,
    key=lambda path: path.stat().st_mtime,
)

latest_topic_file = max(
    topic_files,
    key=lambda path: path.stat().st_mtime,
)


print("\nFILES USED")
print("=" * 90)

print(
    f"Features: {latest_feature_file}"
)

print(
    f"Topics  : {latest_topic_file}"
)


# --------------------------------------------------
# 3. Load datasets
# --------------------------------------------------

features_df = pd.read_csv(
    latest_feature_file,
    parse_dates=[
        "published_at",
        "collected_at",
    ],
)

topics_df = pd.read_csv(
    latest_topic_file,
    parse_dates=[
        "details_collected_at",
    ],
)


# --------------------------------------------------
# 4. Rename interaction metric
# --------------------------------------------------

features_df = features_df.rename(
    columns={
        "visible_interaction_rate_pct":
            "visible_interactions_per_100_views"
    }
)


# --------------------------------------------------
# 5. Join topics to video features
# --------------------------------------------------

analysis_df = topics_df.merge(
    features_df,
    left_on=[
        "video_id",
        "details_collected_at",
    ],
    right_on=[
        "video_id",
        "collected_at",
    ],
    how="left",
    validate="many_to_one",
)


if analysis_df[
    "view_count"
].isna().any():

    raise RuntimeError(
        "Some video-topic rows failed to match video features."
    )


# --------------------------------------------------
# 6. Mark interaction-eligible videos
# --------------------------------------------------

analysis_df[
    "interaction_eligible"
] = (
    (
        analysis_df[
            "view_count"
        ]
        >= MINIMUM_VIEWS_FOR_INTERACTION
    )
    &
    (
        analysis_df[
            "visible_interactions_per_100_views"
        ].notna()
    )
)


# --------------------------------------------------
# 7. Build topic-level base KPIs
# --------------------------------------------------

base_summary = (
    analysis_df
    .groupby(
        "topic"
    )
    .agg(
        sample_video_count=(
            "video_id",
            "count",
        ),

        median_views=(
            "view_count",
            "median",
        ),

        median_views_per_hour=(
            "views_per_hour_since_publish",
            "median",
        ),

        median_video_age_hours=(
            "video_age_hours",
            "median",
        ),

        median_duration_seconds=(
            "duration_seconds",
            "median",
        ),
    )
    .reset_index()
)


# --------------------------------------------------
# 8. Build thresholded interaction KPIs
# --------------------------------------------------

interaction_df = analysis_df[
    analysis_df[
        "interaction_eligible"
    ]
].copy()


interaction_summary = (
    interaction_df
    .groupby(
        "topic"
    )
    .agg(
        interaction_eligible_videos=(
            "video_id",
            "count",
        ),

        median_visible_interactions_per_100_views=(
            "visible_interactions_per_100_views",
            "median",
        ),
    )
    .reset_index()
)


# --------------------------------------------------
# 9. Calculate English-content percentage
# --------------------------------------------------

language_summary = (
    analysis_df
    .assign(
        is_english=(
            analysis_df[
                "content_language_group"
            ]
            == "English"
        )
    )
    .groupby(
        "topic"
    )
    .agg(
        english_content_pct=(
            "is_english",
            "mean",
        )
    )
    .reset_index()
)


language_summary[
    "english_content_pct"
] = (
    language_summary[
        "english_content_pct"
    ]
    * 100
)


# --------------------------------------------------
# 10. Combine KPI sections
# --------------------------------------------------

topic_kpis = (
    base_summary
    .merge(
        interaction_summary,
        on="topic",
        how="left",
        validate="one_to_one",
    )
    .merge(
        language_summary,
        on="topic",
        how="left",
        validate="one_to_one",
    )
)


# --------------------------------------------------
# 11. Add interaction coverage
# --------------------------------------------------

topic_kpis[
    "interaction_coverage_pct"
] = (
    topic_kpis[
        "interaction_eligible_videos"
    ]
    /
    topic_kpis[
        "sample_video_count"
    ]
    * 100
)


# --------------------------------------------------
# 12. Round for readability
# --------------------------------------------------

round_columns = [
    "median_views",
    "median_views_per_hour",
    "median_video_age_hours",
    "median_duration_seconds",
    "median_visible_interactions_per_100_views",
    "interaction_coverage_pct",
    "english_content_pct",
]


topic_kpis[
    round_columns
] = (
    topic_kpis[
        round_columns
    ]
    .round(2)
)


# --------------------------------------------------
# 13. Sort by median views
# --------------------------------------------------

topic_kpis = (
    topic_kpis
    .sort_values(
        "median_views",
        ascending=False,
    )
    .reset_index(
        drop=True
    )
)


# --------------------------------------------------
# 14. Display results
# --------------------------------------------------

print("\nYOUTUBE TOPIC KPI TABLE")
print("=" * 150)

print(
    topic_kpis.to_string(
        index=False
    )
)


print("\nKPI RULES")
print("=" * 90)

print(
    "Median views: all retrieved videos."
)

print(
    "Median views/hour: lifetime average attention metric, "
    "not true growth."
)

print(
    "Interaction KPI: only videos with at least "
    f"{MINIMUM_VIEWS_FOR_INTERACTION} views "
    "and complete like/comment metrics."
)

print(
    "English content %: based on derived content-language metadata."
)


# --------------------------------------------------
# 15. Save KPI table
# --------------------------------------------------

collection_timestamp = (
    features_df[
        "collected_at"
    ]
    .iloc[0]
)


timestamp_string = (
    collection_timestamp.strftime(
        "%Y%m%d_%H%M%S"
    )
)


output_file = (
    PROCESSED_DATA_DIR
    / (
        "youtube_topic_kpis_"
        f"{timestamp_string}.csv"
    )
)


topic_kpis.to_csv(
    output_file,
    index=False,
)


print("\nKPI DATA SAVED")
print("=" * 90)

print(output_file)