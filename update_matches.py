# save as update_matches.py
from app import app
from database import db, Match
from datetime import datetime

app.app_context().push()

# Complete IPL 2026 schedule from CricAPI
# Format: (match_number, cricapi_id, team1, team2, date_ist, venue)
MATCHES = [
    (1,  "55fe0f15-6eb0-4ad5-835b-5564be4f6a21", "Royal Challengers Bengaluru", "Sunrisers Hyderabad",     "2026-03-28 19:30", "M.Chinnaswamy Stadium, Bengaluru"),
    (2,  "e02475c1-8f9a-4915-a9e8-d4dbc3441c96", "Mumbai Indians",             "Kolkata Knight Riders",    "2026-03-29 19:30", "Wankhede Stadium, Mumbai"),
    (3,  "d788e9f9-99bf-4650-a035-92a7e21b3d08", "Rajasthan Royals",           "Chennai Super Kings",      "2026-03-30 19:30", "Barsapara Cricket Stadium, Guwahati"),
    (4,  "11ff7db9-9c71-464e-afcb-5b03e4fa4b0a", "Punjab Kings",               "Gujarat Titans",           "2026-03-31 19:30", "Maharaja Yadavindra Singh International Cricket Stadium, Mullanpur, New Chandigarh"),
    (5,  "ae676d7c-3082-489c-96c5-5620f393c900", "Lucknow Super Giants",       "Delhi Capitals",           "2026-04-01 19:30", "Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium, Lucknow"),
    (6,  "fd010e39-2255-4460-b0e0-962a26b67b70", "Kolkata Knight Riders",      "Sunrisers Hyderabad",      "2026-04-02 19:30", "Eden Gardens, Kolkata"),
    (7,  "96d2aa6b-ea40-4da4-b4cf-eb996de24ef7", "Chennai Super Kings",        "Punjab Kings",             "2026-04-03 19:30", "MA Chidambaram Stadium, Chennai"),
    (8,  "736f3e02-212a-49bc-8b3b-08a106312702", "Delhi Capitals",             "Mumbai Indians",           "2026-04-04 15:30", "Arun Jaitley Stadium, Delhi"),
    (9,  "ea4d01bf-bf47-4f7d-a4f8-32eade678141", "Gujarat Titans",             "Rajasthan Royals",         "2026-04-04 19:30", "Narendra Modi Stadium, Ahmedabad"),
    (10, "e43dd29e-c60e-40c9-a6c4-6c1bd69dd671", "Sunrisers Hyderabad",        "Lucknow Super Giants",     "2026-04-05 15:30", "Rajiv Gandhi International Stadium, Hyderabad"),
    (11, "e92727d0-61fc-4c6f-82ed-cde4789745a2", "Royal Challengers Bengaluru","Chennai Super Kings",      "2026-04-05 19:30", "M.Chinnaswamy Stadium, Bengaluru"),
    (12, "adeebb28-bc39-439b-99ed-2daef5106232", "Kolkata Knight Riders",      "Punjab Kings",             "2026-04-06 19:30", "Eden Gardens, Kolkata"),
    (13, "4f617f5e-c635-4989-b135-5430dc73c5d7", "Rajasthan Royals",           "Mumbai Indians",           "2026-04-07 19:30", "Barsapara Cricket Stadium, Guwahati"),
    (14, "12496498-8526-46d9-a053-da2ba8d047e1", "Delhi Capitals",             "Gujarat Titans",           "2026-04-08 19:30", "Arun Jaitley Stadium, Delhi"),
    (15, "c78dcc8a-67cf-460a-8f2b-8f16d3891682", "Kolkata Knight Riders",      "Lucknow Super Giants",     "2026-04-09 19:30", "Eden Gardens, Kolkata"),
    (16, "05a88a74-0e68-47d9-996b-257b3b1ebf8d", "Rajasthan Royals",           "Royal Challengers Bengaluru","2026-04-10 19:30","Barsapara Cricket Stadium, Guwahati"),
    (17, "a4cd9851-d79a-42b6-8a4b-b35cbb9f9f0a", "Punjab Kings",               "Sunrisers Hyderabad",      "2026-04-11 15:30", "Maharaja Yadavindra Singh International Cricket Stadium, Mullanpur, New Chandigarh"),
    (18, "204afd0a-026a-41f4-afda-653030a84e46", "Chennai Super Kings",        "Delhi Capitals",           "2026-04-11 19:30", "MA Chidambaram Stadium, Chennai"),
    (19, "36d875e2-3333-4fab-ba4d-4f89fb4d7055", "Lucknow Super Giants",       "Gujarat Titans",           "2026-04-12 15:30", "Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium, Lucknow"),
    (20, "11d553de-3b2a-4e58-9abd-4bb7d575595e", "Mumbai Indians",             "Royal Challengers Bengaluru","2026-04-12 19:30","Wankhede Stadium, Mumbai"),
    (21, "4a2b94e3-1e2d-45dc-b542-4764807e06e2", "Sunrisers Hyderabad",        "Rajasthan Royals",         "2026-04-13 19:30", "Rajiv Gandhi International Stadium, Hyderabad"),
    (22, "f30e699c-2e4f-48dd-98d2-4321d9e622e7", "Chennai Super Kings",        "Kolkata Knight Riders",    "2026-04-14 19:30", "MA Chidambaram Stadium, Chennai"),
    (23, "e8225a82-12c7-4bc8-8e40-4892f52d7d21", "Royal Challengers Bengaluru","Lucknow Super Giants",     "2026-04-15 19:30", "M.Chinnaswamy Stadium, Bengaluru"),
    (24, "d0279d32-e120-4b96-b600-efa118f6ec12", "Mumbai Indians",             "Punjab Kings",             "2026-04-16 19:30", "Wankhede Stadium, Mumbai"),
    (25, "c8f30ec3-a953-438a-ba4a-c5dedd97063a", "Gujarat Titans",             "Kolkata Knight Riders",    "2026-04-17 19:30", "Narendra Modi Stadium, Ahmedabad"),
    (26, "d9242d24-f86f-4dbd-8291-3b00eadcda4a", "Royal Challengers Bengaluru","Delhi Capitals",           "2026-04-18 15:30", "M.Chinnaswamy Stadium, Bengaluru"),
    (27, "de4a5f85-ea02-4426-a074-a0bff9f757ca", "Sunrisers Hyderabad",        "Chennai Super Kings",      "2026-04-18 19:30", "Rajiv Gandhi International Stadium, Hyderabad"),
    (28, "a86beb23-22f5-4afb-914c-f2b9f6711166", "Kolkata Knight Riders",      "Rajasthan Royals",         "2026-04-19 15:30", "Eden Gardens, Kolkata"),
    (29, "91f9f16f-8c16-408b-ac66-7b5c7e9b4af0", "Punjab Kings",               "Lucknow Super Giants",     "2026-04-19 19:30", "Maharaja Yadavindra Singh International Cricket Stadium, Mullanpur, New Chandigarh"),
    (30, "f72cb89b-3085-4556-a814-d28a44885b0e", "Gujarat Titans",             "Mumbai Indians",           "2026-04-20 19:30", "Narendra Modi Stadium, Ahmedabad"),
    (31, "771739a7-564d-412d-a181-05722657e8f6", "Sunrisers Hyderabad",        "Delhi Capitals",           "2026-04-21 19:30", "Rajiv Gandhi International Stadium, Hyderabad"),
    (32, "0d462688-8d5b-4aef-936c-094c7b664bb3", "Lucknow Super Giants",       "Rajasthan Royals",         "2026-04-22 19:30", "Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium, Lucknow"),
    (33, "ef0699eb-29be-4949-8e4f-474e90a6be6b", "Mumbai Indians",             "Chennai Super Kings",      "2026-04-23 19:30", "Wankhede Stadium, Mumbai"),
    (34, "bff622ad-fe85-46f0-8969-80a3df72face", "Royal Challengers Bengaluru","Gujarat Titans",           "2026-04-24 19:30", "M.Chinnaswamy Stadium, Bengaluru"),
    (35, "0a8f942f-d951-4dd4-9543-3077af3c91eb", "Delhi Capitals",             "Punjab Kings",             "2026-04-25 15:30", "Arun Jaitley Stadium, Delhi"),
    (36, "c2c75e2e-df87-47fa-8ccd-8473058efae5", "Rajasthan Royals",           "Sunrisers Hyderabad",      "2026-04-25 19:30", "Sawai Mansingh Stadium, Jaipur"),
    (37, "3bfe7704-4818-4501-9708-35261cb09f96", "Gujarat Titans",             "Chennai Super Kings",      "2026-04-26 15:30", "Narendra Modi Stadium, Ahmedabad"),
    (38, "eab75760-b25e-421f-8321-eb0806cbb784", "Lucknow Super Giants",       "Kolkata Knight Riders",    "2026-04-26 19:30", "Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium, Lucknow"),
    (39, "0ed37800-881a-401b-a1fe-f41adb244741", "Delhi Capitals",             "Royal Challengers Bengaluru","2026-04-27 19:30","Arun Jaitley Stadium, Delhi"),
    (40, "80dbe709-8a04-48b2-878d-988042000536", "Punjab Kings",               "Rajasthan Royals",         "2026-04-28 19:30", "Maharaja Yadavindra Singh International Cricket Stadium, Mullanpur, New Chandigarh"),
    (41, "595e2ad6-5b3a-4f81-9c8f-84ee3633b8c7", "Mumbai Indians",             "Sunrisers Hyderabad",      "2026-04-29 19:30", "Wankhede Stadium, Mumbai"),
    (42, "abe1482c-3e40-43c8-be6f-9da9da643111", "Gujarat Titans",             "Royal Challengers Bengaluru","2026-04-30 19:30","Narendra Modi Stadium, Ahmedabad"),
    (43, "f2c8b750-3dcd-41c0-acbf-0e9c179eddaf", "Rajasthan Royals",           "Delhi Capitals",           "2026-05-01 19:30", "Sawai Mansingh Stadium, Jaipur"),
    (44, "ca40682e-02d0-40a0-9a4c-f2a9c8754de0", "Chennai Super Kings",        "Mumbai Indians",           "2026-05-02 19:30", "MA Chidambaram Stadium, Chennai"),
    (45, "178d76ff-214e-46a7-8fe2-27ab7afb75d3", "Sunrisers Hyderabad",        "Kolkata Knight Riders",    "2026-05-03 15:30", "Rajiv Gandhi International Stadium, Hyderabad"),
    (46, "37b02340-7238-41b7-bcf3-8ae4215e4bee", "Gujarat Titans",             "Punjab Kings",             "2026-05-03 19:30", "Narendra Modi Stadium, Ahmedabad"),
    (47, "34d1e7e5-a498-4a9b-bb89-5a273ef81b8d", "Mumbai Indians",             "Lucknow Super Giants",     "2026-05-04 19:30", "Wankhede Stadium, Mumbai"),
    (48, "c741ba65-dc7d-40cb-8e2c-7a415f3df8ab", "Delhi Capitals",             "Chennai Super Kings",      "2026-05-05 19:30", "Arun Jaitley Stadium, Delhi"),
    (49, "d9c104ce-83e8-4342-97d5-33d7ece256b4", "Sunrisers Hyderabad",        "Punjab Kings",             "2026-05-06 19:30", "Rajiv Gandhi International Stadium, Hyderabad"),
    (50, "79770ea7-9819-4414-97fe-f01444aa8ccf", "Lucknow Super Giants",       "Royal Challengers Bengaluru","2026-05-07 19:30","Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium, Lucknow"),
    (51, "058243dd-5399-42b2-ae68-d3e9796fa3b2", "Delhi Capitals",             "Kolkata Knight Riders",    "2026-05-08 19:30", "Arun Jaitley Stadium, Delhi"),
    (52, "1511024c-7c43-453d-b3db-2ee6d6ee6c6e", "Rajasthan Royals",           "Gujarat Titans",           "2026-05-09 19:30", "Sawai Mansingh Stadium, Jaipur"),
    (53, "129a6173-9149-481f-9eeb-e1c8afe1533f", "Chennai Super Kings",        "Lucknow Super Giants",     "2026-05-10 15:30", "MA Chidambaram Stadium, Chennai"),
    (54, "634ea924-b96f-478a-bd6f-48370174f344", "Royal Challengers Bengaluru","Mumbai Indians",           "2026-05-10 19:30", "Shaheed Veer Narayan Singh International Stadium, Raipur"),
    (55, "9c3b727a-2767-4e2b-a30c-855b3c6b59aa", "Punjab Kings",               "Delhi Capitals",           "2026-05-11 19:30", "Himachal Pradesh Cricket Association Stadium, Dharamsala"),
    (56, "ae3b8240-34ff-48ea-b74b-4840ab72ae33", "Gujarat Titans",             "Sunrisers Hyderabad",      "2026-05-12 19:30", "Narendra Modi Stadium, Ahmedabad"),
    (57, "ef86ee7b-dbea-4e3c-9bbf-af77da1ff223", "Royal Challengers Bengaluru","Kolkata Knight Riders",    "2026-05-13 19:30", "Shaheed Veer Narayan Singh International Stadium, Raipur"),
    (58, "df78909a-2ab7-4760-b679-705c381bd2d3", "Punjab Kings",               "Mumbai Indians",           "2026-05-14 19:30", "Himachal Pradesh Cricket Association Stadium, Dharamsala"),
    (59, "999ec29a-1cdf-48e0-b8c5-9d3ae95a45c3", "Lucknow Super Giants",       "Chennai Super Kings",      "2026-05-15 19:30", "Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium, Lucknow"),
    (60, "a30ef3c8-1002-4181-9167-39b9b7ea7760", "Kolkata Knight Riders",      "Gujarat Titans",           "2026-05-16 19:30", "Eden Gardens, Kolkata"),
    (61, "26e1c31e-1033-4d72-887e-2c6ccb09b82f", "Punjab Kings",               "Royal Challengers Bengaluru","2026-05-17 15:30","Himachal Pradesh Cricket Association Stadium, Dharamsala"),
    (62, "0ea0c97c-6fb6-4728-832e-5abd0820edc2", "Delhi Capitals",             "Rajasthan Royals",         "2026-05-17 19:30", "Arun Jaitley Stadium, Delhi"),
    (63, "66477e53-9cd5-4be2-bc3d-78114722da72", "Chennai Super Kings",        "Sunrisers Hyderabad",      "2026-05-18 19:30", "MA Chidambaram Stadium, Chennai"),
    (64, "39a0b9c4-bcb7-4dd6-b21c-e9bf537edce7", "Rajasthan Royals",           "Lucknow Super Giants",     "2026-05-19 19:30", "Sawai Mansingh Stadium, Jaipur"),
    (65, "e5b677a2-6e87-4c9e-baa5-d997644501f1", "Kolkata Knight Riders",      "Mumbai Indians",           "2026-05-20 19:30", "Eden Gardens, Kolkata"),
    (66, "2b441eeb-c4be-4d4e-892e-92f2e47b33df", "Chennai Super Kings",        "Gujarat Titans",           "2026-05-21 19:30", "MA Chidambaram Stadium, Chennai"),
    (67, "25c031c2-2776-48a7-824c-fe66e0e6cf48", "Sunrisers Hyderabad",        "Royal Challengers Bengaluru","2026-05-22 19:30","Rajiv Gandhi International Stadium, Hyderabad"),
    (68, "913bdcbf-179f-452e-a2ed-75f807b7c2b0", "Lucknow Super Giants",       "Punjab Kings",             "2026-05-23 19:30", "Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium, Lucknow"),
    (69, "e1ecf776-e9eb-4456-82df-e6c8b6e12cd3", "Mumbai Indians",             "Rajasthan Royals",         "2026-05-24 15:30", "Wankhede Stadium, Mumbai"),
    (70, "aec16058-7741-4f3d-a1b0-68d7210b29c9", "Kolkata Knight Riders",      "Delhi Capitals",           "2026-05-24 19:30", "Eden Gardens, Kolkata"),
]

# Matches already completed — don't touch their status
COMPLETED_IDS = {
    "55fe0f15-6eb0-4ad5-835b-5564be4f6a21",  # Match 1
    "e02475c1-8f9a-4915-a9e8-d4dbc3441c96",  # Match 2
    "d788e9f9-99bf-4650-a035-92a7e21b3d08",  # Match 3
    "11ff7db9-9c71-464e-afcb-5b03e4fa4b0a",  # Match 4
    "ae676d7c-3082-489c-96c5-5620f393c900",  # Match 5
    "fd010e39-2255-4460-b0e0-962a26b67b70",  # Match 6
    "96d2aa6b-ea40-4da4-b4cf-eb996de24ef7",  # Match 7
    "736f3e02-212a-49bc-8b3b-08a106312702",  # Match 8
    "ea4d01bf-bf47-4f7d-a4f8-32eade678141",  # Match 9
    "e43dd29e-c60e-40c9-a6c4-6c1bd69dd671",  # Match 10
}

updated = 0
created = 0

for match_num, api_id, team1, team2, date_str, venue in MATCHES:
    match_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M")

    # Try to find existing match by match_number
    match = Match.query.filter_by(match_number=match_num).first()

    if match:
        # Update existing
        old_api_id = match.cricapi_match_id
        match.cricapi_match_id = api_id
        match.team1            = team1
        match.team2            = team2
        match.match_date       = match_date
        match.venue            = venue
        # Only update status if not already completed/live
        if match.status not in ("completed", "live"):
            match.status = "upcoming"
        print(f"✅ Updated Match {match_num}: {team1} vs {team2} "
              f"({'API ID changed' if old_api_id != api_id else 'same API ID'})")
        updated += 1
    else:
        # Create new match
        new_match = Match(
            match_number=match_num,
            cricapi_match_id=api_id,
            team1=team1,
            team2=team2,
            match_date=match_date,
            venue=venue,
            status="completed" if api_id in COMPLETED_IDS else "upcoming"
        )
        db.session.add(new_match)
        print(f"➕ Created Match {match_num}: {team1} vs {team2}")
        created += 1

db.session.commit()
print(f"\n🏏 Done! Updated: {updated}, Created: {created}")
print(f"Total matches in DB: {Match.query.count()}")