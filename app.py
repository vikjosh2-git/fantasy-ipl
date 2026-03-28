#from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify
from flask import Flask
from flask import render_template
from flask import redirect
from flask import url_for
from flask import request
from flask import session
from flask import flash
from flask import jsonify
from scoring_config import SCORING_CONFIG

from werkzeug.security import generate_password_hash, check_password_hash
from points import calculate_points
from datetime import datetime, timezone
def utcnow():
    return datetime.now(timezone.utc)

from scoring import process_match_points
from cricapi import get_match_info
from database import db, User, Player, Match, UserTeam, UserMatchTeam, PlayerMatchStats, League, LeagueMember, TransferWindow, TransferHistory


import random
import string

app = Flask(__name__)

import os
app.secret_key = os.environ.get("SECRET_KEY", "fantasy-ipl-secret-key")

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///fantasy_ipl.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    db.create_all()
    # Auto-seed if database is empty
    from database import Player, Match
    if Player.query.count() == 0:
        print("🌱 Empty database detected — seeding data...")
        from seed_players import seed_players, seed_matches
        seed_players()
        seed_matches()
        print("✅ Database seeded!")

# ─── Auth Routes ────────────────────────────────────────────

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["username"] = user.username
            # Redirect to team setup if no team yet
            team = UserTeam.query.filter_by(user_id=user.id).first()
            if not team:
                return redirect(url_for("select_team"))
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        team_name = request.form["team_name"]
        if User.query.filter_by(username=username).first():
            flash("Username already taken!", "error")
            return redirect(url_for("register"))
        if User.query.filter_by(email=email).first():
            flash("Email already registered!", "error")
            return redirect(url_for("register"))
        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, email=email,
               password=hashed_pw, team_name=team_name,
               transfers_remaining=SCORING_CONFIG["season_transfers"])
        
        db.session.add(new_user)
        db.session.commit()
        flash("Account created! Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ─── Dashboard ───────────────────────────────────────────────
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = User.query.get(session["user_id"])
    upcoming_matches = Match.query.filter_by(status="upcoming").order_by(Match.match_date).limit(3).all()
    live_matches = Match.query.filter_by(status="live").all()
    user_team = UserTeam.query.filter_by(user_id=user.id).first()
    players = []
    if user_team:
        player_ids = [int(x) for x in user_team.player_ids.split(",")]
        players = Player.query.filter(Player.id.in_(player_ids)).all()

    # Get next upcoming match for countdown
    next_match = Match.query.filter_by(status="upcoming").order_by(Match.match_date).first()

    return render_template("dashboard.html", user=user,
                           upcoming_matches=upcoming_matches,
                           live_matches=live_matches,
                           players=players,
                           user_team=user_team,
                           next_match=next_match)

# ─── Team Selection ───────────────────────────────────────────

@app.route("/select-team")
def select_team():
    if "user_id" not in session:
        return redirect(url_for("login"))
    players = Player.query.filter_by(is_active=True).order_by(Player.ipl_team, Player.role).all()
    user = User.query.get(session["user_id"])
    existing_team = UserTeam.query.filter_by(user_id=user.id).first()
    selected_ids = []
    captain_id = None
    vc_id = None
    if existing_team:
        selected_ids = [int(x) for x in existing_team.player_ids.split(",")]
        captain_id = existing_team.captain_id
        vc_id = existing_team.vice_captain_id

    live_match = Match.query.filter_by(status="live").first()
    any_match_started = Match.query.filter(
        Match.status.in_(["live", "completed"])
    ).first()
    next_match = Match.query.filter_by(status="upcoming").order_by(Match.match_date).first()
    next_match_teams = []
    if next_match:
        next_match_teams = [next_match.team1, next_match.team2]

    # Get season points per player for points range filter
    from database import PlayerMatchStats
    player_points = {}
    for player in players:
        stats = PlayerMatchStats.query.filter_by(player_id=player.id).all()
        player_points[player.id] = round(sum(s.points_earned for s in stats), 1)

    return render_template("team_select.html", players=players,
                           user=user, selected_ids=selected_ids,
                           captain_id=captain_id, vc_id=vc_id,
                           live_match=live_match,
                           any_match_started=any_match_started,
                           next_match=next_match,
                           next_match_teams=next_match_teams,
                           player_points=player_points)

def get_or_create_transfer_window(user_id):
    from database import TransferWindow
    last_match = Match.query.filter_by(status="completed").order_by(
        Match.match_date.desc()).first()
    window_match_id = last_match.id if last_match else 0

    window = TransferWindow.query.filter_by(
        user_id=user_id,
        window_start_match=window_match_id
    ).first()

    if not window:
        team = UserTeam.query.filter_by(user_id=user_id).first()
        baseline = team.player_ids if team else ""
        window = TransferWindow(
            user_id=user_id,
            window_start_match=window_match_id,
            baseline_player_ids=baseline,
            transfers_used=0
        )
        db.session.add(window)
        db.session.commit()

    return window

@app.route("/save-team", methods=["POST"])
def save_team():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not logged in"})

    data = request.get_json()
    user = User.query.get(session["user_id"])
    new_ids = set(data["player_ids"])

    # Get current team
    old_team = UserTeam.query.filter_by(user_id=user.id).first()
    old_ids = set(int(x) for x in old_team.player_ids.split(",") if x.strip()) if old_team else set()

    # First time selection — no transfers deducted
    is_first_selection = old_team is None

    # Check if any match has started yet
    any_match_started = Match.query.filter(
        Match.status.in_(["live", "completed"])
    ).first()

    # Pre-season or first selection — save freely, no transfers deducted
    if is_first_selection or not any_match_started:
        if old_team:
            old_team.player_ids = ",".join(str(x) for x in data["player_ids"])
            old_team.captain_id = data["captain_id"]
            old_team.vice_captain_id = data["vice_captain_id"]
            old_team.last_updated = utcnow()
        else:
            new_team = UserTeam(
                user_id=user.id,
                player_ids=",".join(str(x) for x in data["player_ids"]),
                captain_id=data["captain_id"],
                vice_captain_id=data["vice_captain_id"]
            )
            db.session.add(new_team)
        db.session.commit()
        return jsonify({
            "success": True,
            "transfers_remaining": user.transfers_remaining,
            "window_transfers_used": 0
        })

    # Season has started — enforce transfer limits
    current_window = get_or_create_transfer_window(user.id)
    baseline_ids = set(int(x) for x in current_window.baseline_player_ids.split(",") if x.strip())

    # Calculate NET transfers in this window
    net_transfers = len(new_ids - baseline_ids)
    previous_net = len(old_ids - baseline_ids)
    additional_transfers = max(0, net_transfers - previous_net)

    if additional_transfers > user.transfers_remaining:
        return jsonify({
            "success": False,
            "message": f"Not enough transfers! You need {additional_transfers} more but only have {user.transfers_remaining} remaining."
        })

    # Log individual transfers
    players_in = new_ids - old_ids
    players_out = old_ids - new_ids
    for player_in_id, player_out_id in zip(sorted(players_in), sorted(players_out)):
        history = TransferHistory(
            user_id=user.id,
            window_match_id=current_window.window_start_match,
            player_in_id=player_in_id,
            player_out_id=player_out_id,
            transferred_at=utcnow()
        )
        db.session.add(history)

    # Deduct transfers
    user.transfers_remaining -= additional_transfers
    current_window.transfers_used = net_transfers

    # Save team
    old_team.player_ids = ",".join(str(x) for x in data["player_ids"])
    old_team.captain_id = data["captain_id"]
    old_team.vice_captain_id = data["vice_captain_id"]
    old_team.last_updated = utcnow()

    db.session.commit()
    return jsonify({
        "success": True,
        "transfers_remaining": user.transfers_remaining,
        "window_transfers_used": net_transfers
    })

# ─── Matches ─────────────────────────────────────────────────
@app.route("/matches")
def matches():
    if "user_id" not in session:
        return redirect(url_for("login"))
    all_matches = Match.query.order_by(Match.match_date).all()
    return render_template("matches.html", matches=all_matches,
                           username=session["username"])

# ─── Leaderboard ─────────────────────────────────────────────

@app.route("/leaderboard")
def leaderboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    users = User.query.order_by(User.total_points.desc()).all()
    return render_template("leaderboard.html", users=users,
                           current_user_id=session["user_id"])

# ─── Mini Leagues ─────────────────────────────────────────────

def generate_league_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

@app.route("/leagues")
def leagues():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user_leagues = db.session.query(League).join(
        LeagueMember, League.id == LeagueMember.league_id
    ).filter(LeagueMember.user_id == session["user_id"]).all()
    return render_template("leagues.html", leagues=user_leagues,
                           username=session["username"])

@app.route("/create-league", methods=["POST"])
def create_league():
    if "user_id" not in session:
        return redirect(url_for("login"))
    name = request.form["league_name"]
    code = generate_league_code()
    league = League(name=name, manager_id=session["user_id"], league_code=code)
    db.session.add(league)
    db.session.flush()
    member = LeagueMember(league_id=league.id, user_id=session["user_id"])
    db.session.add(member)
    db.session.commit()
    flash(f"League created! Your league code is: {code}", "success")
    return redirect(url_for("leagues"))

@app.route("/join-league", methods=["POST"])
def join_league():
    if "user_id" not in session:
        return redirect(url_for("login"))
    code = request.form["league_code"].strip().upper()
    league = League.query.filter_by(league_code=code).first()
    if not league:
        flash("Invalid league code!", "error")
        return redirect(url_for("leagues"))
    already = LeagueMember.query.filter_by(
        league_id=league.id, user_id=session["user_id"]).first()
    if already:
        flash("You are already in this league!", "error")
        return redirect(url_for("leagues"))
    member = LeagueMember(league_id=league.id, user_id=session["user_id"])
    db.session.add(member)
    db.session.commit()
    flash(f"Joined league: {league.name}!", "success")
    return redirect(url_for("leagues"))

@app.route("/league/<int:league_id>")
def league_detail(league_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    league = League.query.get(league_id)
    members = db.session.query(User).join(
        LeagueMember, User.id == LeagueMember.user_id
    ).filter(LeagueMember.league_id == league_id).order_by(User.total_points.desc()).all()
    return render_template("league_detail.html", league=league,
                           members=members, current_user_id=session["user_id"])

# ─── Scoring ─────────────────────────────────────────────────

@app.route("/process-match/<int:match_id>")
def process_match(match_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    # Snapshot all user teams for this match before processing
    snapshot_teams_for_match(match_id)
    success = process_match_points(match_id)
    if success:
        flash("Match points calculated successfully!", "success")
    else:
        flash("Failed to process match. Check API or match status.", "error")
    return redirect(url_for("matches"))

def snapshot_teams_for_match(match_id):
    """Save a snapshot of every user's current team for this match."""
    all_users = User.query.all()
    for user in all_users:
        team = UserTeam.query.filter_by(user_id=user.id).first()
        if not team:
            continue
        existing = UserMatchTeam.query.filter_by(
            user_id=user.id, match_id=match_id).first()
        if not existing:
            snapshot = UserMatchTeam(
                user_id=user.id,
                match_id=match_id,
                player_ids=team.player_ids,
                captain_id=team.captain_id,
                vice_captain_id=team.vice_captain_id
            )
            db.session.add(snapshot)
    db.session.commit()

@app.route("/my-points")
def my_points():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = User.query.get(session["user_id"])
    match_scores = db.session.query(UserMatchTeam, Match).join(
        Match, UserMatchTeam.match_id == Match.id
    ).filter(UserMatchTeam.user_id == user.id).order_by(Match.match_date.desc()).all()
    return render_template("my_points.html", user=user, match_scores=match_scores)

# ─── Admin Panel ─────────────────────────────────────────────
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        user = User.query.get(session["user_id"])
        if not user or not user.is_admin:
            flash("Admin access required!", "error")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated

@app.route("/admin")
@admin_required
def admin():
    matches = Match.query.order_by(Match.match_date).all()
    return render_template("admin.html", matches=matches)

@app.route("/admin/match/<int:match_id>", methods=["GET", "POST"])
@admin_required
def admin_match(match_id):
    match = Match.query.get(match_id)
    # Get players from both teams
    players = Player.query.filter(
        (Player.ipl_team == match.team1) |
        (Player.ipl_team == match.team2)
    ).order_by(Player.ipl_team, Player.role).all()

    # Get existing stats if any
    existing_stats = {}
    for stat in PlayerMatchStats.query.filter_by(match_id=match_id).all():
        existing_stats[stat.player_id] = stat

    if request.method == "POST":
        # Update match status
        new_status = request.form.get("match_status")
        if new_status:
            match.status = new_status

        # Save player stats
        for player in players:
            did_play = request.form.get(f"did_play_{player.id}") == "on"
            runs = int(request.form.get(f"runs_{player.id}", 0) or 0)
            balls_faced = int(request.form.get(f"balls_faced_{player.id}", 0) or 0)
            fours = int(request.form.get(f"fours_{player.id}", 0) or 0)
            sixes = int(request.form.get(f"sixes_{player.id}", 0) or 0)
            wickets = int(request.form.get(f"wickets_{player.id}", 0) or 0)
            overs_bowled = float(request.form.get(f"overs_bowled_{player.id}", 0) or 0)
            runs_conceded = int(request.form.get(f"runs_conceded_{player.id}", 0) or 0)
            maidens = int(request.form.get(f"maidens_{player.id}", 0) or 0)
            catches = int(request.form.get(f"catches_{player.id}", 0) or 0)
            stumpings = int(request.form.get(f"stumpings_{player.id}", 0) or 0)
            run_outs = int(request.form.get(f"run_outs_{player.id}", 0) or 0)
            is_motm = request.form.get(f"is_motm_{player.id}") == "on"
            is_winner = request.form.get(f"is_winner_{player.id}") == "on"
            
            if not did_play:
                continue

            stats_dict = {
                "runs": runs, "balls_faced": balls_faced,
                "fours": fours, "sixes": sixes,
                "wickets": wickets, "overs_bowled": overs_bowled,
                "runs_conceded": runs_conceded, "maidens": maidens,
                "catches": catches, "stumpings": stumpings,
                "run_outs": run_outs, "did_play": did_play,
                "is_motm": is_motm, "is_winner": is_winner,
                "role": player.role
            }
            pts = calculate_points(stats_dict)

            stat = existing_stats.get(player.id)
            if stat:
                stat.runs = runs; stat.balls_faced = balls_faced
                stat.fours = fours; stat.sixes = sixes
                stat.wickets = wickets; stat.overs_bowled = overs_bowled
                stat.runs_conceded = runs_conceded; stat.maidens = maidens
                stat.catches = catches; stat.stumpings = stumpings
                stat.run_outs = run_outs; stat.did_play = did_play
                stat.is_motm = is_motm; stat.is_winner = is_winner
                stat.points_earned = pts
            else:
                stat = PlayerMatchStats(
                    player_id=player.id, match_id=match_id,
                    runs=runs, balls_faced=balls_faced,
                    fours=fours, sixes=sixes,
                    wickets=wickets, overs_bowled=overs_bowled,
                    runs_conceded=runs_conceded, maidens=maidens,
                    catches=catches, stumpings=stumpings,
                    run_outs=run_outs, did_play=did_play,
                    is_motm=is_motm, is_winner=is_winner,
                    points_earned=pts
                )
                db.session.add(stat)
        db.session.commit()

        # If match completed, calculate user points
        if new_status == "completed":
            snapshot_teams_for_match(match_id)
            # Recalculate all user points for this match
            all_stats = PlayerMatchStats.query.filter_by(match_id=match_id).all()
            match_player_points = {s.player_id: s.points_earned for s in all_stats}
            user_teams = UserMatchTeam.query.filter_by(match_id=match_id).all()
            for ut in user_teams:
                pid_list = [int(x) for x in ut.player_ids.split(",")]
                total = 0
                for pid in pid_list:
                    pts = match_player_points.get(pid, 0)
                    if pid == ut.captain_id:
                        pts *= 2
                    elif pid == ut.vice_captain_id:
                        pts *= 1.5
                    total += pts
                # Remove old points if recalculating
                old_points = ut.points_scored
                ut.points_scored = total
                user = User.query.get(ut.user_id)
                if user:
                    user.total_points = user.total_points - old_points + total
            db.session.commit()
            flash(f"Match {match.match_number} stats saved & points calculated!", "success")
        else:
            flash("Stats saved successfully!", "success")

        return redirect(url_for("admin_match", match_id=match_id))

    return render_template("admin_match.html", match=match,
                           players=players, existing_stats=existing_stats)

@app.route("/transfers")
def transfers():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = User.query.get(session["user_id"])

    # Get all transfer history with player and match details
    history = db.session.query(
        TransferHistory, Player, Match
    ).join(
        Player, TransferHistory.player_in_id == Player.id
    ).join(
        Match, TransferHistory.window_match_id == Match.id
    ).filter(
        TransferHistory.user_id == user.id
    ).order_by(TransferHistory.transferred_at.desc()).all()

    # Group by window
    windows = {}
    for transfer, player_in, match in history:
        player_out = Player.query.get(transfer.player_out_id)
        key = match.id
        if key not in windows:
            windows[key] = {
                "match": match,
                "transfers": []
            }
        windows[key]["transfers"].append({
            "player_in": player_in,
            "player_out": player_out,
            "transferred_at": transfer.transferred_at
        })

    return render_template("transfers.html", user=user,
                           windows=windows.values())

@app.route("/players")
def player_stats():
    if "user_id" not in session:
        return redirect(url_for("login"))

    players = Player.query.filter_by(is_active=True).order_by(Player.ipl_team).all()
    
    # Get current user's team
    user_team = UserTeam.query.filter_by(user_id=session["user_id"]).first()
    my_player_ids = set()
    if user_team:
        my_player_ids = set(int(x) for x in user_team.player_ids.split(",") if x.strip())

# Aggregate season stats for each player
    player_data = []
    for player in players:
        stats = PlayerMatchStats.query.filter_by(player_id=player.id).all()
        total_runs = sum(s.runs for s in stats)
        total_wickets = sum(s.wickets for s in stats)
        total_catches = sum(s.catches for s in stats)
        total_sixes = sum(s.sixes for s in stats)
        total_fours = sum(s.fours for s in stats)
        total_points = sum(s.points_earned for s in stats)
        matches_played = len([s for s in stats if s.did_play])

        player_data.append({
            "player": player,
            "matches": matches_played,
            "runs": total_runs,
            "fours": total_fours,
            "sixes": total_sixes,
            "wickets": total_wickets,
            "catches": total_catches,
            "points": total_points
        })

    # Sort by points descending
    player_data.sort(key=lambda x: x["points"], reverse=True)

    return render_template("player_stats.html", player_data=player_data, my_player_ids=my_player_ids)
@app.route("/league/<int:league_id>/compare/<int:opponent_id>")
def compare_teams(league_id, opponent_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])
    opponent = User.query.get(opponent_id)
    league = League.query.get(league_id)

    # Verify both users are in the league
    user_member = LeagueMember.query.filter_by(
        league_id=league_id, user_id=user.id).first()
    opponent_member = LeagueMember.query.filter_by(
        league_id=league_id, user_id=opponent_id).first()
    if not user_member or not opponent_member:
        flash("Both users must be in the league!", "error")
        return redirect(url_for("league_detail", league_id=league_id))

    # Get all completed matches
    completed_matches = Match.query.filter_by(
        status="completed").order_by(Match.match_date.desc()).all()

    # Get match scores for both users
    match_data = []
    user_total = 0
    opponent_total = 0
    user_best = 0
    opponent_best = 0

    for match in completed_matches:
        user_score = UserMatchTeam.query.filter_by(
            user_id=user.id, match_id=match.id).first()
        opponent_score = UserMatchTeam.query.filter_by(
            user_id=opponent_id, match_id=match.id).first()

        user_pts = user_score.points_scored if user_score else 0
        opponent_pts = opponent_score.points_scored if opponent_score else 0

        user_total += user_pts
        opponent_total += opponent_pts
        user_best = max(user_best, user_pts)
        opponent_best = max(opponent_best, opponent_pts)

        # Get user's team for this match
        user_players = []
        if user_score:
            pid_list = [int(x) for x in user_score.player_ids.split(",") if x.strip()]
            user_players = Player.query.filter(Player.id.in_(pid_list)).all()

        # Get opponent's team for this match
        opponent_players = []
        if opponent_score:
            pid_list = [int(x) for x in opponent_score.player_ids.split(",") if x.strip()]
            opponent_players = Player.query.filter(Player.id.in_(pid_list)).all()

        # Get player points for this match
        player_points = {}
        stats = PlayerMatchStats.query.filter_by(match_id=match.id).all()
        for s in stats:
            player_points[s.player_id] = s.points_earned

        match_data.append({
            "match": match,
            "user_pts": user_pts,
            "opponent_pts": opponent_pts,
            "winner": "user" if user_pts > opponent_pts else
                      "opponent" if opponent_pts > user_pts else "draw",
            "user_players": user_players,
            "opponent_players": opponent_players,
            "player_points": player_points,
            "user_captain_id": user_score.captain_id if user_score else None,
            "user_vc_id": user_score.vice_captain_id if user_score else None,
            "opponent_captain_id": opponent_score.captain_id if opponent_score else None,
            "opponent_vc_id": opponent_score.vice_captain_id if opponent_score else None,
        })

    # Head to head record
    user_wins = sum(1 for m in match_data if m["winner"] == "user")
    opponent_wins = sum(1 for m in match_data if m["winner"] == "opponent")
    draws = sum(1 for m in match_data if m["winner"] == "draw")

    return render_template("compare_teams.html",
                           user=user, opponent=opponent,
                           league=league, match_data=match_data,
                           user_total=user_total,
                           opponent_total=opponent_total,
                           user_best=user_best,
                           opponent_best=opponent_best,
                           user_wins=user_wins,
                           opponent_wins=opponent_wins,
                           draws=draws)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")