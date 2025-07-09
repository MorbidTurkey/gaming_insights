import os
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv, find_dotenv
import requests
import pandas as pd
import json

# === Configuration Parameters ===
GAME_NAMES = [
    325610,
    1142710,    
]
# You can mix names and numeric appids here, e.g.:
# "The Warlock of Firetop Mountain", 282070, ...

LANGUAGE = "english"
SAMPLE_SIZE = 1000  # for public profile sampling
REVIEWS_PER_GAME = 1000  # for review text collection
OUTPUT_FOLDER = "game_data"
REVIEWS_FOLDER = "reviews_data"
RATE_LIMIT_SECONDS = 1.2
MARKET = "all"  # Set to 'all' for now, can be changed later

os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(REVIEWS_FOLDER, exist_ok=True)

def load_app_list():
    resp = requests.get("https://api.steampowered.com/ISteamApps/GetAppList/v2/")
    resp.raise_for_status()
    apps = resp.json().get('applist', {}).get('apps', [])
    return {app['name']: app['appid'] for app in apps}

def find_appid(apps_map, name):
    if name.isdigit():
        return int(name)
    if name in apps_map:
        return apps_map[name]
    norm = ''.join(ch.lower() for ch in name if ch.isalnum())
    for n, aid in apps_map.items():
        norm_n = ''.join(ch.lower() for ch in n if ch.isalnum())
        if norm in norm_n:
            return aid
    print(f"'{name}' wasn't found. Try removing punctuation or inputting the AppID directly.")
    return None

def get_reviews(app_id, market, language, per_page, start_date, end_date, max_reviews):
    start_ts = int(start_date.timestamp())
    end_ts = int(end_date.timestamp())
    reviews, cursor = [], "*"
    headers = {"User-Agent": "Mozilla/5.0"}
    max_retries = 5
    for attempt in range(max_retries):
        try:
            resp = requests.get(
                f"https://store.steampowered.com/appreviews/{app_id}",
                params={
                    "json": 1,
                    "filter": "all",
                    "language": language,
                    "purchase_type": "all",
                    "cc": market,
                    "num_per_page": per_page,
                    "cursor": cursor
                }, headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
            batch = data.get("reviews", [])
            if not batch:
                break
            for r in batch:
                ts = r.get('timestamp_created', 0)
                if ts < start_ts:
                    return reviews
                if ts <= end_ts:
                    reviews.append(r)
                    if len(reviews) >= max_reviews:
                        break
            cursor = data.get('cursor', cursor)
            time.sleep(0.2)
        except Exception as e:
            print(f"Error fetching reviews for {app_id}: {e}")
            time.sleep(5)
            continue
    return reviews

def fetch_reviews_text(appid, max_reviews, out_folder, game_name=None):
    display_name = f"appid {appid}" if not game_name else f"appid {appid} ('{game_name}')"
    print(f"Fetching up to {max_reviews} reviews for {display_name}...")
    reviews = []
    cursor = "*"
    total_fetched = 0
    while total_fetched < max_reviews:
        params = {
            "json": 1,
            "filter": "all",
            "language": "all",
            "purchase_type": "all",
            "num_per_page": min(100, max_reviews - total_fetched),
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
            print(f"Fetched {total_fetched} reviews so far for {display_name}...")
            if len(batch) == 0:
                break
        except Exception as e:
            print(f"Error fetching reviews for {display_name}: {e}")
            break
        time.sleep(RATE_LIMIT_SECONDS)
    if reviews:
        df = pd.DataFrame(reviews)
        outpath = os.path.join(out_folder, f"reviews_{appid}.parquet")
        df.to_parquet(outpath, index=False)
        print(f"Saved {len(reviews)} reviews for {display_name} to {outpath}")
    else:
        print(f"No reviews found for {display_name}")

def is_profile_public(api_key, steam_id):
    resp = requests.get(
        "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/",
        params={"key": api_key, "steamids": steam_id}
    )
    if resp.ok:
        players = resp.json().get('response', {}).get('players', [])
        return bool(players and players[0].get('communityvisibilitystate') == 3)
    return False

def get_owned_games(api_key, steam_id):
    resp = requests.get(
        "https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/",
        params={
            "key": api_key,
            "steamid": steam_id,
            "include_appinfo": 1,
            "include_played_free_games": 1,
            "format": "json"
        }
    )
    if resp.status_code in (401, 403):
        return []
    resp.raise_for_status()
    return resp.json().get('response', {}).get('games', [])

def fetch_kpis_spy(appid):
    url = f"https://steamspy.com/api.php?request=appdetails&appid={appid}"
    resp = requests.get(url)
    if not resp.ok:
        return {}
    data = resp.json()
    keys = ['appid', 'name', 'developer', 'publisher', 'score_rank',
            'owners', 'average_forever', 'average_2weeks',
            'median_forever', 'median_2weeks', 'ccu',
            'price', 'initialprice', 'discount']
    return {k: data.get(k) for k in keys}

def main():
    load_dotenv(find_dotenv(), override=True)
    api_key = os.getenv('STEAM_API_KEY', '').strip()
    if not api_key:
        raise RuntimeError('STEAM_API_KEY missing in .env')
    apps_map = load_app_list()
    now = datetime.now()
    initial_months = 6
    max_attempts = 5
    for game_name in GAME_NAMES:
        print(f"Processing '{game_name}'...")
        if str(game_name).isdigit():
            appid = int(game_name)
            kpis = fetch_kpis_spy(appid)
            game_display_name = kpis.get('name')
            if not game_display_name:
                appid_to_name = {v: k for k, v in apps_map.items()}
                game_display_name = appid_to_name.get(appid, str(game_name))
        else:
            appid = find_appid(apps_map, game_name)
            kpis = fetch_kpis_spy(appid) if appid else {}
            game_display_name = kpis.get('name', game_name)
        if not appid:
            print(f"AppID not found for '{game_name}', skipping.")
            continue
        # --- Fetch review text ---
        fetch_reviews_text(appid, REVIEWS_PER_GAME, REVIEWS_FOLDER, game_display_name)
        # --- Fetch other owned games sample (as before) ---
        print(f"Fetching KPIs for '{game_display_name}'...")
        attempts = 0
        steamids_set = set()
        months_back = initial_months
        language_priority = [LANGUAGE, "all"]
        lang_idx = 0
        while attempts < max_attempts and len(steamids_set) < SAMPLE_SIZE:
            end_date = now
            start_date = now - timedelta(days=months_back * 30)
            current_language = language_priority[lang_idx]
            print(f"Trying reviews from {start_date.date()} to {end_date.date()} (attempt {attempts+1}, language: {current_language})")
            reviews = get_reviews(appid, MARKET, current_language, 100, start_date, end_date, min(SAMPLE_SIZE * 2, 2000))
            print(f"Fetched {len(reviews)} reviews for '{game_name}' in date range (language: {current_language}).")
            candidate_steamids = []
            seen = set()
            for rev in reviews:
                sid = rev.get('author', {}).get('steamid')
                if sid and sid not in seen and sid not in steamids_set:
                    candidate_steamids.append(sid)
                    seen.add(sid)
            for sid in candidate_steamids:
                if is_profile_public(api_key, sid):
                    steamids_set.add(sid)
                if len(steamids_set) >= SAMPLE_SIZE:
                    break
            print(f"Accumulated {len(steamids_set)} unique public users (attempt {attempts+1}, language: {current_language})")
            if len(steamids_set) >= min(500, SAMPLE_SIZE):
                break
            attempts += 1
            months_back += initial_months
            # If we've tried all months and not enough, try next language priority
            if attempts >= max_attempts and lang_idx + 1 < len(language_priority) and len(steamids_set) < SAMPLE_SIZE:
                print(f"Not enough public profiles found with language '{current_language}'. Expanding to next language priority...")
                lang_idx += 1
                attempts = 0
                months_back = initial_months
        steamids = list(steamids_set)[:SAMPLE_SIZE]
        if not steamids:
            print(f"No public users found for '{game_display_name}', skipping export.")
            continue
        needed = set()
        user_games = {}
        for sid in steamids:
            glist = get_owned_games(api_key, sid)
            user_games[sid] = glist
            for g in glist:
                needed.add(g.get('name'))
        print(f"Total unique 'other games' encountered: {len(needed)}")
        rows = []
        for sid in steamids:
            glist = user_games[sid]
            row = {'steamid': sid}
            for g in glist:
                name = g.get('name')
                hrs = g.get('playtime_hours', g.get('playtime_forever', 0) / 60)
                row[name] = hrs
            rows.append(row)
        if not rows or len(needed) == 0:
            print(f"No 'other games' data for '{game_display_name}', skipping export.")
            continue
        df_games = pd.DataFrame(rows).fillna(0)
        nonzero_cols = ['steamid'] + [col for col in df_games.columns if col != 'steamid' and df_games[col].sum() > 0]
        if not set(nonzero_cols).issubset(set(df_games.columns)):
            print(f"No nonzero columns for '{game_display_name}', skipping export.")
            continue
        df_games = df_games[nonzero_cols]
        if len(df_games.columns) > 1001:
            playtime_sums = df_games.drop(columns=['steamid']).sum().sort_values(ascending=False)
            top_games = list(playtime_sums.head(1000).index)
            keep_cols = ['steamid'] + top_games
            df_games = df_games[keep_cols]
        kpis['sample_size'] = len(steamids)
        df_kpi = pd.DataFrame([kpis])
        # Robust filename sanitization
        import re
        safe_name = re.sub(r'[^A-Za-z0-9_]+', '_', str(game_display_name)).strip('_')
        if not safe_name:
            print(f"Invalid or empty game_display_name for appid {appid}, skipping export.")
            continue
        outfile = os.path.join(OUTPUT_FOLDER, f"{safe_name}_analysis.parquet")
        try:
            with pd.ExcelWriter(outfile.replace('.parquet', '.xlsx')) as writer:
                df_games.to_excel(writer, sheet_name='Other Games', index=False)
                df_kpi.to_excel(writer, sheet_name='KPIs', index=False)
            df_games.to_parquet(outfile, index=False)
            print(f"Exported other games and KPIs to {outfile}")
        except Exception as e:
            print(f"Failed to export data for '{game_display_name}' (filename: {outfile}): {e}")

if __name__ == '__main__':
    main()
