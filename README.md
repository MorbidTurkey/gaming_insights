# gaming_insights
Find the aslo played data of gamers and other game kpis

---

## Usage Guide

### 1. Collecting Other Owned Games Data (`other_owned_games.py`)
See `README_other_owned_games.md` for full details. In summary:
- Edit the `GAME_NAMES` list in `other_owned_games.py` to specify the games you want to analyze.
- Run:
  ```powershell
  python other_owned_games.py
  ```
- Output Excel files will be saved in the `game_data/` folder, each with sheets for user-owned games and KPIs.

### 2. Merging Game Data (`merge_game_data.py`)
- After collecting data for multiple games, run:
  ```powershell
  python merge_game_data.py
  ```
- This script merges all `*_analysis.xlsx` files in `game_data/` into a single `merged_game_data.xlsx` file with two sheets:
  - `All KPIs`: KPIs for each base game
  - `Top Other Games`: Top other games owned/played by users for each base game

### 3. Interactive Dashboard (`dash_app.py`)
- Launch the dashboard to explore the merged data visually:
  ```powershell
  python dash_app.py
  ```
- The dashboard allows you to select a game, view KPIs, and see which other games are most commonly owned/played by its audience.

### 4. Testing Steam User IDs (`id_check.py`)
- Use this script to test if a Steam user ID is valid and to export their owned games:
  ```powershell
  python id_check.py <steam_id> --output my_games.xlsx
  ```
- Requires a valid `STEAM_API_KEY` in your `.env` file.

### 5. Testing Steam API Key (`key_check.py`)
- Use this script to quickly check if your Steam API key is valid:
  ```powershell
  python key_check.py
  ```
- Prints the HTTP status and a sample response from the Steam API.

---

## Requirements
- Python 3.7+
- `requests`, `pandas`, `python-dotenv`, `dash`, `dash-bootstrap-components`, `plotly`, and related dependencies
- Steam Web API key in a `.env` file:
  ```
  STEAM_API_KEY=your_steam_api_key_here
  ```

## Folder Structure
- `game_data/`: Contains per-game Excel analysis files
- `merged_game_data.xlsx`: Merged summary for dashboard
- `dash_app.py`: Interactive dashboard
- `other_owned_games.py`: Collects user/game data
- `merge_game_data.py`: Merges per-game data
- `id_check.py`: Test user IDs and export owned games
- `key_check.py`: Test Steam API key validity

For more details on each script, see comments at the top of each file and `README_other_owned_games.md`.
