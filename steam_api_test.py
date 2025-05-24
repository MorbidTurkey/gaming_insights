#!/usr/bin/env python3
import os
from dotenv import load_dotenv

# load .env
load_dotenv()
STEAM_KEY = os.getenv("STEAM_API_KEY")
if not STEAM_KEY:
    raise RuntimeError("STEAM_API_KEY not set in environment")
import time
import requests
import pandas as pd
from datetime import datetime
from collections import Counter

# ─── CONFIG ─────────────────────────────────────────────────────────────────────
GAME_TITLE       = "Slay the Spire"
COUNTRY_CODES    = ["us"]               # list of region codes
LANGUAGE         = "all"               # review language filter
NUM_PER_PAGE     = 100                  # reviews per request
START_DATE       = "2025-01-01"        # inclusive, YYYY-MM-DD
END_DATE         = "2025-12-05"        # inclusive, YYYY-MM-DD
MAX_REVIEWS      = 1000                 # max reviews to sample
YEAR             = datetime.now().year  # for file naming

# Play-based similars settings
TOP_N_PLAY_SIM   = 10                   # top N play-based similars
SAMPLE_SIZE_PLAY = 1000                 # sample size for play-based similars

# ─── HELPERS ────────────────────────────────────────────────────────────────────
def find_app_id(title, country="us", lang="en"):
    url = "https://store.steampowered.com/api/storesearch/"
    resp = requests.get(url, params={"term": title, "cc": country, "l": lang})
    resp.raise_for_status()
    items = resp.json().get("items", [])
    if not items:
        raise ValueError(f"No Steam app found for '{title}'")
    return items[0]["id"], items[0]["name"]


def fetch_reviews(app_id, country, language, per_page, start_date, end_date, max_reviews):
    start_ts = int(pd.to_datetime(start_date).timestamp()) if start_date else None
    end_ts   = int(pd.to_datetime(end_date).timestamp())   if end_date   else None
    reviews, cursor = [], "*"
    headers = {"User-Agent": "Mozilla/5.0"}
    while len(reviews) < max_reviews:
        params = {"json":1, "filter":"recent", "language":language,
                  "purchase_type":"all", "cc":country,
                  "num_per_page":per_page, "cursor":cursor}
        resp = requests.get(f"https://store.steampowered.com/appreviews/{app_id}",
                            params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json(); batch = data.get("reviews", [])
        if not batch:
            break
        for r in batch:
            ts = r.get("timestamp_created", 0)
            if start_ts and ts < start_ts:
                return reviews
            if end_ts and ts > end_ts:
                continue
            r["country"] = country
            reviews.append(r)
            if len(reviews) >= max_reviews:
                break
        cursor = data.get("cursor", cursor)
        time.sleep(0.2)
    return reviews


def get_store_details(app_id, country="us", lang="en"):
    url = "https://store.steampowered.com/api/appdetails/"
    resp = requests.get(url, params={"appids":app_id, "cc":country, "l":lang})
    resp.raise_for_status()
    return resp.json().get(str(app_id), {}).get("data", {})


def get_steamspy_appdetails(app_id):
    url = "https://steamspy.com/api.php"
    resp = requests.get(url, params={"request":"appdetails", "appid":app_id})
    resp.raise_for_status()
    try:
        return resp.json()
    except ValueError:
        return {}


def get_player_summaries(steam_ids, key):
    """Fetch summary info (incl. visibility state) for up to 50 SteamIDs at a time"""
    url = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"
    summaries = []
    # debug: show API key being used
    print(f"[DEBUG] Using Steam Key for GetPlayerSummaries: {key}")
    # batch in sizes of 50
    for batch in [steam_ids[i:i+50] for i in range(0, len(steam_ids), 50)]:
        print(f"[DEBUG] Requesting summaries for batch: {batch[:5]}... total {len(batch)} IDs")
        params = {"key": key, "steamids": ",".join(batch)}
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        summaries.extend(resp.json().get("response", {}).get("players", []))
        time.sleep(1)
    return summaries

def get_owned_games(steamid, key):
    url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
    resp = requests.get(url, params={"key":key, "steamid":steamid,
                                      "include_appinfo":0, "include_played_free_games":1})
    resp.raise_for_status()
    return resp.json().get("response", {}).get("games", [])

# ─── MAIN ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app_id, game_name = find_app_id(GAME_TITLE)
    print(f"Found '{game_name}' (AppID {app_id})")

    # 1) Extract and save reviews
    all_reviews = []
    for cc in COUNTRY_CODES:
        all_reviews.extend(fetch_reviews(app_id, cc, LANGUAGE, NUM_PER_PAGE,
                                         START_DATE, END_DATE, MAX_REVIEWS))
    df_reviews = pd.json_normalize(all_reviews, sep="_")
    # add run date
    df_reviews["run_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    reviews_file = f"{game_name.replace(' ', '_')}_reviews_{YEAR}.xlsx"
    df_reviews.to_excel(reviews_file, index=False)

    # 2) Fetch KPIs from store and SteamSpy
    store_data = get_store_details(app_id)
    spy_data   = get_steamspy_appdetails(app_id)
    record = {
        "app_id": app_id,
        "name": game_name,
        "developer": ", ".join(store_data.get("developers", [])),
        "publisher": ", ".join(store_data.get("publishers", [])),
        "owners": spy_data.get("owners"),
        "average_forever": spy_data.get("average_forever"),
        "average_2weeks": spy_data.get("average_2weeks"),
        "median_forever": spy_data.get("median_forever"),
        "median_2weeks": spy_data.get("median_2weeks"),
        "ccu": spy_data.get("ccu"),
        "price": store_data.get("price_overview", {}).get("final"),
        "initialprice": store_data.get("price_overview", {}).get("initial"),
        "discount": store_data.get("price_overview", {}).get("discount_percent"),
        "languages": store_data.get("supported_languages"),
        "genres": [g.get("description") for g in store_data.get("genres", [])]
    }
    df_kpis = pd.DataFrame([record])
    # add run date
    df_kpis["run_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 3) Compute play-based similars
    # collect reviewer IDs
    reviewer_ids = [r["author"]["steamid"] for r in all_reviews]
    # debug: show STEAM_KEY and sample of reviewer_ids        print(f"[DEBUG] Loaded STEAM_KEY: {STEAM_KEY}")
