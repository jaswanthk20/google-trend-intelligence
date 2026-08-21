import json
from datetime import datetime, timezone
from pathlib import Path

from pytrends_modern import TrendReq


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

KEYWORD = "AI agents"
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
# 3. Build request
# --------------------------------------------------

print("\nREQUEST CONFIGURATION")
print("=" * 70)

print(f"Keyword   : {KEYWORD}")
print(f"Geography : {GEO}")
print(f"Timeframe : {TIMEFRAME}")


pytrends.build_payload(
    kw_list=[KEYWORD],
    timeframe=TIMEFRAME,
    geo=GEO,
    gprop="",
)


# --------------------------------------------------
# 4. Retrieve interest-over-time data
# --------------------------------------------------

interest_df = (
    pytrends.interest_over_time()
)


if interest_df.empty:
    raise RuntimeError(
        "Google Trends returned an empty dataset."
    )


# --------------------------------------------------
# 5. Record when this extract was collected
# --------------------------------------------------

collected_at = datetime.now(
    timezone.utc
)

timestamp = collected_at.strftime(
    "%Y%m%d_%H%M%S"
)


# --------------------------------------------------
# 6. Save unmodified source extract
# --------------------------------------------------

csv_file = (
    RAW_DATA_DIR
    / f"google_trends_ai_agents_{timestamp}.csv"
)

interest_df.to_csv(
    csv_file
)


# Also save a JSON representation
json_file = (
    RAW_DATA_DIR
    / f"google_trends_ai_agents_{timestamp}.json"
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
# 7. Explore the returned structure
# --------------------------------------------------

print("\nRAW GOOGLE TRENDS DATA SAVED")
print("=" * 70)

print(f"CSV : {csv_file}")
print(f"JSON: {json_file}")


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


print("\nINDEX")
print("=" * 70)

print(
    interest_df.index.name
)


print("\nDATA TYPES")
print("=" * 70)

print(
    interest_df.dtypes
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


print("\nBASIC STATISTICS")
print("=" * 70)

print(
    interest_df[
        KEYWORD
    ].describe()
)