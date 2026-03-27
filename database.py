from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
def utcnow():
    return datetime.now(timezone.utc)


db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    team_name = db.Column(db.String(80), nullable=True)
    transfers_remaining = db.Column(db.Integer, default=150)
    total_points = db.Column(db.Float, default=0)
    is_admin = db.Column(db.Boolean, default=False)
    joined_at = db.Column(db.DateTime, default=utcnow)

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    ipl_team = db.Column(db.String(80), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # batsman, bowler, allrounder, keeper
    credits = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True)

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    match_number = db.Column(db.Integer, nullable=False)
    team1 = db.Column(db.String(80), nullable=False)
    team2 = db.Column(db.String(80), nullable=False)
    venue = db.Column(db.String(120), nullable=False)
    match_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default="upcoming")  # upcoming, live, completed
    cricapi_match_id = db.Column(db.String(100), nullable=True)  # for API calls

class UserTeam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    player_ids = db.Column(db.String(200), nullable=False)  # comma separated 11 player ids
    captain_id = db.Column(db.Integer, nullable=False)
    vice_captain_id = db.Column(db.Integer, nullable=False)
    last_updated = db.Column(db.DateTime, default=utcnow)

    

class UserMatchTeam(db.Model):
    # Snapshot of user's team for each match (for points calculation)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey("match.id"), nullable=False)
    player_ids = db.Column(db.String(200), nullable=False)
    captain_id = db.Column(db.Integer, nullable=False)
    vice_captain_id = db.Column(db.Integer, nullable=False)
    points_scored = db.Column(db.Float, default=0)

class PlayerMatchStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey("player.id"), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey("match.id"), nullable=False)
    runs = db.Column(db.Integer, default=0)
    balls_faced = db.Column(db.Integer, default=0)
    fours = db.Column(db.Integer, default=0)
    sixes = db.Column(db.Integer, default=0)
    wickets = db.Column(db.Integer, default=0)
    overs_bowled = db.Column(db.Float, default=0)
    runs_conceded = db.Column(db.Integer, default=0)
    catches = db.Column(db.Integer, default=0)
    stumpings = db.Column(db.Integer, default=0)
    maidens = db.Column(db.Integer, default=0)
    run_outs = db.Column(db.Integer, default=0)
    did_play = db.Column(db.Boolean, default=False)
    is_motm = db.Column(db.Boolean, default=False)
    is_winner = db.Column(db.Boolean, default=False)
    points_earned = db.Column(db.Float, default=0)

class League(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    manager_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    league_code = db.Column(db.String(8), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)

class LeagueMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    league_id = db.Column(db.Integer, db.ForeignKey("league.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    joined_at = db.Column(db.DateTime, default=utcnow)

class TransferWindow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    window_start_match = db.Column(db.Integer, db.ForeignKey("match.id"), nullable=False)
    baseline_player_ids = db.Column(db.String(200), nullable=False)  # team at window start
    transfers_used = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=utcnow)
    
class TransferHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    window_match_id = db.Column(db.Integer, db.ForeignKey("match.id"), nullable=False)
    player_in_id = db.Column(db.Integer, db.ForeignKey("player.id"), nullable=False)
    player_out_id = db.Column(db.Integer, db.ForeignKey("player.id"), nullable=False)
    transferred_at = db.Column(db.DateTime, default=utcnow)