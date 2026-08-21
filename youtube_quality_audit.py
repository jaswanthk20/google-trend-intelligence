from pathlib import Path

import pandas as pd


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

PROCESSED_DATA_DIR = Path(
    "data/processed/youtube"
)


# --------------------------------------------------
# 2. Find latest processed datasets
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
        "No YouTube video snapshot files found."
    )

if not topic_files:
    raise FileNotFoundError(
        "No YouTube video-topic files found."
    )


latest_video_file = max(
    video_files,
    key=lambda path: path.stat().st_mtime
)

latest_topic_file = max(
    topic_files,
    key=lambda path: path.stat().st_mtime
)


# --------------------------------------------------
# 3. Load datasets
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
# 4. General quality checks
# --------------------------------------------------

print("\nGENERAL QUALITY CHECKS")
print("=" * 80)

print(
    "Unique videos:",
    videos_df["video_id"].nunique()
)

print(
    "Video-topic relationships:",
    len(analysis_df)
)

print(
    "Zero-view videos:",
    (videos_df["view_count"] == 0).sum()
)

print(
    "Missing like counts:",
    videos_df["like_count"].isna().sum()
)

print(
    "Missing comment counts:",
    videos_df["comment_count"].isna().sum()
)

print(
    "Negative video ages:",
    (videos_df["video_age_hours"] < 0).sum()
)

print(
    "Zero/negative durations:",
    (videos_df["duration_seconds"] <= 0).sum()
)


# --------------------------------------------------
# 5. Language distributions
# --------------------------------------------------

print("\nDEFAULT LANGUAGE DISTRIBUTION")
print("=" * 80)

print(
    videos_df[
        "default_language"
    ]
    .fillna("MISSING")
    .value_counts(
        dropna=False
    )
    .to_string()
)


print("\nDEFAULT AUDIO LANGUAGE DISTRIBUTION")
print("=" * 80)

print(
    videos_df[
        "default_audio_language"
    ]
    .fillna("MISSING")
    .value_counts(
        dropna=False
    )
    .to_string()
)


# --------------------------------------------------
# 6. Non-English-looking API language metadata
# --------------------------------------------------

non_english_mask = (
    (
        videos_df[
            "default_language"
        ].notna()
    )
    &
    (
        ~videos_df[
            "default_language"
        ].str.lower().str.startswith(
            "en",
            na=False,
        )
    )
)


non_english_df = videos_df[
    non_english_mask
].copy()


print("\nNON-ENGLISH DEFAULT LANGUAGE VIDEOS")
print("=" * 80)

print(
    "Count:",
    len(non_english_df)
)


if not non_english_df.empty:

    print(
        non_english_df[
            [
                "video_id",
                "title",
                "channel_title",
                "default_language",
                "default_audio_language",
                "view_count",
            ]
        ]
        .sort_values(
            "view_count",
            ascending=False,
        )
        .head(20)
        .to_string(
            index=False
        )
    )


# --------------------------------------------------
# 7. Quality checks by topic
# --------------------------------------------------

topic_quality = (
    analysis_df
    .groupby(
        "topic"
    )
    .agg(
        sample_rows=(
            "video_id",
            "count",
        ),

        zero_view_videos=(
            "view_count",
            lambda x: (x == 0).sum(),
        ),

        missing_likes=(
            "like_count",
            lambda x: x.isna().sum(),
        ),

        missing_comments=(
            "comment_count",
            lambda x: x.isna().sum(),
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


topic_quality[
    [
        "median_video_age_hours",
        "median_duration_seconds",
    ]
] = (
    topic_quality[
        [
            "median_video_age_hours",
            "median_duration_seconds",
        ]
    ]
    .round(2)
)


print("\nQUALITY BY TOPIC")
print("=" * 100)

print(
    topic_quality.to_string(
        index=False
    )
)


# --------------------------------------------------
# 8. Videos with zero views
# --------------------------------------------------

zero_view_df = videos_df[
    videos_df[
        "view_count"
    ] == 0
]


print("\nZERO-VIEW VIDEO SAMPLE")
print("=" * 100)

print(
    "Count:",
    len(zero_view_df)
)


if not zero_view_df.empty:

    print(
        zero_view_df[
            [
                "video_id",
                "title",
                "published_at",
                "video_age_hours",
                "like_count",
                "comment_count",
            ]
        ]
        .head(15)
        .to_string(
            index=False
        )
    )