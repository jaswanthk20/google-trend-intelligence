from pathlib import Path

import pandas as pd


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

RAW_DATA_DIR = Path(
    "data/raw/google_trends"
)

KEYWORDS = [
    "AI agents",
    "Agentic AI",
    "Vibe coding",
    "Model Context Protocol",
    "Multimodal AI",
]


# --------------------------------------------------
# 2. Find latest topic-basket file
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
# 3. Load raw data
# --------------------------------------------------

df = pd.read_csv(
    latest_file,
    parse_dates=["date"],
)


# --------------------------------------------------
# 4. Remove partial observations
# --------------------------------------------------

complete_df = df[
    df["isPartial"] == False
].copy()


complete_df = complete_df.sort_values(
    "date"
)


# --------------------------------------------------
# 5. Define comparison windows
# --------------------------------------------------

recent_7 = complete_df.tail(7)

previous_7 = (
    complete_df
    .iloc[-14:-7]
)


print("\nPREVIOUS WINDOW")
print("=" * 70)

print(
    f"{previous_7['date'].min().date()} "
    f"to "
    f"{previous_7['date'].max().date()}"
)


print("\nRECENT WINDOW")
print("=" * 70)

print(
    f"{recent_7['date'].min().date()} "
    f"to "
    f"{recent_7['date'].max().date()}"
)


# --------------------------------------------------
# 6. Calculate topic momentum
# --------------------------------------------------

records = []

for keyword in KEYWORDS:

    previous_avg = (
        previous_7[
            keyword
        ].mean()
    )

    recent_avg = (
        recent_7[
            keyword
        ].mean()
    )

    change_points = (
        recent_avg
        - previous_avg
    )


    if previous_avg == 0:
        percent_change = pd.NA
    else:
        percent_change = (
            change_points
            / previous_avg
            * 100
        )


    # ----------------------------------------------
    # Conservative classification
    # ----------------------------------------------

    if (
        previous_avg < 3
        and recent_avg < 3
    ):
        momentum = "Low signal"

    elif change_points >= 2:
        momentum = "Rising"

    elif change_points <= -2:
        momentum = "Declining"

    else:
        momentum = "Stable"


    records.append(
        {
            "topic": keyword,
            "previous_7d_avg": previous_avg,
            "recent_7d_avg": recent_avg,
            "change_points": change_points,
            "percent_change": percent_change,
            "momentum": momentum,
        }
    )


momentum_df = pd.DataFrame(
    records
)


# --------------------------------------------------
# 7. Sort by recent interest
# --------------------------------------------------

momentum_df = (
    momentum_df
    .sort_values(
        "recent_7d_avg",
        ascending=False
    )
    .reset_index(
        drop=True
    )
)


# --------------------------------------------------
# 8. Round for readable output
# --------------------------------------------------

display_df = momentum_df.copy()

numeric_columns = [
    "previous_7d_avg",
    "recent_7d_avg",
    "change_points",
    "percent_change",
]

display_df[
    numeric_columns
] = (
    display_df[
        numeric_columns
    ]
    .round(2)
)


# --------------------------------------------------
# 9. Display results
# --------------------------------------------------

print("\nTOPIC MOMENTUM")
print("=" * 70)

print(
    display_df.to_string(
        index=False
    )
)