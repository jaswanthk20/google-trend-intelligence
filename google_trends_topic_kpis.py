from pathlib import Path

import pandas as pd


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

PROCESSED_DATA_DIR = Path(
    "data/processed/google_trends"
)


# --------------------------------------------------
# 2. Find latest cleaned Trends dataset
# --------------------------------------------------

trend_files = list(
    PROCESSED_DATA_DIR.glob(
        "google_trends_cleaned_*.csv"
    )
)


if not trend_files:
    raise FileNotFoundError(
        "No cleaned Google Trends files found."
    )


latest_trend_file = max(
    trend_files,
    key=lambda path: path.stat().st_mtime,
)


print("\nSOURCE FILE")
print("=" * 90)

print(latest_trend_file)


# --------------------------------------------------
# 3. Load processed Trends data
# --------------------------------------------------

df = pd.read_csv(
    latest_trend_file,
    parse_dates=[
        "date",
        "collected_at",
    ],
)


# --------------------------------------------------
# 4. Remove partial periods for KPI calculation
# --------------------------------------------------

complete_df = df[
    df["is_partial"] == False
].copy()


complete_df = (
    complete_df
    .sort_values(
        [
            "topic",
            "date",
        ]
    )
)


# --------------------------------------------------
# 5. Identify latest complete date
# --------------------------------------------------

latest_complete_date = (
    complete_df[
        "date"
    ]
    .max()
)


print("\nLATEST COMPLETE DATE")
print("=" * 90)

print(
    latest_complete_date.date()
)


# --------------------------------------------------
# 6. Calculate topic KPIs
# --------------------------------------------------

records = []


for topic, topic_df in (
    complete_df.groupby(
        "topic"
    )
):

    topic_df = (
        topic_df
        .sort_values(
            "date"
        )
        .reset_index(
            drop=True
        )
    )


    # Most recent 7 complete days
    recent_7 = (
        topic_df
        .tail(7)
    )


    # Seven complete days immediately before that
    previous_7 = (
        topic_df
        .iloc[-14:-7]
    )


    if len(recent_7) < 7:
        raise RuntimeError(
            f"Not enough recent data for {topic}."
        )


    if len(previous_7) < 7:
        raise RuntimeError(
            f"Not enough previous-period data for {topic}."
        )


    latest_interest_score = (
        topic_df.iloc[-1][
            "interest_score"
        ]
    )


    recent_7d_avg = (
        recent_7[
            "interest_score"
        ]
        .mean()
    )


    previous_7d_avg = (
        previous_7[
            "interest_score"
        ]
        .mean()
    )


    change_points = (
        recent_7d_avg
        - previous_7d_avg
    )


    if previous_7d_avg == 0:

        percent_change = pd.NA

    else:

        percent_change = (
            change_points
            / previous_7d_avg
            * 100
        )


    # --------------------------------------------------
    # Momentum classification
    # --------------------------------------------------

    if (
        previous_7d_avg < 3
        and recent_7d_avg < 3
    ):

        momentum = "Low signal"

    elif change_points >= 2:

        momentum = "Rising"

    elif change_points <= -2:

        momentum = "Declining"

    else:

        momentum = "Stable"


    # --------------------------------------------------
    # Longer-window context
    # --------------------------------------------------

    three_month_avg = (
        topic_df[
            "interest_score"
        ]
        .mean()
    )


    three_month_peak = (
        topic_df[
            "interest_score"
        ]
        .max()
    )


    records.append(
        {
            "topic":
                topic,

            "latest_complete_date":
                latest_complete_date,

            "latest_interest_score":
                latest_interest_score,

            "recent_7d_avg":
                recent_7d_avg,

            "previous_7d_avg":
                previous_7d_avg,

            "change_points":
                change_points,

            "percent_change":
                percent_change,

            "momentum":
                momentum,

            "three_month_avg":
                three_month_avg,

            "three_month_peak":
                three_month_peak,

            "region_code":
                topic_df.iloc[-1][
                    "region_code"
                ],

            "search_type":
                topic_df.iloc[-1][
                    "search_type"
                ],

            "trends_collected_at":
                topic_df.iloc[-1][
                    "collected_at"
                ],
        }
    )


# --------------------------------------------------
# 7. Create topic KPI DataFrame
# --------------------------------------------------

topic_kpis = pd.DataFrame(
    records
)


# --------------------------------------------------
# 8. Convert numeric fields
# --------------------------------------------------

numeric_columns = [
    "latest_interest_score",
    "recent_7d_avg",
    "previous_7d_avg",
    "change_points",
    "percent_change",
    "three_month_avg",
    "three_month_peak",
]


for column in numeric_columns:

    topic_kpis[column] = (
        pd.to_numeric(
            topic_kpis[column],
            errors="coerce",
        )
    )


# --------------------------------------------------
# 9. Round display values
# --------------------------------------------------

round_columns = [
    "recent_7d_avg",
    "previous_7d_avg",
    "change_points",
    "percent_change",
    "three_month_avg",
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
# 10. Sort by recent search interest
# --------------------------------------------------

topic_kpis = (
    topic_kpis
    .sort_values(
        "recent_7d_avg",
        ascending=False,
    )
    .reset_index(
        drop=True
    )
)


# --------------------------------------------------
# 11. Validate grain
# --------------------------------------------------

duplicate_topics = (
    topic_kpis[
        "topic"
    ]
    .duplicated()
    .sum()
)


print("\nGOOGLE TRENDS TOPIC KPI SHAPE")
print("=" * 90)

print(
    topic_kpis.shape
)


print("\nDUPLICATE TOPICS")
print("=" * 90)

print(
    duplicate_topics
)


print("\nGOOGLE TRENDS TOPIC KPI TABLE")
print("=" * 150)

print(
    topic_kpis.to_string(
        index=False
    )
)


# --------------------------------------------------
# 12. Save KPI dataset
# --------------------------------------------------

collection_timestamp = (
    topic_kpis[
        "trends_collected_at"
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
        "google_trends_topic_kpis_"
        f"{timestamp_string}.csv"
    )
)


topic_kpis.to_csv(
    output_file,
    index=False,
)


print("\nKPI DATA SAVED")
print("=" * 90)

print(
    output_file
)