# save as find_match_id.py
import requests

API_KEY = "0fcdf764-1fd7-46b9-9d4c-6698264d48ee"
SERIES_ID = "87c62aac-bc3c-4738-ab93-19da0690488f"

r = requests.get(
    "https://api.cricapi.com/v1/series_info",
    params={"apikey": API_KEY, "id": SERIES_ID}
)
data = r.json()

for match in data.get("data", {}).get("matchList", []):
    if "Delhi" in match.get("name","") and "Mumbai" in match.get("name",""):
        print(f"FOUND: {match['name']}")
        print(f"  ID: {match['id']}")
        print(f"  Date: {match.get('date','')}")