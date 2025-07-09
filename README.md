# Steam Game Analytics Dashboard

An interactive dashboard for exploring Steam game KPIs, player overlap, and review sentiment.

---

## Features

- Game View: Explore KPIs and player overlap for each game.
- Reviews View: Analyze review sentiment over time and see recent reviews.
- Theme-aware UI with light/dark mode.
- DataTables and dropdowns styled for accessibility.
- Navigation between views with persistent game selection.

---

## Quick Start

1. **Install requirements:**
   ```powershell
   pip install -r requirements.txt
   ```

2. **Prepare your data:**
   - Place your processed data in the `game_data/`, `game_data_cleaned/`, and `reviews_data/` folders.
   - Ensure `merged_game_data.xlsx` and `game_tags_and_genres.json` are present in the project root.

3. **Run the dashboard:**
   ```powershell
   python dash_app.py
   ```

4. **(Optional) Data refresh:**
   - Use your data collection scripts (e.g., `fetch_steamspy_full_db.py`, `fetch_reviews_text.py`) to update your data files as needed.

---

## Deployment

- You can deploy this app for free using [Render.com](https://render.com) or similar services.
- See the deployment section above for step-by-step instructions.

---

## Requirements

- Python 3.7+
- See `requirements.txt` for all dependencies.

---

## Folder Structure

- `dash_app.py` — Main dashboard app
- `pages/` — Dashboard page layouts and callbacks
- `shared_data.py` — Centralized data loading
- `game_data/`, `game_data_cleaned/`, `reviews_data/` — Data folders
- `merged_game_data.xlsx`, `game_tags_and_genres.json` — Main data files

---

## Data Refresh

To update your dashboard with new data:
- Run your data collection scripts to fetch and process new data.
- Overwrite the files in `game_data/`, `reviews_data/`, and update `merged_game_data.xlsx` and `game_tags_and_genres.json`.
- Restart the dashboard.

---

## Steam API Key

Some scripts require a Steam Web API key in a `.env` file:
```
STEAM_API_KEY=your_steam_api_key_here
```
