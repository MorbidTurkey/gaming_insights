import os
import time
from datetime import datetime
from dotenv import load_dotenv, find_dotenv
import requests
import pandas as pd

# === Configuration Parameters ===
GAME_NAMES = ["Slay the Spire"]  # List of target game names to sample
START_DATE_STR = "2025-01-01"
END_DATE_STR = "2025-05-20"
LANGUAGE = "english"
MARKET = "us"
SAMPLE_SIZE = 1000
OUTPUT_FOLDER = "game_data"

# === Helper Functions ===

def load_app_list():
    """Fetch full Steam AppList"""
    resp = requests.get("https://api.steampowered.com/ISteamApps/GetAppList/v2/")
    resp.raise_for_status()
    apps = resp.json().get('applist', {}).get('apps', [])
    return {app['name']: app['appid'] for app in apps}


def find_appid(apps_map, name):
    """Lookup AppID by name"""
    if name in apps_map:
        return apps_map[name]
    for n, aid in apps_map.items():
        if name.lower() in n.lower():
            return aid
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

    apps_map = load_app_list()
    start_date = datetime.strptime(START_DATE_STR, '%Y-%m-%d')
    end_date   = datetime.strptime(END_DATE_STR, '%Y-%m-%d')

    for game_name in GAME_NAMES:
        print(f"\nProcessing '{game_name}'...")
        appid = find_appid(apps_map, game_name)
        if not appid:
            print(f"AppID not found for '{game_name}', skipping.")
            continue

        # Fetch KPI for this game
        print("Fetching KPIs...")
        kpis = fetch_kpis_spy(appid)

        # Sample reviews and public users
        reviews = get_reviews(appid, MARKET, LANGUAGE, 100,
                              start_date, end_date, SAMPLE_SIZE)
        steamids = []
        for rev in reviews:
            sid = rev.get('author', {}).get('steamid')
            if sid and sid not in steamids and is_profile_public(api_key, sid):
                steamids.append(sid)
            if len(steamids) >= SAMPLE_SIZE:
                break
        print(f"Found {len(steamids)} public users")

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
        for sid, glist in user_games.items():
            row = {'steamid': sid}
            for g in glist:
                name = g.get('name')
                hrs = g.get('playtime_forever', 0) / 60
                row[name] = hrs
            rows.append(row)
        df_games = pd.DataFrame(rows).fillna(0)

        # Build KPI DataFrame (one row)
        kpis['sample_size'] = len(steamids)
        df_kpi = pd.DataFrame([kpis])

        # Export to Excel in game_data folder with two sheets
        outfile = os.path.join(OUTPUT_FOLDER, f"{game_name.replace(' ', '_')}_analysis.xlsx")
        with pd.ExcelWriter(outfile) as writer:
            df_games.to_excel(writer, sheet_name='Other Games', index=False)
            df_kpi.to_excel(writer, sheet_name='KPIs', index=False)
        print(f"Exported other games and KPIs to {outfile}")

if __name__ == '__main__':
    main()
