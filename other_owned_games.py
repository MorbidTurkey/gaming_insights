import os
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv, find_dotenv
import requests
import pandas as pd
import difflib

# === Configuration Parameters ===
GAME_NAMES = ["Thea The Awakening"]  # List of target game names to sample
# Start with last 6 months
LANGUAGE = "english"
MARKET = "us"
SAMPLE_SIZE = 1000
OUTPUT_FOLDER = "game_data"


def load_app_list():
    """Fetch full Steam AppList"""
    resp = requests.get("https://api.steampowered.com/ISteamApps/GetAppList/v2/")
    resp.raise_for_status()
    apps = resp.json().get('applist', {}).get('apps', [])
    return {app['name']: app['appid'] for app in apps}


def find_appid(apps_map, name):
    """Lookup AppID by exact name, substring match, or numeric ID input"""
    # If user provided a numeric AppID, use it directly
    if name.isdigit():
        return int(name)
    # Exact match
    if name in apps_map:
        return apps_map[name]
    # Substring match (ignoring punctuation/spaces)
    norm = ''.join(ch.lower() for ch in name if ch.isalnum())
    for n, aid in apps_map.items():
        norm_n = ''.join(ch.lower() for ch in n if ch.isalnum())
        if norm in norm_n:
            return aid
    # Not found
    print(f"'{name}' wasn't found. Try removing punctuation or inputting the AppID directly.")
    return None


def get_reviews(app_id, country, language, per_page, start_date, end_date, max_reviews):
    """Paginate Steam Store reviews"""
    start_ts = int(start_date.timestamp())
    end_ts = int(end_date.timestamp())
    reviews, cursor = [], "*"
    headers = {"User-Agent": "Mozilla/5.0"}
    while len(reviews) < max_reviews:
        params = {
            "json": 1,
            # fetch all reviews to cover full date range
            "filter": "all",
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
            ts = r.get('timestamp_created', 0)
            if ts < start_ts:
                return reviews
            if ts <= end_ts:
                reviews.append(r)
                if len(reviews) >= max_reviews:
                    break
        cursor = data.get('cursor', cursor)
        time.sleep(0.2)
    return reviews


def is_profile_public(api_key, steam_id):
    """Check profile visibility via GetPlayerSummaries"""
    resp = requests.get(
        "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/",
        params={"key": api_key, "steamids": steam_id}
    )
    if resp.ok:
        players = resp.json().get('response', {}).get('players', [])
        return bool(players and players[0].get('communityvisibilitystate') == 3)
    return False


def get_owned_games(api_key, steam_id):
    """Fetch owned games (name + playtime)"""
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
    """Fetch KPI metrics from SteamSpy for a given appid"""
    url = f"https://steamspy.com/api.php?request=appdetails&appid={appid}"
    resp = requests.get(url)
    if not resp.ok:
        return {}
    data = resp.json()
    # select relevant KPIs
    keys = ['appid', 'name', 'developer', 'publisher', 'score_rank',
            'owners', 'average_forever', 'average_2weeks',
            'median_forever', 'median_2weeks', 'ccu',
            'price', 'initialprice', 'discount']
    return {k: data.get(k) for k in keys}


def main():
    # Load API key
    load_dotenv(find_dotenv(), override=True)
    api_key = os.getenv('STEAM_API_KEY', '').strip()
    if not api_key:
        raise RuntimeError('STEAM_API_KEY missing in .env')

    # Ensure output folder exists
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    now = datetime.now()
    initial_months = 6
    max_attempts = 5
    apps_map = load_app_list()  # Only load once
    for game_name in GAME_NAMES:
        print(f"Processing '{game_name}'...")
        # If game_name is numeric, use as appid directly
        if game_name.isdigit():
            appid = int(game_name)
            kpis = fetch_kpis_spy(appid)
            # Try to get the name from SteamSpy, then from app list, then fallback to input
            game_display_name = kpis.get('name')
            if not game_display_name:
                # Try to get from app list
                appid_to_name = {v: k for k, v in apps_map.items()}
                game_display_name = appid_to_name.get(appid, game_name)
        else:
            appid = find_appid(apps_map, game_name)
            kpis = fetch_kpis_spy(appid) if appid else {}
            game_display_name = kpis.get('name', game_name)
        if not appid:
            print(f"AppID not found for '{game_name}', skipping.")
            continue

        print(f"Fetching KPIs for '{game_display_name}'...")

        # Dynamic date range expansion
        attempts = 0
        steamids_set = set()
        months_back = initial_months
        while attempts < max_attempts and len(steamids_set) < SAMPLE_SIZE:
            end_date = now
            start_date = now - timedelta(days=months_back * 30)
            print(f"Trying reviews from {start_date.date()} to {end_date.date()} (attempt {attempts+1})")
            # Limit reviews fetched per attempt to avoid pulling too much data
            reviews = get_reviews(appid, MARKET, LANGUAGE, 100, start_date, end_date, min(SAMPLE_SIZE * 2, 2000))
            print(f"Fetched {len(reviews)} reviews for '{game_name}' in date range.")
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
            print(f"Accumulated {len(steamids_set)} unique public users (attempt {attempts+1})")
            if len(steamids_set) >= min(500, SAMPLE_SIZE):
                break
            attempts += 1
            months_back += initial_months

        # Only keep up to SAMPLE_SIZE public profiles
        steamids = list(steamids_set)[:SAMPLE_SIZE]
        # Collect unique 'other games'
        needed = set()
        user_games = {}
        for sid in steamids:
            glist = get_owned_games(api_key, sid)
            user_games[sid] = glist
            for g in glist:
                needed.add(g.get('name'))
        print(f"Total unique 'other games' encountered: {len(needed)}")

        # Build DataFrame for other games
        rows = []
        for sid in steamids:
            glist = user_games[sid]
            row = {'steamid': sid}
            for g in glist:
                name = g.get('name')
                hrs = g.get('playtime_hours', g.get('playtime_forever', 0) / 60)
                row[name] = hrs
            rows.append(row)
        df_games = pd.DataFrame(rows).fillna(0)

        # Remove columns where all values are zero (except 'steamid')
        nonzero_cols = ['steamid'] + [col for col in df_games.columns if col != 'steamid' and df_games[col].sum() > 0]
        df_games = df_games[nonzero_cols]

        # Limit columns to top 1000 by total playtime (excluding 'steamid')
        if len(df_games.columns) > 1001:
            playtime_sums = df_games.drop(columns=['steamid']).sum().sort_values(ascending=False)
            top_games = list(playtime_sums.head(1000).index)
            keep_cols = ['steamid'] + top_games
            df_games = df_games[keep_cols]

        # Build KPI DataFrame (one row)
        kpis['sample_size'] = len(steamids)
        df_kpi = pd.DataFrame([kpis])

        # Export to Excel in game_data folder with two sheets
        safe_name = game_display_name.replace(' ', '_').replace('/', '_')
        outfile = os.path.join(OUTPUT_FOLDER, f"{safe_name}_analysis.xlsx")
        with pd.ExcelWriter(outfile) as writer:
            df_games.to_excel(writer, sheet_name='Other Games', index=False)
            df_kpi.to_excel(writer, sheet_name='KPIs', index=False)
        print(f"Exported other games and KPIs to {outfile}")

if __name__ == '__main__':
    main()
