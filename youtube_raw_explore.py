import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

#----- Load Credentials -----
load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")

if not API_KEY:
    raise RuntimeError("YOUTUBE_API_KEY was not found. Check your .env file.")

#----- Configuration -----
RAW_DATA_DIR = Path("data/raw/youtube")
RAW_DATA_DIR.mkdir(
    parents=True,
    exist_ok=True
)

#----- Connect to Youtube -----
youtube = build(
    "youtube",
    "v3",
    developerKey=API_KEY
)

#----- One Search Request -----
try:
    request = youtube.search().list(
        part="snippet",
        q="AI agents",
        type="video",
        maxResults=5,
        order="date",
        
    )

    response = request.execute()

except HttpError as error:
    print("\nYoutube API request failed.")
    print(error)
    raise

#----- Create timestamped raw-data filename -----
timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
file_path = RAW_DATA_DIR / (f"youtube_search_ai_agents_{timestamp}.json")

#----- Save complete response -----
with open (file_path, "w", encoding="utf-8") as f:
    json.dump(response, f, indent=4, ensure_ascii=False)

print("\nRAW DATA SAVED")
print("="*60)
print(f"File:{file_path}")

#----- Explore response structure-----
print("\nRESPONSE STRUCTURE")
print("="*60)

print("\nTop-level keys:")
print(list(response.keys()))

items = response.get("items", [])

print("\nNumber of items in response:")
print(len(items))

if "pageInfo" in response:
    print("\nPage information:")
    print(response["pageInfo"])

if "nextPageToken" in response:
    print("\nNext page token exists:")
    print(True)

else: 
    print("\nNext page token exists:")
    print(False)

#----- Explore one video result -----
if items:

    first_item = items[0]

    print("\nFIRST ITEM STRUCTURE")
    print("=" * 60)

    print("\nFirst item keys:")
    print(list(first_item.keys()))


    print("\nID object:")
    print(
        json.dumps(
            first_item.get("id", {}),
            indent=2,
            ensure_ascii=False
        )
    )


    snippet = first_item.get(
        "snippet",
        {}
    )

    print("\nSnippet keys:")
    print(list(snippet.keys()))


    print("\nComplete first item:")
    print(
        json.dumps(
            first_item,
            indent=2,
            ensure_ascii=False
        )
    )
