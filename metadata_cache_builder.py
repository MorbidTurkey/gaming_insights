import os
import time
import json
from dotenv import load_dotenv, find_dotenv
import requests

# Configuration
CACHE_FILE = "metadata_cache.json"
NEEDED_FILE = "needed_appids.json"
APPLIST_URL = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
STORE_DETAILS_URL = "https://store.steampowered.com/api/appdetails"
STEAMSPY_URL = "https://steamspy.com/api.php?request=appdetails&appid={}"

# Load environment (if needed)
load_dotenv(find_dotenv(), override=True)


def fetch_app_list():
    resp = requests.get(APPLIST_URL)
    resp.raise_for_status()
    return resp.json().get("applist", {}).get("apps", [])


def fetch_store_genres(appid, max_retries=3, backoff_factor=2):
    retries = 0
    while True:
        resp = requests.get(STORE_DETAILS_URL, params={"appids": appid})
        if resp.status_code == 429 and retries < max_retries:
            wait = backoff_factor ** retries
            print(f"Rate limited fetching genres for {appid}, retrying in {wait}s")
            time.sleep(wait)
            retries += 1
            continue
        resp.raise_for_status()
        data = resp.json().get(str(appid), {}).get("data", {})
        return [g.get("description") for g in data.get("genres", [])]


def fetch_spy_tags(appid):
    resp = requests.get(STEAMSPY_URL.format(appid))
    resp.raise_for_status()
    data = resp.json()
    tags = data.get("tags") if isinstance(data, dict) else None
    return list(tags.keys()) if isinstance(tags, dict) else []


def load_needed_appids():
    if os.path.exists(NEEDED_FILE):
        with open(NEEDED_FILE) as f:
            return set(json.load(f))
    return None


def load_existing_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {}


def build_metadata_cache(appids_to_fetch):
    total = len(appids_to_fetch)
    cache = {}
    for idx, appid in enumerate(appids_to_fetch, 1):
        try:
            genres = fetch_store_genres(appid)
            tags = fetch_spy_tags(appid)
        except Exception as e:
            print(f"Skipping {appid} due to error: {e}")
            genres, tags = [], []
        cache[str(appid)] = {"genres": genres, "tags": tags}
        if idx % 50 == 0 or idx == total:
            print(f"Fetched metadata for {idx}/{total} apps")
        time.sleep(0.2)
    return cache


def main():
    # Load list of needed appids (from analysis script)
    needed = load_needed_appids()
    if needed is None:
        print(f"No '{NEEDED_FILE}' found. Run analysis to generate needed appids first.")
        return
    # Load existing cache
    cache = load_existing_cache()
    # Determine which appids still need fetching
    to_fetch = [aid for aid in needed if str(aid) not in cache]
    if not to_fetch:
        print("All needed app metadata already cached.")
    else:
        print(f"Fetching metadata for {len(to_fetch)} new apps...")
        new_data = build_metadata_cache(to_fetch)
        cache.update(new_data)
        # Write updated cache
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f)
        print(f"Updated '{CACHE_FILE}' with {len(new_data)} entries. Total entries: {len(cache)}")

if __name__ == '__main__':
    main()
