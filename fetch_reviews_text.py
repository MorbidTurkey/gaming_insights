import requests
import time
import csv
import os
from datetime import datetime

# === CONFIGURATION ===
GAME_APPIDS = [
    251950,  628750,  358130,  323190,  282070,  2415030  # Example appids, replace with your own
]
REVIEWS_PER_GAME = 1000
OUTPUT_FOLDER = "reviews_data"
RATE_LIMIT_SECONDS = 1.2

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

for appid in GAME_APPIDS:
    print(f"Fetching reviews for appid {appid}...")
    reviews = []
    cursor = "*"
    total_fetched = 0
    while total_fetched < REVIEWS_PER_GAME:
        params = {
            "json": 1,
            "filter": "all",
            "language": "all",
            "purchase_type": "all",
            "num_per_page": min(100, REVIEWS_PER_GAME - total_fetched),
            "cursor": cursor
        }
        try:
            resp = requests.get(f"https://store.steampowered.com/appreviews/{appid}", params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            batch = data.get("reviews", [])
            if not batch:
                break
            for r in batch:
                reviews.append({
                    "appid": appid,
                    "steamid": r.get("author", {}).get("steamid"),
                    "review": r.get("review"),
                    "timestamp": r.get("timestamp_created"),
                    "voted_up": r.get("voted_up"),
                    "playtime_forever": r.get("author", {}).get("playtime_forever"),
                    "language": r.get("language"),
                    "review_id": r.get("recommendationid")
                })
            total_fetched += len(batch)
            cursor = data.get("cursor", cursor)
            print(f"Fetched {total_fetched} reviews so far...")
            if len(batch) == 0:
                break
        except Exception as e:
            print(f"Error fetching reviews for appid {appid}: {e}")
            break
        time.sleep(RATE_LIMIT_SECONDS)
    # Save to CSV
    outpath = os.path.join(OUTPUT_FOLDER, f"reviews_{appid}.csv")
    with open(outpath, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=reviews[0].keys() if reviews else ["appid","steamid","review","timestamp","voted_up","playtime_forever","language","review_id"])
        writer.writeheader()
        writer.writerows(reviews)
    print(f"Saved {len(reviews)} reviews for appid {appid} to {outpath}")
print("Done.")
