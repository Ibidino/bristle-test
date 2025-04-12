import requests
import json
import time
from datetime import datetime, timedelta, timezone

BRISTLEBACK_HERO_ID = 99
BASE_URL = "https://api.opendota.com/api"

def get_item_mapping():
    print("Fetching item data...")
    response = requests.get(f"{BASE_URL}/constants/items")
    response.raise_for_status()
    items_data = response.json()
    item_id_map = {}
    for name, item in items_data.items():
        if 'id' in item:
            item_id_map[item['id']] = name.replace("item_", "").replace("_", " ").title()
    return item_id_map

def is_recent(timestamp, days=14):
    match_date = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return datetime.now(timezone.utc) - match_date < timedelta(days=days)

def fetch_recent_pro_matches(max_matches=500):
    print(f"Fetching up to {max_matches} recent pro matches...")
    matches = []
    url = f"{BASE_URL}/proMatches"
    last_match_id = None

    while len(matches) < max_matches:
        params = {"less_than_match_id": last_match_id} if last_match_id else {}
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if not data:
            break

        for match in data:
            if is_recent(match["start_time"]):
                matches.append(match)
            else:
                return matches  # Stop when matches are older than 14 days

        last_match_id = data[-1]["match_id"]
        time.sleep(1)

    return matches

def get_match_details(match_id):
    response = requests.get(f"{BASE_URL}/matches/{match_id}")
    response.raise_for_status()
    return response.json()

def get_player_name(account_id):
    if not account_id:
        return "Unknown"
    try:
        response = requests.get(f"{BASE_URL}/players/{account_id}")
        response.raise_for_status()
        data = response.json()
        profile = data.get("profile", {})
        return profile.get("name") or profile.get("personaname") or "Unknown"
    except:
        return "Unknown"

def get_bristleback_games(limit=5):
    item_id_map = get_item_mapping()
    all_matches = fetch_recent_pro_matches(max_matches=1000)
    bristleback_games = []
    count = 0

    for match in all_matches:
        if count >= limit:
            break

        try:
            match_data = get_match_details(match["match_id"])
        except Exception as e:
            print(f"Skipping match {match['match_id']} due to error: {e}")
            continue

        for player in match_data.get("players", []):
            if player["hero_id"] == BRISTLEBACK_HERO_ID:
                items = [item_id_map.get(player.get(f"item_{i}", 0), "Unknown") for i in range(6)]
                backpack = [item_id_map.get(player.get(f"backpack_{i}", 0), "Unknown") for i in range(3)]
                neutral_item = item_id_map.get(player.get("item_neutral", 0), "Unknown")
                win = player.get("win", 0) == 1

                kda = {
                    "kills": player.get("kills", 0),
                    "deaths": player.get("deaths", 0),
                    "assists": player.get("assists", 0)
                }

                account_id = player.get("account_id")
                player_name = get_player_name(account_id)
                time.sleep(0.5)  # avoid hitting OpenDota's rate limit

                game_info = {
                    "match_id": match["match_id"],
                    "match_date": datetime.fromtimestamp(match["start_time"], tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                    "radiant_team": match.get("radiant_name", "Radiant"),
                    "dire_team": match.get("dire_name", "Dire"),
                    "player_name": player_name,
                    "items": items,
                    "backpack": backpack,
                    "neutral_item": neutral_item,
                    "win": win,
                    "kda": kda
                }

                bristleback_games.append(game_info)
                print(f"✓ Match {match['match_id']} | {player_name} | Win: {win} | KDA: {kda['kills']}/{kda['deaths']}/{kda['assists']}")
                count += 1

                # Auto-save after each match
                with open("bristleback_matches.json", "w") as f:
                    json.dump(bristleback_games, f, indent=2)

                break

        time.sleep(1)

    return bristleback_games

if __name__ == "__main__":
    print("Running Bristleback match scraper...")
    games = get_bristleback_games()
    print(f"\n✔ Done! {len(games)} Bristleback matches saved to bristleback_matches.json")
