import os, requests
from dotenv import load_dotenv

load_dotenv()
key    = os.getenv("STEAM_API_KEY")
steamid = "76561198012345678"

url = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"
resp = requests.get(url, params={"key": key, "steamids": steamid})
print(resp.status_code)
print(resp.json())
