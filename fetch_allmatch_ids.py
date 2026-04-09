# save as fetch_correct_ids.py
import requests

API_KEY = "0fcdf764-1fd7-46b9-9d4c-6698264d48ee"
SERIES_ID = "87c62aac-bc3c-4738-ab93-19da0690488f"

# Step 1: Get all matches from series_info (has all 70 matches)
print("Fetching series_info...")
r1 = requests.get(
    "https://api.cricapi.com/v1/series_info",
    params={"apikey": API_KEY, "id": SERIES_ID}
)
series_matches = r1.json().get("data", {}).get("matchList", [])
print(f"Series info matches: {len(series_matches)}")

# Step 2: Get recent/current matches (has correct scorecard IDs)
print("Fetching currentMatches...")
current_ipl = {}
for offset in [0, 25, 50]:
    r2 = requests.get(
        "https://api.cricapi.com/v1/currentMatches",
        params={"apikey": API_KEY, "offset": offset}
    )
    data = r2.json()
    for m in data.get("data", []):
        if m.get("series_id") == SERIES_ID:
            current_ipl[m["id"]] = m
    total = data.get("info", {}).get("totalRows", 0)
    if offset + 25 >= total:
        break

print(f"Current IPL matches found: {len(current_ipl)}")
print(f"API hits used: {r2.json().get('info',{}).get('hitsToday','N/A')}")
print()

# Step 3: Build lookup from team names + date → correct ID
# currentMatches has correct IDs, series_info has match numbers
current_by_teams = {}
for m in current_ipl.values():
    teams = tuple(sorted(m.get("teams", [])))
    date  = m.get("date", "")
    key   = (teams, date)
    current_by_teams[key] = m["id"]

# Step 4: Match series_info entries to current IDs
print(f"{'Match':<8} {'Series ID':<40} {'Current ID':<40} {'Name'}")
print("-" * 130)

results = []
for m in sorted(series_matches, key=lambda x: x.get("date","")):
    name  = m.get("name", "")
    teams = tuple(sorted(m.get("teams", [])))
    date  = m.get("date", "")
    series_id = m["id"]

    # Extract match number
    match_num = "?"
    for part in name.split(","):
        part = part.strip()
        if "Match" in part:
            num = part.replace("Match","").replace("th","").replace("st","").replace("nd","").replace("rd","").strip()
            try:
                match_num = int(num)
            except:
                pass

    # Find correct ID from currentMatches
    correct_id = current_by_teams.get((teams, date), "NOT IN CURRENT")

    print(f"M{str(match_num):<6} {series_id:<40} {correct_id:<40} "
          f"{','.join(m.get('teams',[]))[:40]}")
    
    results.append({
        "match_num": match_num,
        "series_id": series_id,
        "correct_id": correct_id,
        "teams": m.get("teams", []),
        "date": date,
        "name": name
    })

# Step 5: Generate update SQL for matches where IDs differ
print("\n" + "="*60)
print("UPDATE SCRIPT FOR MISMATCHED IDs:")
print("="*60)
for r in results:
    if r["correct_id"] != "NOT IN CURRENT" and \
       r["correct_id"] != r["series_id"]:
        print(f"# Match {r['match_num']}: {','.join(r['teams'])}")
        print(f"# Series ID: {r['series_id']}")
        print(f"# Correct ID: {r['correct_id']}")
        print(f"({r['match_num']}, \"{r['correct_id']}\"),")
        print()