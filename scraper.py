import urllib.request
import json
import csv
import io
import os

API_KEY = "0fcdf764-1fd7-46b9-9d4c-6698264d48ee"
BASE_URL = "https://api.cricapi.com/v1"
CACHE_DIR = "scorecard_cache"

def fetch_cricapi_scorecard(match_api_id):
    """Fetch and parse scorecard from CricAPI with local caching."""

    # Check cache first — never hit API twice for same match
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(CACHE_DIR, f"{match_api_id}.json")

    if os.path.exists(cache_file):
        print(f"📦 Using cached scorecard for {match_api_id}")
        with open(cache_file, "r") as f:
            match_data = json.load(f)
        return parse_cricapi_scorecard(match_data)

    # Fetch from API
    try:
        url = f"{BASE_URL}/match_scorecard?apikey={API_KEY}&id={match_api_id}"
        response = urllib.request.urlopen(url)
        data = json.loads(response.read())
    except Exception as e:
        return None, f"Failed to fetch CricAPI: {e}"

    if data.get("status") != "success":
        reason = data.get("reason", "Unknown error")
        return None, f"CricAPI error: {data.get('status')} - {reason}"

    match_data = data.get("data", {})
    if not match_data.get("scorecard"):
        return None, "No scorecard data available yet. Match may not be complete."

    # Save to cache
    with open(cache_file, "w") as f:
        json.dump(match_data, f)
    print(f"✅ Scorecard fetched and cached for {match_api_id}")

    return parse_cricapi_scorecard(match_data)

def parse_cricapi_scorecard(match_data):
    """Parse CricAPI scorecard JSON into CSV format."""
    try:
        winning_team = match_data.get("matchWinner", "")
        scorecard = match_data.get("scorecard", [])
        teams = match_data.get("teams", [])

        # Extract MOTM from match data
        motm_name = ""
        match_name = match_data.get("name", "")
        # CricAPI sometimes includes MOTM in different fields
        if match_data.get("player_of_match"):
            motm_name = match_data["player_of_match"].lower().strip()
        elif match_data.get("playerOfMatch"):
            motm_name = match_data["playerOfMatch"].lower().strip()
        
        players = {}

        for innings in scorecard:
            # Determine batting and bowling teams
            inning_name = innings.get("inning", "")
            batting_team = ""
            for team in teams:
                if team in inning_name:
                    batting_team = team
                    break
            bowling_team = next(
                (t for t in teams if t != batting_team), "")

            is_batting_winner = batting_team == winning_team
            is_bowling_winner = bowling_team == winning_team

            # ── Batting ──────────────────────────────
            for batter in innings.get("batting", []):
                name = batter.get("batsman", {}).get("name", "").strip()
                if not name:
                    continue

                if name not in players:
                    players[name] = empty_stats()

                p = players[name]
                p["did_play"] = 1
                p["team"] = batting_team
                p["runs"] += int(batter.get("r", 0) or 0)
                p["balls_faced"] += int(batter.get("b", 0) or 0)
                p["fours"] += int(batter.get("4s", 0) or 0)
                p["sixes"] += int(batter.get("6s", 0) or 0)
                if is_batting_winner:
                    p["is_winner"] = 1

                # Fielding from dismissals
                dismissal = batter.get("dismissal", "").lower()
                catcher = batter.get("catcher", {})
                if catcher:
                    fname = catcher.get("name", "").strip()
                    if fname:
                        if fname not in players:
                            players[fname] = empty_stats()
                        players[fname]["did_play"] = 1
                        if "catch" in dismissal:
                            players[fname]["catches"] += 1
                        elif "stump" in dismissal:
                            players[fname]["stumpings"] += 1
                        elif "run out" in dismissal:
                            players[fname]["run_outs"] += 1

            # ── Bowling ──────────────────────────────
            for bowler in innings.get("bowling", []):
                name = bowler.get("bowler", {}).get("name", "").strip()
                if not name:
                    continue

                if name not in players:
                    players[name] = empty_stats()

                p = players[name]
                p["did_play"] = 1
                p["team"] = bowling_team
                if is_bowling_winner:
                    p["is_winner"] = 1

                p["wickets"] += int(bowler.get("w", 0) or 0)
                p["maidens"] += int(bowler.get("m", 0) or 0)
                p["runs_conceded"] += int(bowler.get("r", 0) or 0)
                p["wides"] += int(bowler.get("wd", 0) or 0)
                p["no_balls"] += int(bowler.get("nb", 0) or 0)

                # Parse overs e.g. "4.0" or "3.2"
                overs_str = str(bowler.get("o", "0") or "0")
                try:
                    if "." in overs_str:
                        whole, balls = overs_str.split(".")
                        overs = int(whole) + int(balls) / 6
                    else:
                        overs = float(overs_str)
                    p["overs_bowled"] += round(overs, 2)
                except:
                    pass

        # Set MOTM
        if motm_name:
            for name in players:
                if motm_name in name.lower() or name.lower() in motm_name:
                    players[name]["is_motm"] = 1
                    break

        # Generate CSV
        output = io.StringIO()
        fieldnames = [
            "player_name", "runs", "balls_faced", "fours", "sixes",
            "wickets", "overs_bowled", "runs_conceded", "maidens",
            "catches", "stumpings", "run_outs", "is_motm",
            "is_winner", "did_play"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for name, stats in players.items():
            if stats["did_play"]:
                writer.writerow({
                    "player_name": name,
                    "runs": stats["runs"],
                    "balls_faced": stats["balls_faced"],
                    "fours": stats["fours"],
                    "sixes": stats["sixes"],
                    "wickets": stats["wickets"],
                    "overs_bowled": round(stats["overs_bowled"], 2),
                    "runs_conceded": stats["runs_conceded"],
                    "maidens": stats["maidens"],
                    "catches": stats["catches"],
                    "stumpings": stats["stumpings"],
                    "run_outs": stats["run_outs"],
                    "is_motm": stats["is_motm"],
                    "is_winner": stats["is_winner"],
                    "did_play": stats["did_play"],
                })

        return output.getvalue(), None

    except Exception as e:
        return None, f"Error parsing scorecard: {e}"

def empty_stats():
    return {
        "runs": 0, "balls_faced": 0, "fours": 0, "sixes": 0,
        "wickets": 0, "overs_bowled": 0.0, "runs_conceded": 0,
        "maidens": 0, "wides": 0, "no_balls": 0,
        "catches": 0, "stumpings": 0, "run_outs": 0,
        "is_motm": 0, "is_winner": 0, "did_play": 0, "team": ""
    }