import os

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")

if not API_KEY:
    raise RuntimeError("YOUTUBE_API_KEY was not found. Check your .env file.")

def main() -> None:
    youtube = build(
        "youtube",
        "v3",
        developerKey=API_KEY
    )

    try:
        request = youtube.search().list(
            part="snippet",
            q="AI agents",
            type="video",
            maxResults=5,
            order="date",
            regionCode="CA",
            relevanceLanguage="en",
        )

        response = request.execute()

        print("\nLive Youtube Results")
        print("=" * 60)

        for number, item in enumerate(response["items"], start=1):
            video_id = item["id"]["videoId"]
            snippet = item["snippet"]

            title = snippet["title"]
            channel = snippet["channelTitle"]
            published_at = snippet["publishedAt"]

            print(f"\n{number}. {title}")
            print(f"   Channel: {channel}")
            print(f"   Published: {published_at}")
            print(f"   Video ID: {video_id}")

    except HttpError as error:
        print("\nYoutube API request failed.")
        print(error)

if __name__ == "__main__":
    main()