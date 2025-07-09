import requests
import pandas as pd
import time
import json
import os
from datetime import datetime

STEAMSPY_ALL_API = "https://steamspy.com/api.php?request=all"
STEAMSPY_APPDETAILS_API = "https://steamspy.com/api.php?request=appdetails&appid={appid}"
DATE_STR = datetime.now().strftime("%Y-%m-%d")
OUTPUT_CSV = f"steamspy_full_db_{DATE_STR}.csv"
OUTPUT_PARQUET = f"steamspy_full_db_{DATE_STR}.parquet"
DETAILS_CACHE = f"steamspy_full_details_cache_{DATE_STR}.json"
LOG_FILE = "steamspy_db_update_log.txt"
RATE_LIMIT_SECONDS = 1.2

# 1. Download all games summary from SteamSpy
print("Fetching all games summary from SteamSpy...")
resp = requests.get(STEAMSPY_ALL_API)
resp.raise_for_status()
all_games = resp.json()
print(f"Fetched {len(all_games)} games.")

# 2. Convert to DataFrame
rows = []
for appid, data in all_games.items():
    row = data.copy()
    row['appid'] = int(appid)
    rows.append(row)
df = pd.DataFrame(rows)

# 3. Optionally, fetch details for each game (genres, tags, release date)
#    This is slow, so we cache results.
if os.path.exists(DETAILS_CACHE):
    with open(DETAILS_CACHE, "r", encoding="utf-8") as f:
        details_cache = json.load(f)
else:
    details_cache = {}

details_needed = [str(appid) for appid in df['appid'] if str(appid) not in details_cache]
print(f"Need to fetch details for {len(details_needed)} games...")

for i, appid in enumerate(details_needed):
    for attempt in range(3):
        try:
            resp = requests.get(STEAMSPY_APPDETAILS_API.format(appid=appid), timeout=10)
            if resp.status_code == 200:
                details_cache[appid] = resp.json()
                break
        except Exception as e:
            print(f"Error fetching details for {appid}: {e}")
        time.sleep(RATE_LIMIT_SECONDS)
    else:
        details_cache[appid] = {}
    if (i+1) % 100 == 0:
        print(f"Fetched {i+1}/{len(details_needed)} details...")
        with open(DETAILS_CACHE, "w", encoding="utf-8") as f:
            json.dump(details_cache, f, ensure_ascii=False, indent=2)
    time.sleep(RATE_LIMIT_SECONDS)

# Save cache at end
with open(DETAILS_CACHE, "w", encoding="utf-8") as f:
    json.dump(details_cache, f, ensure_ascii=False, indent=2)

# 4. Merge details into main DataFrame
#    We'll add columns: genre, tags, release_date

def get_detail(appid, key):
    d = details_cache.get(str(appid), {})
    if key == 'tags':
        return list(d.get('tags', {}).keys()) if d.get('tags') else []
    if key == 'languages':
        return d.get('languages', '').split(', ') if d.get('languages') else []
    return d.get(key, None)

# Add more fields from appdetails
extra_fields = [
    'developer', 'publisher', 'languages', 'score_rank', 'positive', 'negative',
    'userscore', 'owners', 'average_forever', 'average_2weeks', 'median_forever',
    'median_2weeks', 'ccu', 'price', 'initialprice', 'discount', 'release_date',
    'genre', 'tags'
]

for field in extra_fields:
    if field in ['genre', 'tags', 'release_date', 'languages']:
        # Already handled or special handling
        continue
    df[field] = df['appid'].apply(lambda x: get_detail(x, field))

df['genre'] = df['appid'].apply(lambda x: get_detail(x, 'genre'))
df['tags'] = df['appid'].apply(lambda x: get_detail(x, 'tags'))
df['release_date'] = df['appid'].apply(lambda x: get_detail(x, 'release_date'))
df['languages'] = df['appid'].apply(lambda x: get_detail(x, 'languages'))

# 5. Save to CSV and Parquet
print(f"Saving to {OUTPUT_CSV} and {OUTPUT_PARQUET}...")
df.to_csv(OUTPUT_CSV, index=False)
df.to_parquet(OUTPUT_PARQUET, index=False)
print("Done.")
