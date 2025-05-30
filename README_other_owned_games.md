# other_owned_games.py

## Overview

`other_owned_games.py` is a Python script that analyzes Steam user data to identify which other games are owned and played by users who reviewed a target game. It leverages the Steam Web API and SteamSpy to collect review data, user profiles, and game KPIs, then exports the results to Excel for further analysis.

## Features
- Fetches recent Steam reviews for a specified game (or games).
- Identifies unique public Steam users who reviewed the game.
- Retrieves the list of games owned and played by these users.
- Aggregates and exports the data to an Excel file, including:
  - A matrix of users vs. other games owned/played (with playtime hours).
  - Key performance indicators (KPIs) for the target game from SteamSpy.
- Handles dynamic date range expansion to reach a target sample size.

## Usage
1. **Set up your environment:**
   - Install dependencies: `pip install -r requirements.txt` (requires `requests`, `pandas`, `python-dotenv`)
   - Create a `.env` file with your Steam API key:
     ```
     STEAM_API_KEY=your_steam_api_key_here
     ```
2. **Configure the script:**
   - Edit the `GAME_NAMES` list at the top of the script to include the Steam game(s) you want to analyze.
   - Adjust other parameters as needed (e.g., `SAMPLE_SIZE`, `LANGUAGE`, `MARKET`).
3. **Run the script:**
   - Execute: `python other_owned_games.py`
   - Output Excel files will be saved in the `game_data/` folder.

## Output
- For each target game, an Excel file is created in `game_data/` with two sheets:
  - `Other Games`: Table of sampled users and their playtime in other games.
  - `KPIs`: Key metrics for the target game from SteamSpy.

## Requirements
- Python 3.7+
- Steam Web API key
- Internet connection

## Notes
- Only public Steam profiles are included in the analysis.
- The script automatically expands the review date range if not enough public users are found.
- The output is limited to the top 1000 other games by total playtime for manageability.

## License
This script is provided for research and personal use. Please respect Steam's API terms of service.
