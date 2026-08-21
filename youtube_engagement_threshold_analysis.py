from pathlib import Path

import pandas as pd


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

PROCESSED_DATA_DIR = Path(
    "data/processed/youtube"
)

VIEW_THRESHOLDS = [
    0,
    25,
    50,
    100,
    250,
]


# --------------------------------------------------
# 2. Find latest feature and topic files
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
        "No YouTube video-topic files found."
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
# 4. Rename metric for clearer interpretation
# --------------------------------------------------

features_df = features_df.rename(
    columns={
        "visible_interaction_rate_pct":
            "visible_interactions_per_100_views"
    }
)


# --------------------------------------------------
# 5. Join topic relationships to video features
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


print("\nJOIN VALIDATION")
print("=" * 90)

print(
    "Topic relationships:",
    len(topics_df)
)

print(
    "Joined rows:",
    len(analysis_df)
)

print(
    "Missing feature matches:",
    analysis_df[
        "view_count"
    ].isna().sum()
)


# --------------------------------------------------
# 6. Threshold sensitivity — overall
# --------------------------------------------------

overall_records = []


for threshold in VIEW_THRESHOLDS:

    eligible_df = analysis_df[
        (
            analysis_df[
                "view_count"
            ] >= threshold
        )
        &
        (
            analysis_df[
                "visible_interactions_per_100_views"
            ].notna()
        )
    ]


    eligible_count = len(
        eligible_df
    )


    coverage_pct = (
        eligible_count
        / len(analysis_df)
        * 100
    )


    median_interactions = (
        eligible_df[
            "visible_interactions_per_100_views"
        ]
        .median()
    )


    p90_interactions = (
        eligible_df[
            "visible_interactions_per_100_views"
        ]
        .quantile(
            0.90
        )
    )


    max_interactions = (
        eligible_df[
            "visible_interactions_per_100_views"
        ]
        .max()
    )


    overall_records.append(
        {
            "minimum_views":
                threshold,

            "eligible_rows":
                eligible_count,

            "coverage_pct":
                coverage_pct,

            "median_interactions_per_100_views":
                median_interactions,

            "p90_interactions_per_100_views":
                p90_interactions,

            "max_interactions_per_100_views":
                max_interactions,
        }
    )


overall_df = pd.DataFrame(
    overall_records
)


overall_df[
    [
        "coverage_pct",
        "median_interactions_per_100_views",
        "p90_interactions_per_100_views",
        "max_interactions_per_100_views",
    ]
] = (
    overall_df[
        [
            "coverage_pct",
            "median_interactions_per_100_views",
            "p90_interactions_per_100_views",
            "max_interactions_per_100_views",
        ]
    ]
    .round(2)
)


print("\nOVERALL THRESHOLD SENSITIVITY")
print("=" * 110)

print(
    overall_df.to_string(
        index=False
    )
)


# --------------------------------------------------
# 7. Threshold coverage by topic
# --------------------------------------------------

topic_records = []


for threshold in VIEW_THRESHOLDS:

    for topic, topic_df in (
        analysis_df.groupby(
            "topic"
        )
    ):

        eligible_df = topic_df[
            (
                topic_df[
                    "view_count"
                ] >= threshold
            )
            &
            (
                topic_df[
                    "visible_interactions_per_100_views"
                ].notna()
            )
        ]


        eligible_count = len(
            eligible_df
        )


        coverage_pct = (
            eligible_count
            / len(topic_df)
            * 100
        )


        median_interactions = (
            eligible_df[
                "visible_interactions_per_100_views"
            ]
            .median()
        )


        topic_records.append(
            {
                "minimum_views":
                    threshold,

                "topic":
                    topic,

                "eligible_videos":
                    eligible_count,

                "coverage_pct":
                    coverage_pct,

                "median_interactions_per_100_views":
                    median_interactions,
            }
        )


topic_threshold_df = pd.DataFrame(
    topic_records
)


topic_threshold_df[
    [
        "coverage_pct",
        "median_interactions_per_100_views",
    ]
] = (
    topic_threshold_df[
        [
            "coverage_pct",
            "median_interactions_per_100_views",
        ]
    ]
    .round(2)
)


print("\nTOPIC COVERAGE BY THRESHOLD")
print("=" * 120)

print(
    topic_threshold_df.to_string(
        index=False
    )
)


# --------------------------------------------------
# 8. English vs non-English diagnostic
# --------------------------------------------------

language_summary = (
    analysis_df
    .groupby(
        "content_language_group"
    )
    .agg(
        video_topic_rows=(
            "video_id",
            "count",
        ),

        median_views=(
            "view_count",
            "median",
        ),

        median_interactions_per_100_views=(
            "visible_interactions_per_100_views",
            "median",
        ),
    )
    .reset_index()
)


language_summary[
    [
        "median_views",
        "median_interactions_per_100_views",
    ]
] = (
    language_summary[
        [
            "median_views",
            "median_interactions_per_100_views",
        ]
    ]
    .round(2)
)


print("\nLANGUAGE DIAGNOSTIC")
print("=" * 100)

print(
    language_summary.to_string(
        index=False
    )
)