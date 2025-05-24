#!/usr/bin/env python3
import os
import time
import requests
import pandas as pd
from datetime import datetime
from collections import Counter
from dotenv import load_dotenv

# ─── LOAD ENV VARS ───────────────────────────────────────────────────────────────
load_dotenv()
STEAM_KEY = os.getenv("STEAM_API_KEY")
if not STEAM_KEY:
    raise RuntimeError("STEAM_API_KEY not set in environment")

# ─── CONFIG ─────────────────────────────────────────────────────────────────────
GAME_TITLE       = "Slay the Spire"
COUNTRY_CODES    = ["us"]             # list of region codes
LANGUAGE         = "all"            # review language filter
NUM_PER_PAGE     = 100               # reviews per request
START_DATE       = "2025-01-01"     # inclusive, YYYY-MM-DD
END_DATE         = "2025-12-05"     # inclusive, YYYY-MM-DD
MAX_REVIEWS      = 1000              # max reviews to sample
YEAR             = datetime.now().year

# Play-based similars settings
TOP_N_PLAY_SIM   = 10                # top N play-based similars
SAMPLE_SIZE_PLAY = 1000              # sample size for play-based similars

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
    end_ts   = int(pd.to_datetime(end_date).timestamp()) if end_date else None
    reviews, cursor = [], "*"
    headers = {"User-Agent": "Mozilla/5.0"}
    while len(reviews) < max_reviews:
        params = {
            "json": 1,
            "filter": "recent",
            "language": language,
            "purchase_type": "all",
            "cc": country,
            "num_per_page": per_page,
            "cursor": cursor
        }
        resp = requests.get(
            f"https://store.steampowered.com/appreviews/{app_id}",
            params=params, headers=headers
        )
        resp.raise_for_status()
        data = resp.json()
        batch = data.get("reviews", [])
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
    resp = requests.get(url, params={"appids": app_id, "cc": country, "l": lang})
    resp.raise_for_status()
    return resp.json().get(str(app_id), {}).get("data", {})


def get_steamspy_appdetails(app_id):
    url = "https://steamspy.com/api.php"
    resp = requests.get(url, params={"request": "appdetails", "appid": app_id})
    resp.raise_for_status()
    try:
        return resp.json()
    except ValueError:
        return {}


def get_player_summaries(steam_ids, key):
    """Batch-fetch public profile summaries (max 100 per request)"""
    url = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"
    summaries = []
    for i in range(0, len(steam_ids), 100):
        batch = steam_ids[i:i+100]
        params = {"key": key, "steamids": ",".join(batch)}
        resp = requests.get(url, params=params)
        if resp.status_code == 200:
            data = resp.json().get("response", {}).get("players", [])
            summaries.extend(data)
        time.sleep(1)
    return summaries


def get_owned_games(steamid, key):
    """Fetch owned games list; returns empty on any error"""
    url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
    params = {"key": key, "steamid": steamid,
              "include_appinfo": 0, "include_played_free_games": 1}
    resp = requests.get(url, params=params)
    if resp.status_code == 200:
        return resp.json().get("response", {}).get("games", [])
    return []

# ─── MAIN ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # 1) Resolve AppID
    app_id, game_name = find_app_id(GAME_TITLE)
    print(f"Found '{game_name}' (AppID {app_id})")

    # 2) Extract Reviews
    all_reviews = []
    for cc in COUNTRY_CODES:
        all_reviews.extend(
            fetch_reviews(app_id, cc, LANGUAGE, NUM_PER_PAGE,
                          START_DATE, END_DATE, MAX_REVIEWS)
        )
    df_reviews = pd.json_normalize(all_reviews, sep="_")
    df_reviews["run_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    reviews_file = f"{game_name.replace(' ', '_')}_reviews_{YEAR}.xlsx"
    df_reviews.to_excel(reviews_file, index=False)

    # 3) Fetch KPIs
    store_data = get_store_details(app_id)
    spy_data = get_steamspy_appdetails(app_id)
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
        "genres": [g.get("description") for g in store_data.get("genres", [])],
        "run_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    df_kpis = pd.DataFrame([record])

    # 4) Compute PlaySimilars
    reviewer_ids = [r.get("author", {}).get("steamid") for r in all_reviews]
    reviewer_ids = [rid for rid in reviewer_ids if rid]
    sample_ids = reviewer_ids[:SAMPLE_SIZE_PLAY]
    play_counter = Counter()
    for sid in sample_ids:
        for g in get_owned_games(sid, STEAM_KEY):
            app = g.get("appid")
            if app:
                play_counter[app] += 1
        time.sleep(0.2)
    if app_id in play_counter:
        del play_counter[app_id]
    df_play = pd.DataFrame(
        play_counter.most_common(TOP_N_PLAY_SIM),
        columns=["appid", "count"]
    )
    df_play["run_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 5) Save Summary
    summary_file = f"{game_name.replace(' ', '_')}_summary_{YEAR}.xlsx"
    with pd.ExcelWriter(summary_file) as writer:
        df_kpis.to_excel(writer, sheet_name="KPIs", index=False)
        df_play.to_excel(writer, sheet_name="PlaySimilars", index=False)

    print(f"Saved reviews to {reviews_file} and summary to {summary_file}")
