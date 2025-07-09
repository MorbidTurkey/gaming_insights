import pandas as pd
import json
import os

MERGED_FILE = "merged_game_data.xlsx"
TAGS_GENRES_FILE = "game_tags_and_genres.json"

df_kpis_all = pd.DataFrame()
df_other_all = pd.DataFrame()
TAGS_GENRES_DICT = {}

if os.path.exists(MERGED_FILE):
    try:
        df_kpis_all = pd.read_excel(MERGED_FILE, sheet_name='All KPIs')
    except Exception as e:
        print(f"Error loading All KPIs: {e}")
    try:
        df_other_all = pd.read_excel(MERGED_FILE, sheet_name='Top Other Games')
    except Exception as e:
        print(f"Error loading Top Other Games: {e}")
if os.path.exists(TAGS_GENRES_FILE):
    try:
        with open(TAGS_GENRES_FILE, "r", encoding="utf-8") as f:
            TAGS_GENRES_DICT = json.load(f)
    except Exception as e:
        print(f"Error loading tags/genres: {e}")
