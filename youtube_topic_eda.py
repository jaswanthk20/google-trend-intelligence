from pathlib import Path

import pandas as pd


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

PROCESSED_DATA_DIR = Path(
    "data/processed/youtube"
)


# --------------------------------------------------
# 2. Find latest processed files
# --------------------------------------------------

video_files = list(
    PROCESSED_DATA_DIR.glob(
        "youtube_video_snapshots_*.csv"
    )
)

topic_files = list(
    PROCESSED_DATA_DIR.glob(
        "youtube_video_topics_*.csv"
    )
)


if not video_files:
    raise FileNotFoundError(
        "No processed YouTube video snapshot files found."
    )

if not topic_files:
    raise FileNotFoundError(
        "No processed YouTube video-topic files found."
    )


latest_video_file = max(
    video_files,
    key=lambda path: path.stat().st_mtime
)

latest_topic_file = max(
    topic_files,
    key=lambda path: path.stat().st_mtime
)


print("\nFILES USED")
print("=" * 80)

print(
    f"Videos: {latest_video_file}"
)

print(
    f"Topics: {latest_topic_file}"
)


# --------------------------------------------------
# 3. Load processed datasets
# --------------------------------------------------

videos_df = pd.read_csv(
    latest_video_file,
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
# 4. Join topic relationships to video metrics
# --------------------------------------------------

analysis_df = topics_df.merge(
    videos_df,
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


# --------------------------------------------------
# 5. Validate join
# --------------------------------------------------

print("\nJOIN VALIDATION")
print("=" * 80)

print(
    "Relationship rows:",
    len(topics_df)
)

print(
    "Joined rows:",
    len(analysis_df)
)

print(
    "Rows missing video metrics:",
    analysis_df[
        "view_count"
    ].isna().sum()
)


# --------------------------------------------------
# 6. Overall view distribution
# --------------------------------------------------

print("\nOVERALL VIEW DISTRIBUTION")
print("=" * 80)

print(
    analysis_df[
        "view_count"
    ]
    .describe(
        percentiles=[
            0.25,
            0.50,
            0.75,
            0.90,
            0.95,
        ]
    )
    .round(2)
)


# --------------------------------------------------
# 7. Topic-level metrics
# --------------------------------------------------

topic_summary = (
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

        mean_views=(
            "view_count",
            "mean",
        ),

        max_views=(
            "view_count",
            "max",
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

        videos_missing_likes=(
            "like_count",
            lambda x: x.isna().sum(),
        ),

        videos_missing_comments=(
            "comment_count",
            lambda x: x.isna().sum(),
        ),
    )
    .reset_index()
)


# --------------------------------------------------
# 8. Calculate 90th percentile views separately
# --------------------------------------------------

p90_views = (
    analysis_df
    .groupby(
        "topic"
    )[
        "view_count"
    ]
    .quantile(
        0.90
    )
    .rename(
        "p90_views"
    )
    .reset_index()
)


topic_summary = (
    topic_summary
    .merge(
        p90_views,
        on="topic",
        how="left",
        validate="one_to_one",
    )
)


# --------------------------------------------------
# 9. Arrange columns
# --------------------------------------------------

topic_summary = topic_summary[
    [
        "topic",
        "sample_video_count",
        "median_views",
        "mean_views",
        "p90_views",
        "max_views",
        "median_views_per_hour",
        "median_video_age_hours",
        "median_duration_seconds",
        "videos_missing_likes",
        "videos_missing_comments",
    ]
]


# --------------------------------------------------
# 10. Sort by median views
# --------------------------------------------------

topic_summary = (
    topic_summary
    .sort_values(
        "median_views",
        ascending=False,
    )
    .reset_index(
        drop=True
    )
)


# --------------------------------------------------
# 11. Round numeric values for display
# --------------------------------------------------

display_summary = (
    topic_summary.copy()
)


columns_to_round = [
    "median_views",
    "mean_views",
    "p90_views",
    "median_views_per_hour",
    "median_video_age_hours",
    "median_duration_seconds",
]


display_summary[
    columns_to_round
] = (
    display_summary[
        columns_to_round
    ]
    .round(2)
)


print("\nTOPIC PERFORMANCE SUMMARY")
print("=" * 120)

print(
    display_summary.to_string(
        index=False
    )
)


# --------------------------------------------------
# 12. Highest-viewed video in each topic
# --------------------------------------------------

top_video_indices = (
    analysis_df
    .groupby(
        "topic"
    )[
        "view_count"
    ]
    .idxmax()
)


top_videos = (
    analysis_df
    .loc[
        top_video_indices,
        [
            "topic",
            "video_id",
            "title",
            "channel_title",
            "view_count",
            "like_count",
            "comment_count",
            "video_age_hours",
        ],
    ]
    .sort_values(
        "view_count",
        ascending=False,
    )
)


print("\nHIGHEST-VIEWED VIDEO PER TOPIC")
print("=" * 120)

print(
    top_videos.to_string(
        index=False
    )
)
