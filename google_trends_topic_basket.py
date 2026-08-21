import json
from datetime import datetime, timezone
from pathlib import Path

from pytrends_modern import TrendReq


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

KEYWORDS = [
    "AI agents",
    "Agentic AI",
    "Vibe coding",
    "Model Context Protocol",
    "Multimodal AI",
]

GEO = "CA"
TIMEFRAME = "today 3-m"

RAW_DATA_DIR = Path(
    "data/raw/google_trends"
)

RAW_DATA_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# --------------------------------------------------
# 2. Connect to Google Trends
# --------------------------------------------------

pytrends = TrendReq(
    hl="en-CA",
    tz=0,
    retries=2,
    backoff_factor=0.5,
)


# --------------------------------------------------
# 3. Display configuration
# --------------------------------------------------

print("\nTOPIC BASKET")
print("=" * 70)

for keyword in KEYWORDS:
    print(keyword)

print(f"\nGeography : {GEO}")
print(f"Timeframe : {TIMEFRAME}")


# --------------------------------------------------
# 4. Build ONE comparison request
# --------------------------------------------------

pytrends.build_payload(
    kw_list=KEYWORDS,
    timeframe=TIMEFRAME,
    geo=GEO,
    gprop="",
)


# --------------------------------------------------
# 5. Retrieve interest-over-time data
# --------------------------------------------------

interest_df = (
    pytrends.interest_over_time()
)


if interest_df.empty:
    raise RuntimeError(
        "Google Trends returned an empty dataset."
    )


# --------------------------------------------------
# 6. Collection timestamp
# --------------------------------------------------

collected_at = datetime.now(
    timezone.utc
)

timestamp = collected_at.strftime(
    "%Y%m%d_%H%M%S"
)


# --------------------------------------------------
# 7. Save raw source data
# --------------------------------------------------

csv_file = (
    RAW_DATA_DIR
    / f"google_trends_topic_basket_{timestamp}.csv"
)

interest_df.to_csv(
    csv_file
)


json_file = (
    RAW_DATA_DIR
    / f"google_trends_topic_basket_{timestamp}.json"
)


json_records = (
    interest_df
    .reset_index()
    .to_dict(
        orient="records"
    )
)


with open(
    json_file,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        json_records,
        file,
        indent=2,
        ensure_ascii=False,
        default=str,
    )


# --------------------------------------------------
# 8. Remove partial observations for analysis
# --------------------------------------------------

complete_df = interest_df[
    interest_df["isPartial"] == False
].copy()


# --------------------------------------------------
# 9. Basic profile
# --------------------------------------------------

print("\nDATAFRAME SHAPE")
print("=" * 70)
print(
    interest_df.shape
)


print("\nCOLUMN NAMES")
print("=" * 70)
print(
    list(
        interest_df.columns
    )
)


print("\nMAXIMUM INTEREST")
print("=" * 70)

for keyword in KEYWORDS:
    print(
        f"{keyword:<25} "
        f"{complete_df[keyword].max()}"
    )


print("\nAVERAGE INTEREST")
print("=" * 70)

for keyword in KEYWORDS:
    print(
        f"{keyword:<25} "
        f"{complete_df[keyword].mean():.2f}"
    )


# --------------------------------------------------
# 10. Latest complete observation
# --------------------------------------------------

print("\nLATEST COMPLETE OBSERVATION")
print("=" * 70)

print(
    complete_df
    .tail(1)
    .to_string()
)


# --------------------------------------------------
# 11. Recent 7-day average
# --------------------------------------------------

recent_7_days = (
    complete_df
    .tail(7)
)


print("\nRECENT 7-DAY AVERAGE")
print("=" * 70)

for keyword in KEYWORDS:

    average = (
        recent_7_days[
            keyword
        ].mean()
    )

    print(
        f"{keyword:<25} "
        f"{average:.2f}"
    )


# --------------------------------------------------
# 12. Save locations
# --------------------------------------------------

print("\nRAW FILES SAVED")
print("=" * 70)

print(f"CSV : {csv_file}")
print(f"JSON: {json_file}")