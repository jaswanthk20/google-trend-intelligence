import re
from pathlib import Path

import pandas as pd


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

RAW_DATA_DIR = Path(
    "data/raw/google_trends"
)

PROCESSED_DATA_DIR = Path(
    "data/processed/google_trends"
)

PROCESSED_DATA_DIR.mkdir(
    parents=True,
    exist_ok=True
)


REGION_CODE = "CA"
TIMEFRAME = "today 3-m"
SEARCH_TYPE = "web"


# --------------------------------------------------
# 2. Find latest raw topic-basket file
# --------------------------------------------------

basket_files = list(
    RAW_DATA_DIR.glob(
        "google_trends_topic_basket_*.csv"
    )
)

if not basket_files:
    raise FileNotFoundError(
        "No Google Trends topic basket files found."
    )


latest_file = max(
    basket_files,
    key=lambda path: path.stat().st_mtime
)


print("\nFILE USED")
print("=" * 70)
print(latest_file)


# --------------------------------------------------
# 3. Derive collection timestamp from filename
# --------------------------------------------------

timestamp_match = re.search(
    r"google_trends_topic_basket_(\d{8}_\d{6})",
    latest_file.stem
)

if not timestamp_match:
    raise ValueError(
        "Could not determine collection timestamp "
        "from filename."
    )


timestamp_string = (
    timestamp_match.group(1)
)


collected_at = pd.to_datetime(
    timestamp_string,
    format="%Y%m%d_%H%M%S",
    utc=True
)


# --------------------------------------------------
# 4. Load raw dataset
# --------------------------------------------------

raw_df = pd.read_csv(
    latest_file,
    parse_dates=["date"],
)


# --------------------------------------------------
# 5. Identify topic columns
# --------------------------------------------------

metadata_columns = [
    "date",
    "isPartial",
]


topic_columns = [
    column
    for column in raw_df.columns
    if column not in metadata_columns
]


print("\nTOPICS FOUND")
print("=" * 70)

for topic in topic_columns:
    print(topic)


# --------------------------------------------------
# 6. Convert wide dataset to long format
# --------------------------------------------------

trends_df = raw_df.melt(
    id_vars=[
        "date",
        "isPartial",
    ],
    value_vars=topic_columns,
    var_name="topic",
    value_name="interest_score",
)


# --------------------------------------------------
# 7. Rename and standardize fields
# --------------------------------------------------

trends_df = trends_df.rename(
    columns={
        "isPartial": "is_partial"
    }
)


trends_df[
    "interest_score"
] = (
    pd.to_numeric(
        trends_df[
            "interest_score"
        ],
        errors="coerce"
    )
    .astype("Int64")
)


trends_df[
    "is_partial"
] = (
    trends_df[
        "is_partial"
    ]
    .astype(bool)
)


# --------------------------------------------------
# 8. Add collection context
# --------------------------------------------------

trends_df[
    "region_code"
] = REGION_CODE


trends_df[
    "timeframe"
] = TIMEFRAME


trends_df[
    "search_type"
] = SEARCH_TYPE


trends_df[
    "collected_at"
] = collected_at


# --------------------------------------------------
# 9. Arrange columns
# --------------------------------------------------

column_order = [
    "date",
    "topic",
    "interest_score",
    "is_partial",
    "region_code",
    "timeframe",
    "search_type",
    "collected_at",
]


trends_df = trends_df[
    column_order
]


# --------------------------------------------------
# 10. Sort dataset
# --------------------------------------------------

trends_df = trends_df.sort_values(
    by=[
        "date",
        "topic",
    ]
).reset_index(
    drop=True
)


# --------------------------------------------------
# 11. Validate grain
# --------------------------------------------------

duplicate_count = (
    trends_df
    .duplicated(
        subset=[
            "date",
            "topic",
            "collected_at",
        ]
    )
    .sum()
)


# --------------------------------------------------
# 12. Display validation
# --------------------------------------------------

print("\nPROCESSED DATASET SHAPE")
print("=" * 70)
print(
    trends_df.shape
)


print("\nDATA TYPES")
print("=" * 70)
print(
    trends_df.dtypes
)


print("\nMISSING VALUES")
print("=" * 70)
print(
    trends_df.isna().sum()
)


print("\nDUPLICATE GRAIN ROWS")
print("=" * 70)
print(
    duplicate_count
)


print("\nFIRST 15 ROWS")
print("=" * 70)

print(
    trends_df
    .head(15)
    .to_string(
        index=False
    )
)


print("\nLATEST COMPLETE OBSERVATIONS")
print("=" * 70)

latest_complete_date = (
    trends_df.loc[
        trends_df["is_partial"] == False,
        "date"
    ]
    .max()
)


latest_complete_df = trends_df[
    (
        trends_df["date"]
        == latest_complete_date
    )
    &
    (
        trends_df["is_partial"]
        == False
    )
]


print(
    latest_complete_df[
        [
            "date",
            "topic",
            "interest_score",
        ]
    ]
    .sort_values(
        "interest_score",
        ascending=False
    )
    .to_string(
        index=False
    )
)


# --------------------------------------------------
# 13. Save processed dataset
# --------------------------------------------------

output_file = (
    PROCESSED_DATA_DIR
    / (
        "google_trends_cleaned_"
        f"{timestamp_string}.csv"
    )
)


trends_df.to_csv(
    output_file,
    index=False
)


print("\nPROCESSED DATA SAVED")
print("=" * 70)
print(
    output_file
)