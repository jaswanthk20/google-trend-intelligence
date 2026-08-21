import os

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

#----- Configuration -----
SEARCH_QUERY = "AI Agents"
REGION_CODE = "CA"
MAX_RESULTS = 25
LOOKBACK_DAYS = 7

OUTPUT_DIRECTORY = Path("data/raw")

#----- Credentials -----
load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")
if not API_KEY:
    raise RuntimeError("YOUTUBE_API_KEY was not found. Check your .env file.")

#----- Youtube Client -----
youtube = build("youtube", "v3", developerKey=API_KEY)

#----- Search Youtube -----
def search_videos() -> list[str]:
    '''Search Youtube and return video IDs for recent matching videos.'''

    published_after = (
        datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    ).isoformat().replace("+00:00", "Z")

    request = youtube.search().list(
        part = "snippet",
        q = SEARCH_QUERY,
        type = "video",
        maxResults = MAX_RESULTS,
        order = "date",
        regionCode = REGION_CODE,
        relevanceLanguage = "en",
        publishedAfter = published_after    
    )

    response = request.execute()

    video_ids = [
        item["id"]["videoId"]
        for item in response.get("items", [])
    ]

    return video_ids

