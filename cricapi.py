import urllib.request
import json

API_KEY = "0fcdf764-1fd7-46b9-9d4c-6698264d48ee"
BASE_URL = "https://api.cricapi.com/v1"

def api_get(endpoint, params={}):
    params["apikey"] = API_KEY
    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{BASE_URL}/{endpoint}?{query}"
    try:
        response = urllib.request.urlopen(url)
        return json.loads(response.read())
    except Exception as e:
        print(f"API Error: {e}")
        return None

def get_match_scorecard(match_id):
    return api_get("match_scorecard", {"id": match_id})

def get_current_matches():
    return api_get("currentMatches", {"offset": 0})

def get_match_info(match_id):
    return api_get("match_info", {"id": match_id})