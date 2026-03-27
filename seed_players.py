#from app import app
from database import db, Player, Match
from datetime import datetime

def seed_players():
    if True:  # context already active when called from app.py
        Player.query.delete()
        db.session.commit()

        players = [
            # Mumbai Indians
            Player(name="Rohit Sharma", ipl_team="Mumbai Indians", role="batsman", credits=10.5),
            Player(name="Ishan Kishan", ipl_team="Mumbai Indians", role="keeper", credits=9.5),
            Player(name="Suryakumar Yadav", ipl_team="Mumbai Indians", role="batsman", credits=10.0),
            Player(name="Hardik Pandya", ipl_team="Mumbai Indians", role="allrounder", credits=11.0),
            Player(name="Jasprit Bumrah", ipl_team="Mumbai Indians", role="bowler", credits=10.5),
            Player(name="Tim David", ipl_team="Mumbai Indians", role="batsman", credits=8.5),
            Player(name="Tilak Varma", ipl_team="Mumbai Indians", role="batsman", credits=8.5),
            Player(name="Naman Dhir", ipl_team="Mumbai Indians", role="allrounder", credits=7.5),
            Player(name="Trent Boult", ipl_team="Mumbai Indians", role="bowler", credits=9.0),
            Player(name="Deepak Chahar", ipl_team="Mumbai Indians", role="bowler", credits=8.0),

            # Chennai Super Kings
            Player(name="MS Dhoni", ipl_team="Chennai Super Kings", role="keeper", credits=10.0),
            Player(name="Ruturaj Gaikwad", ipl_team="Chennai Super Kings", role="batsman", credits=10.0),
            Player(name="Ravindra Jadeja", ipl_team="Chennai Super Kings", role="allrounder", credits=10.5),
            Player(name="Shivam Dube", ipl_team="Chennai Super Kings", role="allrounder", credits=8.5),
            Player(name="Devon Conway", ipl_team="Chennai Super Kings", role="batsman", credits=8.5),
            Player(name="Tushar Deshpande", ipl_team="Chennai Super Kings", role="bowler", credits=8.0),
            Player(name="Matheesha Pathirana", ipl_team="Chennai Super Kings", role="bowler", credits=8.5),
            Player(name="Rachin Ravindra", ipl_team="Chennai Super Kings", role="allrounder", credits=8.0),

            # Royal Challengers Bengaluru
            Player(name="Virat Kohli", ipl_team="Royal Challengers Bengaluru", role="batsman", credits=12.0),
            Player(name="Faf du Plessis", ipl_team="Royal Challengers Bengaluru", role="batsman", credits=9.0),
            Player(name="Glenn Maxwell", ipl_team="Royal Challengers Bengaluru", role="allrounder", credits=9.5),
            Player(name="Mohammed Siraj", ipl_team="Royal Challengers Bengaluru", role="bowler", credits=9.0),
            Player(name="Dinesh Karthik", ipl_team="Royal Challengers Bengaluru", role="keeper", credits=8.0),
            Player(name="Yash Dayal", ipl_team="Royal Challengers Bengaluru", role="bowler", credits=7.5),
            Player(name="Cameron Green", ipl_team="Royal Challengers Bengaluru", role="allrounder", credits=8.5),

            # Kolkata Knight Riders
            Player(name="Shreyas Iyer", ipl_team="Kolkata Knight Riders", role="batsman", credits=9.5),
            Player(name="Andre Russell", ipl_team="Kolkata Knight Riders", role="allrounder", credits=10.5),
            Player(name="Sunil Narine", ipl_team="Kolkata Knight Riders", role="allrounder", credits=10.0),
            Player(name="Varun Chakravarthy", ipl_team="Kolkata Knight Riders", role="bowler", credits=9.0),
            Player(name="Phil Salt", ipl_team="Kolkata Knight Riders", role="keeper", credits=8.5),
            Player(name="Rinku Singh", ipl_team="Kolkata Knight Riders", role="batsman", credits=8.5),
            Player(name="Harshit Rana", ipl_team="Kolkata Knight Riders", role="bowler", credits=8.0),

            # Delhi Capitals
            Player(name="Rishabh Pant", ipl_team="Delhi Capitals", role="keeper", credits=10.5),
            Player(name="David Warner", ipl_team="Delhi Capitals", role="batsman", credits=9.0),
            Player(name="Axar Patel", ipl_team="Delhi Capitals", role="allrounder", credits=9.0),
            Player(name="Anrich Nortje", ipl_team="Delhi Capitals", role="bowler", credits=9.0),
            Player(name="Mitchell Marsh", ipl_team="Delhi Capitals", role="allrounder", credits=9.5),
            Player(name="Prithvi Shaw", ipl_team="Delhi Capitals", role="batsman", credits=7.5),
            Player(name="Kuldeep Yadav", ipl_team="Delhi Capitals", role="bowler", credits=9.5),

            # Rajasthan Royals
            Player(name="Sanju Samson", ipl_team="Rajasthan Royals", role="keeper", credits=10.0),
            Player(name="Jos Buttler", ipl_team="Rajasthan Royals", role="batsman", credits=10.5),
            Player(name="Yashasvi Jaiswal", ipl_team="Rajasthan Royals", role="batsman", credits=10.5),
            Player(name="Ravichandran Ashwin", ipl_team="Rajasthan Royals", role="bowler", credits=8.5),
            Player(name="Shimron Hetmyer", ipl_team="Rajasthan Royals", role="batsman", credits=8.0),
            Player(name="Yuzvendra Chahal", ipl_team="Rajasthan Royals", role="bowler", credits=9.0),

            # Punjab Kings
            Player(name="Shikhar Dhawan", ipl_team="Punjab Kings", role="batsman", credits=8.5),
            Player(name="Liam Livingstone", ipl_team="Punjab Kings", role="allrounder", credits=9.0),
            Player(name="Arshdeep Singh", ipl_team="Punjab Kings", role="bowler", credits=9.0),
            Player(name="Jonny Bairstow", ipl_team="Punjab Kings", role="keeper", credits=8.5),
            Player(name="Sam Curran", ipl_team="Punjab Kings", role="allrounder", credits=9.0),
            Player(name="Kagiso Rabada", ipl_team="Punjab Kings", role="bowler", credits=9.5),

            # Sunrisers Hyderabad
            Player(name="Pat Cummins", ipl_team="Sunrisers Hyderabad", role="allrounder", credits=10.5),
            Player(name="Heinrich Klaasen", ipl_team="Sunrisers Hyderabad", role="keeper", credits=9.5),
            Player(name="Travis Head", ipl_team="Sunrisers Hyderabad", role="batsman", credits=10.0),
            Player(name="Abhishek Sharma", ipl_team="Sunrisers Hyderabad", role="allrounder", credits=9.0),
            Player(name="Bhuvneshwar Kumar", ipl_team="Sunrisers Hyderabad", role="bowler", credits=8.5),
            Player(name="T Natarajan", ipl_team="Sunrisers Hyderabad", role="bowler", credits=8.0),

            # Gujarat Titans
            Player(name="Shubman Gill", ipl_team="Gujarat Titans", role="batsman", credits=10.5),
            Player(name="Mohammed Shami", ipl_team="Gujarat Titans", role="bowler", credits=9.5),
            Player(name="Wriddhiman Saha", ipl_team="Gujarat Titans", role="keeper", credits=7.5),
            Player(name="Rashid Khan", ipl_team="Gujarat Titans", role="bowler", credits=10.5),
            Player(name="David Miller", ipl_team="Gujarat Titans", role="batsman", credits=8.5),

            # Lucknow Super Giants
            Player(name="KL Rahul", ipl_team="Lucknow Super Giants", role="keeper", credits=10.5),
            Player(name="Quinton de Kock", ipl_team="Lucknow Super Giants", role="keeper", credits=9.5),
            Player(name="Marcus Stoinis", ipl_team="Lucknow Super Giants", role="allrounder", credits=9.0),
            Player(name="Ravi Bishnoi", ipl_team="Lucknow Super Giants", role="bowler", credits=8.5),
            Player(name="Mark Wood", ipl_team="Lucknow Super Giants", role="bowler", credits=9.0),
            Player(name="Nicholas Pooran", ipl_team="Lucknow Super Giants", role="keeper", credits=9.0),
        ]

        db.session.add_all(players)
        db.session.commit()
        print(f"✅ {len(players)} players seeded successfully!")

def seed_matches():
    if True:  # context already active when called from app.py
        Match.query.delete()
        db.session.commit()

        matches = [
            Match(match_number=1, team1="Royal Challengers Bengaluru", team2="Sunrisers Hyderabad",
                  venue="M. Chinnaswamy Stadium, Bengaluru", match_date=datetime(2026, 3, 28, 19, 30),
                  status="completed", cricapi_match_id="55fe0f15-6eb0-4ad5-835b-5564be4f6a21"),
            Match(match_number=2, team1="Mumbai Indians", team2="Kolkata Knight Riders",
                  venue="Wankhede Stadium, Mumbai", match_date=datetime(2026, 3, 29, 19, 30),
                  status="completed", cricapi_match_id="e02475c1-8f9a-4915-a9e8-d4dbc3441c96"),
            Match(match_number=3, team1="Rajasthan Royals", team2="Chennai Super Kings",
                  venue="Sawai Mansingh Stadium, Jaipur", match_date=datetime(2026, 3, 30, 19, 30),
                  status="completed", cricapi_match_id="d788e9f9-99bf-4650-a035-92a7e21b3d08"),
            Match(match_number=4, team1="Punjab Kings", team2="Gujarat Titans",
                  venue="Punjab Cricket Association Stadium, Mohali", match_date=datetime(2026, 3, 31, 19, 30),
                  status="completed", cricapi_match_id="11ff7db9-9c71-464e-afcb-5b03e4fa4b0a"),
            Match(match_number=5, team1="Lucknow Super Giants", team2="Delhi Capitals",
                  venue="BRSABV Ekana Cricket Stadium, Lucknow", match_date=datetime(2026, 4, 1, 19, 30),
                  status="completed", cricapi_match_id="ae676d7c-3082-489c-96c5-5620f393c900"),
            Match(match_number=6, team1="Kolkata Knight Riders", team2="Sunrisers Hyderabad",
                  venue="Eden Gardens, Kolkata", match_date=datetime(2026, 4, 2, 19, 30),
                  status="completed", cricapi_match_id="fd010e39-2255-4460-b0e0-962a26b67b70"),
            Match(match_number=7, team1="Chennai Super Kings", team2="Punjab Kings",
                  venue="MA Chidambaram Stadium, Chennai", match_date=datetime(2026, 4, 3, 19, 30),
                  status="completed", cricapi_match_id="96d2aa6b-ea40-4da4-b4cf-eb996de24ef7"),
            Match(match_number=8, team1="Gujarat Titans", team2="Rajasthan Royals",
                  venue="Narendra Modi Stadium, Ahmedabad", match_date=datetime(2026, 4, 4, 19, 30),
                  status="completed", cricapi_match_id="ea4d01bf-bf47-4f7d-a4f8-32eade678141"),
            Match(match_number=9, team1="Sunrisers Hyderabad", team2="Lucknow Super Giants",
                  venue="Rajiv Gandhi Stadium, Hyderabad", match_date=datetime(2026, 4, 5, 19, 30),
                  status="completed", cricapi_match_id="e43dd29e-c60e-40c9-a6c4-6c1bd69dd671"),
            Match(match_number=10, team1="Royal Challengers Bengaluru", team2="Chennai Super Kings",
                  venue="M. Chinnaswamy Stadium, Bengaluru", match_date=datetime(2026, 4, 5, 15, 30),
                  status="completed", cricapi_match_id="e92727d0-61fc-4c6f-82ed-cde4789745a2"),
            Match(match_number=11, team1="Kolkata Knight Riders", team2="Punjab Kings",
                  venue="Eden Gardens, Kolkata", match_date=datetime(2026, 4, 6, 19, 30),
                  status="completed", cricapi_match_id="adeebb28-bc39-439b-99ed-2daef5106232"),
            Match(match_number=12, team1="Rajasthan Royals", team2="Mumbai Indians",
                  venue="Sawai Mansingh Stadium, Jaipur", match_date=datetime(2026, 4, 7, 19, 30),
                  status="upcoming", cricapi_match_id="4f617f5e-c635-4989-b135-5430dc73c5d7"),
            Match(match_number=13, team1="Delhi Capitals", team2="Gujarat Titans",
                  venue="Arun Jaitley Stadium, Delhi", match_date=datetime(2026, 4, 8, 19, 30),
                  status="upcoming", cricapi_match_id="12496498-8526-46d9-a053-da2ba8d047e1"),
            Match(match_number=14, team1="Kolkata Knight Riders", team2="Lucknow Super Giants",
                  venue="Eden Gardens, Kolkata", match_date=datetime(2026, 4, 9, 19, 30),
                  status="upcoming", cricapi_match_id="c78dcc8a-67cf-460a-8f2b-8f16d3891682"),
            Match(match_number=15, team1="Rajasthan Royals", team2="Royal Challengers Bengaluru",
                  venue="Sawai Mansingh Stadium, Jaipur", match_date=datetime(2026, 4, 10, 19, 30),
                  status="upcoming", cricapi_match_id="05a88a74-0e68-47d9-996b-257b3b1ebf8d"),
            Match(match_number=16, team1="Punjab Kings", team2="Sunrisers Hyderabad",
                  venue="Punjab Cricket Association Stadium, Mohali", match_date=datetime(2026, 4, 11, 19, 30),
                  status="upcoming", cricapi_match_id="a4cd9851-d79a-42b6-8a4b-b35cbb9f9f0a"),
            Match(match_number=17, team1="Chennai Super Kings", team2="Delhi Capitals",
                  venue="MA Chidambaram Stadium, Chennai", match_date=datetime(2026, 4, 11, 15, 30),
                  status="upcoming", cricapi_match_id="204afd0a-026a-41f4-afda-653030a84e46"),
            Match(match_number=18, team1="Mumbai Indians", team2="Royal Challengers Bengaluru",
                  venue="Wankhede Stadium, Mumbai", match_date=datetime(2026, 4, 12, 19, 30),
                  status="upcoming", cricapi_match_id="11d553de-3b2a-4e58-9abd-4bb7d575595e"),
            Match(match_number=19, team1="Lucknow Super Giants", team2="Gujarat Titans",
                  venue="BRSABV Ekana Cricket Stadium, Lucknow", match_date=datetime(2026, 4, 12, 15, 30),
                  status="upcoming", cricapi_match_id="36d875e2-3333-4fab-ba4d-4f89fb4d7055"),
        ]

        db.session.add_all(matches)
        db.session.commit()
        print(f"✅ {len(matches)} matches seeded successfully!")

if __name__ == "__main__":
    from app import app
    with app.app_context():
      seed_players()
      seed_matches()