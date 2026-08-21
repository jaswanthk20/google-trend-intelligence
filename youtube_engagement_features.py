from pathlib import Path

import pandas as pd


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

PROCESSED_DATA_DIR = Path(
    "data/processed/youtube"
)


# --------------------------------------------------
# 2. Find latest video snapshot file
# --------------------------------------------------

video_files = list(
    PROCESSED_DATA_DIR.glob(
        "youtube_video_snapshots_*.csv"
    )
)

if not video_files:
    raise FileNotFoundError(
        "No YouTube video snapshot files found."
    )


latest_video_file = max(
    video_files,
    key=lambda path: path.stat().st_mtime
)


print("\nSOURCE FILE")
print("=" * 80)
print(latest_video_file)


# --------------------------------------------------
# 3. Load video snapshots
# --------------------------------------------------

df = pd.read_csv(
    latest_video_file,
    parse_dates=[
        "published_at",
        "collected_at",
    ],
)


# --------------------------------------------------
# 4. Language helper
# --------------------------------------------------

def language_group(language_code):

    if pd.isna(language_code):
        return "Missing"

    language_code = (
        str(language_code)
        .lower()
    )

    if language_code.startswith("en"):
        return "English"

    return "Non-English"


# --------------------------------------------------
# 5. Create language dimensions
# --------------------------------------------------

df[
    "default_language_group"
] = (
    df[
        "default_language"
    ]
    .apply(
        language_group
    )
)


df[
    "audio_language_group"
] = (
    df[
        "default_audio_language"
    ]
    .apply(
        language_group
    )
)


# Prefer audio metadata when available because it
# more directly describes the video's spoken audio.
df[
    "content_language_group"
] = df[
    "audio_language_group"
]


missing_audio_mask = (
    df[
        "content_language_group"
    ]
    == "Missing"
)


df.loc[
    missing_audio_mask,
    "content_language_group"
] = (
    df.loc[
        missing_audio_mask,
        "default_language_group"
    ]
)


# --------------------------------------------------
# 6. Initialize rate columns
# --------------------------------------------------

df[
    "like_rate_pct"
] = pd.NA

df[
    "comment_rate_pct"
] = pd.NA

df[
    "visible_interaction_rate_pct"
] = pd.NA


# --------------------------------------------------
# 7. Calculate like rate
# --------------------------------------------------

like_eligible = (
    (df["view_count"] > 0)
    &
    df["like_count"].notna()
)


df.loc[
    like_eligible,
    "like_rate_pct"
] = (
    df.loc[
        like_eligible,
        "like_count"
    ]
    /
    df.loc[
        like_eligible,
        "view_count"
    ]
    * 100
)


# --------------------------------------------------
# 8. Calculate comment rate
# --------------------------------------------------

comment_eligible = (
    (df["view_count"] > 0)
    &
    df["comment_count"].notna()
)


df.loc[
    comment_eligible,
    "comment_rate_pct"
] = (
    df.loc[
        comment_eligible,
        "comment_count"
    ]
    /
    df.loc[
        comment_eligible,
        "view_count"
    ]
    * 100
)


# --------------------------------------------------
# 9. Calculate visible-interaction rate
# --------------------------------------------------

interaction_eligible = (
    (df["view_count"] > 0)
    &
    df["like_count"].notna()
    &
    df["comment_count"].notna()
)


df.loc[
    interaction_eligible,
    "visible_interaction_rate_pct"
] = (
    (
        df.loc[
            interaction_eligible,
            "like_count"
        ]
        +
        df.loc[
            interaction_eligible,
            "comment_count"
        ]
    )
    /
    df.loc[
        interaction_eligible,
        "view_count"
    ]
    * 100
)


# --------------------------------------------------
# 10. Convert derived rates to nullable floats
# --------------------------------------------------

rate_columns = [
    "like_rate_pct",
    "comment_rate_pct",
    "visible_interaction_rate_pct",
]


for column in rate_columns:

    df[column] = (
        pd.to_numeric(
            df[column],
            errors="coerce",
        )
        .astype("Float64")
    )


# --------------------------------------------------
# 11. Validation
# --------------------------------------------------

print("\nFEATURE DATASET SHAPE")
print("=" * 80)
print(df.shape)


print("\nCONTENT LANGUAGE GROUP")
print("=" * 80)

print(
    df[
        "content_language_group"
    ]
    .value_counts(
        dropna=False
    )
    .to_string()
)


print("\nRATE ELIGIBILITY")
print("=" * 80)

print(
    "Total videos:",
    len(df)
)

print(
    "Videos with zero views:",
    (df["view_count"] == 0).sum()
)

print(
    "Like-rate eligible:",
    df[
        "like_rate_pct"
    ].notna().sum()
)

print(
    "Comment-rate eligible:",
    df[
        "comment_rate_pct"
    ].notna().sum()
)

print(
    "Visible-interaction-rate eligible:",
    df[
        "visible_interaction_rate_pct"
    ].notna().sum()
)


# --------------------------------------------------
# 12. Explore interaction-rate distribution
# --------------------------------------------------

print("\nVISIBLE INTERACTION RATE DISTRIBUTION")
print("=" * 80)

print(
    df[
        "visible_interaction_rate_pct"
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
    .round(3)
)


# --------------------------------------------------
# 13. Inspect highest rates
# --------------------------------------------------

highest_rates = (
    df[
        df[
            "visible_interaction_rate_pct"
        ].notna()
    ]
    .sort_values(
        "visible_interaction_rate_pct",
        ascending=False,
    )
    [
        [
            "video_id",
            "title",
            "view_count",
            "like_count",
            "comment_count",
            "visible_interaction_rate_pct",
            "content_language_group",
        ]
    ]
    .head(15)
)


print("\nHIGHEST VISIBLE INTERACTION RATES")
print("=" * 120)

print(
    highest_rates.to_string(
        index=False
    )
)


# --------------------------------------------------
# 14. Save feature dataset
# --------------------------------------------------

collected_at = (
    df[
        "collected_at"
    ]
    .iloc[0]
)


timestamp_string = (
    collected_at.strftime(
        "%Y%m%d_%H%M%S"
    )
)


output_file = (
    PROCESSED_DATA_DIR
    / (
        "youtube_video_features_"
        f"{timestamp_string}.csv"
    )
)


df.to_csv(
    output_file,
    index=False,
)


print("\nFEATURE DATA SAVED")
print("=" * 80)

print(output_file)
