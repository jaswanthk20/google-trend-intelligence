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
# 3. Display request
# --------------------------------------------------

print("\nREQUEST CONFIGURATION")
print("=" * 70)

print(f"Keywords  : {KEYWORDS}")
print(f"Geography : {GEO}")
print(f"Timeframe : {TIMEFRAME}")


# --------------------------------------------------
# 4. Build ONE shared comparison request
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
# 6. Timestamp the raw extract
# --------------------------------------------------

collected_at = datetime.now(
    timezone.utc
)

timestamp = collected_at.strftime(
    "%Y%m%d_%H%M%S"
)


# --------------------------------------------------
# 7. Save raw CSV
# --------------------------------------------------

csv_file = (
    RAW_DATA_DIR
    / f"google_trends_comparison_{timestamp}.csv"
)

interest_df.to_csv(
    csv_file
)


# --------------------------------------------------
# 8. Save raw JSON
# --------------------------------------------------

json_file = (
    RAW_DATA_DIR
    / f"google_trends_comparison_{timestamp}.json"
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
    encoding="utf-8",
) as file:

    json.dump(
        json_records,
        file,
        indent=2,
        ensure_ascii=False,
        default=str,
    )


# --------------------------------------------------
# 9. Explore comparison
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


print("\nFIRST 10 ROWS")
print("=" * 70)

print(
    interest_df
    .head(10)
    .to_string()
)


print("\nLAST 10 ROWS")
print("=" * 70)

print(
    interest_df
    .tail(10)
    .to_string()
)


# --------------------------------------------------
# 10. Compare maximum interest
# --------------------------------------------------

print("\nMAXIMUM INTEREST BY KEYWORD")
print("=" * 70)

for keyword in KEYWORDS:

    print(
        f"{keyword}: "
        f"{interest_df[keyword].max()}"
    )


# --------------------------------------------------
# 11. Compare mean interest
# --------------------------------------------------

print("\nAVERAGE INTEREST BY KEYWORD")
print("=" * 70)

for keyword in KEYWORDS:

    print(
        f"{keyword}: "
        f"{interest_df[keyword].mean():.2f}"
    )


# --------------------------------------------------
# 12. Exclude partial observations
# --------------------------------------------------

complete_df = interest_df[
    interest_df["isPartial"] == False
].copy()


print("\nLATEST COMPLETE OBSERVATION")
print("=" * 70)

print(
    complete_df
    .tail(1)
    .to_string()
)


print("\nRAW FILES SAVED")
print("=" * 70)

print(f"CSV : {csv_file}")
print(f"JSON: {json_file}")