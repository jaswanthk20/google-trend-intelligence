import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# --------------------------------------------------
# 1. Load credentials
# --------------------------------------------------

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "YOUTUBE_API_KEY was not found. Check your .env file."
    )


# --------------------------------------------------
# 2. Locate raw YouTube search files
# --------------------------------------------------

RAW_DATA_DIR = Path("data/raw/youtube")

search_files = list(
    RAW_DATA_DIR.glob("youtube_search_ai_agents_*.json")
)

if not search_files:
    raise FileNotFoundError(
        "No raw YouTube search JSON files were found."
    )


# --------------------------------------------------
# 3. Select the most recently created search file
# --------------------------------------------------

latest_search_file = max(
    search_files,
    key=lambda path: path.stat().st_mtime
)

print("\nUSING RAW SEARCH FILE")
print("=" * 60)
print(latest_search_file)


# --------------------------------------------------
# 4. Load the raw search JSON
# --------------------------------------------------

with open(
    latest_search_file,
    "r",
    encoding="utf-8"
) as file:
    search_response = json.load(file)


# --------------------------------------------------
# 5. Extract video IDs
# --------------------------------------------------

video_ids = []

for item in search_response.get("items", []):
    video_id = item.get("id", {}).get("videoId")

    if video_id:
        video_ids.append(video_id)


if not video_ids:
    raise RuntimeError(
        "No video IDs were found in the raw search response."
    )


print("\nVIDEO IDS FOUND")
print("=" * 60)

for video_id in video_ids:
    print(video_id)


# --------------------------------------------------
# 6. Connect to YouTube
# --------------------------------------------------

youtube = build(
    "youtube",
    "v3",
    developerKey=API_KEY
)


# --------------------------------------------------
# 7. Request full video details
# --------------------------------------------------

try:
    request = youtube.videos().list(
        part="snippet,statistics,contentDetails",
        id=",".join(video_ids)
    )

    response = request.execute()

except HttpError as error:
    print("\nYouTube API request failed.")
    print(error)
    raise


# --------------------------------------------------
# 8. Save COMPLETE raw video-details response
# --------------------------------------------------

timestamp = datetime.now(timezone.utc).strftime(
    "%Y%m%d_%H%M%S"
)

output_file = RAW_DATA_DIR / (
    f"youtube_video_details_{timestamp}.json"
)

with open(
    output_file,
    "w",
    encoding="utf-8"
) as file:
    json.dump(
        response,
        file,
        indent=2,
        ensure_ascii=False
    )


print("\nRAW VIDEO DETAILS SAVED")
print("=" * 60)
print(output_file)


# --------------------------------------------------
# 9. Explore response structure
# --------------------------------------------------

print("\nVIDEO DETAILS RESPONSE STRUCTURE")
print("=" * 60)

print("\nTop-level keys:")
print(list(response.keys()))

items = response.get("items", [])

print("\nNumber of videos returned:")
print(len(items))


# --------------------------------------------------
# 10. Explore first video
# --------------------------------------------------

if items:
    first_video = items[0]

    print("\nFIRST VIDEO KEYS")
    print("=" * 60)
    print(list(first_video.keys()))


    snippet = first_video.get("snippet", {})
    statistics = first_video.get("statistics", {})
    content_details = first_video.get(
        "contentDetails",
        {}
    )


    print("\nSnippet keys:")
    print(list(snippet.keys()))


    print("\nStatistics keys:")
    print(list(statistics.keys()))


    print("\nContentDetails keys:")
    print(list(content_details.keys()))


    print("\nStatistics object:")
    print(
        json.dumps(
            statistics,
            indent=2,
            ensure_ascii=False
        )
    )


    print("\nContentDetails object:")
    print(
        json.dumps(
            content_details,
            indent=2,
            ensure_ascii=False
        )
    )


    print("\nCOMPLETE FIRST VIDEO")
    print("=" * 60)

    print(
        json.dumps(
            first_video,
            indent=2,
            ensure_ascii=False
        )
    )