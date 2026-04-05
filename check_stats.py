# save as fix_match8.py
from app import app
from database import db, Match
app.app_context().push()

match = Match.query.filter_by(match_number=8).first()
print(f"Current ID: {match.cricapi_match_id}")
match.cricapi_match_id = "PASTE_CORRECT_ID_HERE"
db.session.commit()
print(f"Updated to: {match.cricapi_match_id}")