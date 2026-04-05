# save as fetch_schedule.py
import requests, json

API_KEY = "0fcdf764-1fd7-46b9-9d4c-6698264d48ee"
SERIES_ID = "87c62aac-bc3c-4738-ab93-19da0690488f"

r = requests.get(
    "https://api.cricapi.com/v1/series_info",
    params={"apikey": API_KEY, "id": SERIES_ID}
)
data = r.json()

print(f"Status: {data.get('status')}")
print(f"API calls remaining: {data.get('info', {}).get('hitsToday', 'N/A')}")
print()

matches = data.get("data", {}).get("matchList", [])
print(f"Total matches found: {len(matches)}")
print()

for m in matches:
    print(f"Name: {m.get('name')}")
    print(f"  ID:   {m.get('id')}")
    print(f"  Date: {m.get('date')}")
    print(f"  Venue: {m.get('venue', 'N/A')}")
    print()

# Save full response for reference
with open("ipl2026_schedule.json", "w") as f:
    json.dump(data, f, indent=2)
print("Full response saved to ipl2026_schedule.json")