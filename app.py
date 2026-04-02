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
from scheduler import start_scheduler
from scoring_config import SCORING_CONFIG
from points_engine import save_player_stats, recalculate_user_points
from scraper import fetch_cricapi_scorecard

from werkzeug.security import generate_password_hash, check_password_hash
from points import calculate_points
from datetime import datetime, timezone
def utcnow():
    return datetime.now(timezone.utc)

from scoring import process_match_points
# from cricapi import get_match_info
from database import db, User, Player, Match, UserTeam, UserMatchTeam, PlayerMatchStats, League, LeagueMember, TransferWindow, TransferHistory

import io
import random
import string


app = Flask(__name__)
import os

app.secret_key = os.environ.get("SECRET_KEY", "fantasy-ipl-secret-key")

# Use PostgreSQL if DATABASE_URL is set, otherwise fall back to SQLite
database_url = os.environ.get("DATABASE_URL")
if database_url:
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///fantasy_ipl.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

#import os
#app.secret_key = os.environ.get("SECRET_KEY", "fantasy-ipl-secret-key")

#app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///fantasy_ipl.db"
#app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    db.create_all()
    
    # Start background scheduler
    scheduler = start_scheduler(app)
    
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
    # Convert match time to UTC timestamp for accurate countdown
    next_match_utc_timestamp = None
    if next_match:
        from datetime import timezone, timedelta
        # match_date is stored as IST naive datetime
        # Attach IST timezone then convert to UTC timestamp
        ist = timezone(timedelta(hours=5, minutes=30))
        match_ist = next_match.match_date.replace(tzinfo=ist)
        next_match_utc_timestamp = int(match_ist.timestamp() * 1000)



    return render_template("dashboard.html", user=user,
                           upcoming_matches=upcoming_matches,
                           live_matches=live_matches,
                           players=players,
                           user_team=user_team,
                           next_match=next_match,
                           next_match_utc_timestamp=next_match_utc_timestamp)

# ─── Team Selection ───────────────────────────────────────────
@app.route("/select-team")
def select_team():
    if "user_id" not in session:
        return redirect(url_for("login"))
    players = Player.query.filter_by(is_active=True).all()
    user = User.query.get(session["user_id"])
    existing_team = UserTeam.query.filter_by(user_id=user.id).first()
    selected_ids = []
    captain_id = None
    vc_id = None
    if existing_team:
        selected_ids = [int(x) for x in existing_team.player_ids.split(",")]
        captain_id = existing_team.captain_id
        vc_id = existing_team.vice_captain_id

    any_match_started = Match.query.filter(
        Match.status.in_(["live", "completed"])
    ).first()
    next_match = Match.query.filter_by(status="upcoming").order_by(Match.match_date).first()
    next_match_teams = []
    if next_match:
        next_match_teams = [next_match.team1, next_match.team2]

# Get season points per player
    from database import PlayerMatchStats
    player_points = {}
    for player in players:
        stats = PlayerMatchStats.query.filter_by(player_id=player.id).all()
        player_points[player.id] = round(sum(s.points_earned for s in stats), 1)

    # sSort players:
    selected_set = set(selected_ids)

    players.sort(key=lambda p: (
        0 if p.id in selected_set else 1,     # Selected first
        -player_points.get(p.id, 0),          # Highest points first
        -p.credits                             # Highest credits first
    ))

    # Team formation rules
    from scoring_config import SCORING_CONFIG
    rules = {
        "team_size": SCORING_CONFIG["team_size"],
        "max_overseas": SCORING_CONFIG["max_overseas"],
        "min_batsmen": SCORING_CONFIG["min_batsmen"],
        "max_batsmen": SCORING_CONFIG["max_batsmen"],
        "min_bowlers": SCORING_CONFIG["min_bowlers"],
        "max_bowlers": SCORING_CONFIG["max_bowlers"],
        "min_allrounders": SCORING_CONFIG["min_allrounders"],
        "max_allrounders": SCORING_CONFIG["max_allrounders"],
        "min_keepers": SCORING_CONFIG["min_keepers"],
        "max_keepers": SCORING_CONFIG["max_keepers"],
        "max_players_per_team": SCORING_CONFIG["max_players_per_team"],
    }

    return render_template("team_select.html", players=players,
                           user=user, selected_ids=selected_ids,
                           captain_id=captain_id, vc_id=vc_id,
                           any_match_started=any_match_started,
                           next_match=next_match,
                           next_match_teams=next_match_teams,
                           player_points=player_points,
                           rules=rules)

@app.route("/save-team", methods=["POST"])
@app.route("/save-team", methods=["POST"])
def save_team():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not logged in"})

    data = request.get_json()
    user = User.query.get(session["user_id"])
    new_ids = set(int(x) for x in data["player_ids"])

    # Get current team
    old_team = UserTeam.query.filter_by(user_id=user.id).first()
    old_ids = set(
        int(x) for x in old_team.player_ids.split(",") if x.strip()
    ) if old_team else set()
    is_first_selection = old_team is None

    # ── Determine current window ───────────────────────────────
    last_match = Match.query.filter(
        Match.status.in_(["live", "completed"])
    ).order_by(Match.match_date.desc()).first()
    window_match_id = last_match.id if last_match else 0

    # Get or create window for current match
    current_window = TransferWindow.query.filter_by(
        user_id=user.id,
        window_start_match=window_match_id
    ).first()
    if not current_window:
        team = old_team
        baseline = team.player_ids if (team and team.player_ids) else \
                   ",".join(str(x) for x in data["player_ids"])
        current_window = TransferWindow(
            user_id=user.id,
            window_start_match=window_match_id,
            baseline_player_ids=baseline,
            transfers_used=0
        )
        db.session.add(current_window)
        db.session.flush()  # get the id without committing

    # ── Record first window for this user ──────────────────────
    if user.first_transfer_window_id is None:
        user.first_transfer_window_id = current_window.id

    # ── Free period = still in their very first window ─────────
    in_free_period = (current_window.id == user.first_transfer_window_id)

    new_player_ids_str = ",".join(str(x) for x in data["player_ids"])

    if is_first_selection or in_free_period:
        # Save team freely
        if old_team:
            old_team.player_ids = new_player_ids_str
            old_team.captain_id = data["captain_id"]
            old_team.vice_captain_id = data["vice_captain_id"]
            old_team.last_updated = utcnow()
        else:
            new_team = UserTeam(
                user_id=user.id,
                player_ids=new_player_ids_str,
                captain_id=data["captain_id"],
                vice_captain_id=data["vice_captain_id"]
            )
            db.session.add(new_team)

        # Keep baseline in sync with latest free save
        current_window.baseline_player_ids = new_player_ids_str
        current_window.transfers_used = 0

        db.session.commit()
        return jsonify({
            "success": True,
            "transfers_remaining": user.transfers_remaining,
            "window_transfers_used": 0,
            "message": "Free period — no transfers used"
        })

    # ── Paid window: enforce transfer limits ───────────────────
    baseline_ids = set(
        int(x) for x in current_window.baseline_player_ids.split(",")
        if x.strip()
    )

    net_transfers = len(new_ids - baseline_ids)
    previous_net  = len(old_ids - baseline_ids)
    delta         = net_transfers - previous_net

    additional_transfers = max(0, delta)
    refund               = max(0, -delta)

    print(f"DEBUG window={current_window.id} first_window={user.first_transfer_window_id} "
          f"net={net_transfers} prev={previous_net} delta={delta} "
          f"additional={additional_transfers} refund={refund}")

    if additional_transfers > user.transfers_remaining:
        return jsonify({
            "success": False,
            "message": f"Not enough transfers! Need {additional_transfers} "
                       f"but only {user.transfers_remaining} remaining."
        })

    # ── Log transfers ─────────────────────────────────────────
    if delta > 0:
        newly_added   = (new_ids - baseline_ids) - (old_ids - baseline_ids)
        newly_removed = (old_ids - baseline_ids) - (new_ids - baseline_ids)
        for player_in_id, player_out_id in zip(
            sorted(newly_added), sorted(newly_removed)
        ):
            db.session.add(TransferHistory(
                user_id=user.id,
                window_match_id=current_window.window_start_match,
                player_in_id=player_in_id,
                player_out_id=player_out_id,
                transferred_at=utcnow()
            ))

    # ── Apply ─────────────────────────────────────────────────
    user.transfers_remaining -= additional_transfers
    user.transfers_remaining += refund
    from scoring_config import SCORING_CONFIG
    user.transfers_remaining = min(
        user.transfers_remaining,
        SCORING_CONFIG["season_transfers"]
    )
    current_window.transfers_used = current_window.transfers_used + delta

    old_team.player_ids = new_player_ids_str
    old_team.captain_id = data["captain_id"]
    old_team.vice_captain_id = data["vice_captain_id"]
    old_team.last_updated = utcnow()

    db.session.commit()
    return jsonify({
        "success": True,
        "transfers_remaining": user.transfers_remaining,
        "window_transfers_used": current_window.transfers_used
    })

def get_or_create_transfer_window(user_id):
    from database import TransferWindow
    last_match = Match.query.filter(
        Match.status.in_(["live", "completed"])
    ).order_by(Match.match_date.desc()).first()
    window_match_id = last_match.id if last_match else 0

    window = TransferWindow.query.filter_by(
        user_id=user_id,
        window_start_match=window_match_id
    ).first()

    if not window:
        team = UserTeam.query.filter_by(user_id=user_id).first()
        baseline = team.player_ids if (team and team.player_ids) else ""

        # Safety check — baseline must have 11 players
        baseline_ids = [x for x in baseline.split(",") if x.strip()]
        if len(baseline_ids) != 11:
            print(f"⚠️ Warning: baseline has {len(baseline_ids)} players for user {user_id}")

        window = TransferWindow(
            user_id=user_id,
            window_start_match=window_match_id,
            baseline_player_ids=baseline,
            transfers_used=0
        )
        db.session.add(window)
        db.session.commit()
        print(f"✅ New transfer window created for user {user_id} "
              f"with {len(baseline_ids)} baseline players")
    else:
        # Fix corrupted baseline if found
        baseline_ids = [x for x in window.baseline_player_ids.split(",") if x.strip()]
        if len(baseline_ids) == 0:
            team = UserTeam.query.filter_by(user_id=user_id).first()
            if team and team.player_ids:
                window.baseline_player_ids = team.player_ids
                window.transfers_used = 0
                db.session.commit()
                print(f"🔧 Fixed empty baseline for user {user_id}")

    return window

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
    all_matches = Match.query.order_by(Match.match_date).all()
    live_matches = Match.query.filter_by(status="live").order_by(Match.match_date).all()
    completed_matches = Match.query.filter_by(status="completed").order_by(Match.match_date.desc()).all()
    return render_template("admin.html",
                           all_matches=all_matches,
                           live_matches=live_matches,
                           completed_matches=completed_matches)

@app.route("/admin/match/<int:match_id>", methods=["GET", "POST"])
@admin_required
def admin_match(match_id):
    match = Match.query.get(match_id)
    players = Player.query.filter(
        (Player.ipl_team == match.team1) |
        (Player.ipl_team == match.team2)
    ).order_by(Player.ipl_team, Player.role).all()

    existing_stats = {}
    for stat in PlayerMatchStats.query.filter_by(match_id=match_id).all():
        existing_stats[stat.player_id] = stat

    if request.method == "POST":
        action = request.form.get("action", "save")
        new_status = request.form.get("match_status")
        if new_status:
            match.status = new_status

        for player in players:
            # For recalculate — only process checked players
            if action == "recalculate":
                if request.form.get(f"recalc_{player.id}") != "on":
                    continue

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

            if not did_play and action == "save":
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

            save_player_stats(player, match_id, stats_dict, existing_stats)

        db.session.commit()

        # Recalculate user points whenever stats change
        if new_status == "completed" or action == "recalculate":
            recalculate_user_points(match_id, snapshot_teams_for_match)

        if action == "recalculate":
            flash("🔄 Selected players recalculated successfully!", "success")
        elif new_status == "completed":
            flash(f"✅ Match {match.match_number} completed & points calculated!", "success")
        else:
            flash("✅ Stats saved successfully!", "success")

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

    user_team = UserTeam.query.filter_by(user_id=session["user_id"]).first()
    my_player_ids = set()
    if user_team:
        my_player_ids = set(int(x) for x in user_team.player_ids.split(",") if x.strip())

    from scoring_config import SCORING_CONFIG as c

    player_data = []
    for player in players:
        stats = PlayerMatchStats.query.filter_by(player_id=player.id).all()
        total_points = sum(s.points_earned for s in stats)
        matches_played = len([s for s in stats if s.did_play])

        match_breakdown = []
        for s in stats:
            if not s.did_play:
                continue
            match = Match.query.get(s.match_id)
            if not match:
                continue

            # ── Playing & Match Bonus ──────────────────────────
            playing_pts = c["playing_bonus"]
            winning_pts = c["winning_team"] if s.is_winner else 0
            mom_pts     = c["motm"] if s.is_motm else 0

            # ── Batting ────────────────────────────────────────
            runs_pts   = s.runs * c["run"]
            fours_pts  = s.fours * c["four_bonus"]
            sixes_pts  = s.sixes * c["six_bonus"]
            duck_pts   = c["duck"] if (s.runs == 0 and
                         player.role in ["batsman", "keeper", "allrounder"]) else 0

            # Batting milestones
            milestone_pts = 0
            if s.runs >= 125:   milestone_pts = c["milestone_125"]
            elif s.runs >= 105: milestone_pts = c["milestone_105"]
            elif s.runs >= 80:  milestone_pts = c["milestone_80"]
            elif s.runs >= 60:  milestone_pts = c["milestone_60"]
            elif s.runs >= 40:  milestone_pts = c["milestone_40"]
            elif s.runs >= 25:  milestone_pts = c["milestone_25"]

            # Strike rate
            sr_pts = 0
            sr = None
            qualifies = (s.balls_faced >= c["sr_min_balls"] or
                         s.runs >= c["sr_min_runs"])
            if qualifies and s.balls_faced > 0 and \
               player.role in c["sr_applicable_roles"]:
                sr = round((s.runs / s.balls_faced) * 100, 1)
                if sr > 200:   sr_pts = c["sr_above_200"]
                elif sr > 160: sr_pts = c["sr_160_200"]
                elif sr > 130: sr_pts = c["sr_130_160"]
                elif sr > 100: sr_pts = c["sr_100_130"]
                else:          sr_pts = c["sr_below_100"]

            batting_pts = runs_pts + fours_pts + sixes_pts + \
                          milestone_pts + duck_pts + sr_pts

            # ── Bowling ────────────────────────────────────────
            wickets_pts = s.wickets * c["wicket"]
            maidens_pts = s.maidens * c["maiden"]
            dot_pts     = getattr(s, 'dot_balls', 0) * c["dot_ball"]
            wides_pts   = getattr(s, 'wides', 0) * c["wide"]
            nb_pts      = getattr(s, 'no_balls', 0) * c["no_ball"]

            # Bowling milestones
            bowling_milestone_pts = 0
            if s.wickets >= 6:   bowling_milestone_pts = c["wicket_milestone_6"]
            elif s.wickets >= 5: bowling_milestone_pts = c["wicket_milestone_5"]
            elif s.wickets >= 4: bowling_milestone_pts = c["wicket_milestone_4"]
            elif s.wickets >= 3: bowling_milestone_pts = c["wicket_milestone_3"]
            elif s.wickets >= 2: bowling_milestone_pts = c["wicket_milestone_2"]

            # Economy
            economy_pts = 0
            economy = None
            if s.overs_bowled >= c["economy_min_overs"] and \
               player.role in c["economy_applicable_roles"]:
                economy = round(s.runs_conceded / s.overs_bowled, 1)
                if economy <= 3:    economy_pts = c["economy_below_3"]
                elif economy <= 5:  economy_pts = c["economy_3_5"]
                elif economy <= 7:  economy_pts = c["economy_5_7"]
                elif economy <= 9:  economy_pts = c["economy_7_9"]
                elif economy <= 11: economy_pts = c["economy_9_11"]
                elif economy <= 13: economy_pts = c["economy_11_13"]
                else:               economy_pts = c["economy_above_13"]

            bowling_pts = (wickets_pts + maidens_pts + dot_pts +
                           wides_pts + nb_pts +
                           bowling_milestone_pts + economy_pts)

            # ── Fielding ───────────────────────────────────────
            catches_pts   = s.catches * c["catch"]
            stumpings_pts = s.stumpings * c["stumping"]
            runouts_pts   = s.run_outs * c["run_out"]
            fielding_pts  = catches_pts + stumpings_pts + runouts_pts

            match_breakdown.append({
                "match": match,
                "total": round(s.points_earned, 1),
                # Playing & bonus
                "playing_pts": playing_pts,
                "winning_pts": winning_pts,
                "mom_pts": mom_pts,
                # Batting
                "batting_pts": round(batting_pts, 1),
                "runs": s.runs,
                "balls_faced": s.balls_faced,
                "fours": s.fours,
                "sixes": s.sixes,
                "runs_pts": runs_pts,
                "fours_pts": fours_pts,
                "sixes_pts": sixes_pts,
                "milestone_pts": milestone_pts,
                "duck_pts": duck_pts,
                "sr": sr,
                "sr_pts": sr_pts,
                # Bowling
                "bowling_pts": round(bowling_pts, 1),
                "wickets": s.wickets,
                "wickets_pts": wickets_pts,
                "maidens": s.maidens,
                "maidens_pts": maidens_pts,
                "dot_balls": getattr(s, 'dot_balls', 0),
                "dot_pts": dot_pts,
                "wides": getattr(s, 'wides', 0),
                "wides_pts": wides_pts,
                "no_balls": getattr(s, 'no_balls', 0),
                "nb_pts": nb_pts,
                "bowling_milestone_pts": bowling_milestone_pts,
                "economy": economy,
                "economy_pts": economy_pts,
                # Fielding
                "fielding_pts": round(fielding_pts, 1),
                "catches": s.catches,
                "catches_pts": catches_pts,
                "stumpings": s.stumpings,
                "stumpings_pts": stumpings_pts,
                "run_outs": s.run_outs,
                "runouts_pts": runouts_pts,
            })

        match_breakdown.sort(key=lambda x: x["match"].match_date, reverse=True)

        player_data.append({
            "player": player,
            "matches": matches_played,
            "points": round(total_points, 1),
            "match_breakdown": match_breakdown
        })

    player_data.sort(key=lambda x: x["points"], reverse=True)

    return render_template("player_stats.html", player_data=player_data,
                           my_player_ids=my_player_ids)

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

import csv
import io

@app.route("/admin/upload-csv", methods=["POST"])
@admin_required
def upload_csv():
    match_id = request.form.get("match_id")
    csv_file = request.files.get("csv_file")

    if not match_id or not csv_file:
        flash("Please select a match and upload a CSV file!", "error")
        return redirect(url_for("admin"))

    match = Match.query.get(match_id)
    if not match:
        flash("Match not found!", "error")
        return redirect(url_for("admin"))

    # Read CSV
    try:
        stream = io.StringIO(csv_file.stream.read().decode("utf-8"))
        reader = csv.DictReader(stream)
        # Strip whitespace from headers
        reader.fieldnames = [h.strip() for h in reader.fieldnames]
    except Exception as e:
        flash(f"Error reading CSV: {e}", "error")
        return redirect(url_for("admin"))

    # Get all players for name matching
    all_players = Player.query.all()
    player_map = {p.name.lower().strip(): p for p in all_players}

    success_count = 0
    not_found = []

    for row in reader:
        # Strip whitespace from all values
        row = {k.strip(): v.strip() for k, v in row.items()}
        player_name = row.get("player_name", "").lower().strip()

        # Find player in DB
        player = player_map.get(player_name)
        if not player:
            # Try partial match
            for db_name, db_player in player_map.items():
                if player_name in db_name or db_name in player_name:
                    player = db_player
                    break

        if not player:
            not_found.append(row.get("player_name", "Unknown"))
            continue

        # Parse stats
        stats_dict = {
            "runs": int(row.get("runs", 0) or 0),
            "balls_faced": int(row.get("balls_faced", 0) or 0),
            "fours": int(row.get("fours", 0) or 0),
            "sixes": int(row.get("sixes", 0) or 0),
            "wickets": int(row.get("wickets", 0) or 0),
            "overs_bowled": float(row.get("overs_bowled", 0) or 0),
            "runs_conceded": int(row.get("runs_conceded", 0) or 0),
            "maidens": int(row.get("maidens", 0) or 0),
            "wides": int(request.form.get(f"wides_{player.id}", 0)),
            "no_balls": int(request.form.get(f"no_balls_{player.id}", 0)),
            "dot_balls": int(request.form.get(f"dot_balls_{player.id}", 0)),
            "catches": int(row.get("catches", 0) or 0),
            "stumpings": int(row.get("stumpings", 0) or 0),
            "run_outs": int(row.get("run_outs", 0) or 0),
            "is_motm": row.get("is_motm", "0").strip() in ["1", "true", "True", "yes"],
            "is_winner": row.get("is_winner", "0").strip() in ["1", "true", "True", "yes"],
            "did_play": row.get("did_play", "0").strip() in ["1", "true", "True", "yes"],
            "role": player.role
        }

# Get existing stats for this player
        existing = {s.player_id: s for s in
                   PlayerMatchStats.query.filter_by(match_id=match.id).all()}
        save_player_stats(player, match.id, stats_dict, existing)
        success_count += 1

    db.session.commit()

    # Calculate user points and mark completed
    recalculate_user_points(match.id, snapshot_teams_for_match)
    match.status = "completed"
    db.session.commit()

    # Show results
    msg = f"✅ {success_count} players processed successfully!"
    if not_found:
        msg += f" ⚠️ Players not found: {', '.join(not_found)}"
    flash(msg, "success" if not not_found else "info")
    return redirect(url_for("admin"))


import atexit
atexit.register(lambda: scheduler.shutdown())
@app.route("/admin/scrape-scorecard", methods=["POST"])
@admin_required
def scrape_scorecard():
    match_id = request.form.get("match_id")
    if not match_id:
        flash("Please select a match!", "error")
        return redirect(url_for("admin"))

# Get the cricapi_match_id from the selected match
    match = Match.query.get(match_id)
    if not match or not match.cricapi_match_id:
        flash("This match has no CricAPI ID configured!", "error")
        return redirect(url_for("admin"))
    import os
    cache_file = os.path.join("scorecard_cache", f"{match.cricapi_match_id}.json")
    from_cache = os.path.exists(cache_file)
    csv_content, error = fetch_cricapi_scorecard(match.cricapi_match_id)
    
    # Store in session for scrape_preview to use
    session["from_cache"] = from_cache
    session["scrape_match_api_id"] = match.cricapi_match_id

    if error:
        flash(f"Scraping failed: {error}", "error")
        return redirect(url_for("admin"))

    # Store CSV in session temporarily and redirect to preview
    session["scraped_csv"] = csv_content
    session["scrape_match_id"] = match_id
    flash("✅ Scorecard scraped successfully! Review and confirm below.", "success")
    return redirect(url_for("scrape_preview"))

@app.route("/admin/scrape-preview")
@admin_required
def scrape_preview():
    csv_content = session.get("scraped_csv")
    match_id = session.get("scrape_match_id")

    if not csv_content or not match_id:
        flash("No scraped data found!", "error")
        return redirect(url_for("admin"))

    match = Match.query.get(match_id)

    # Parse CSV for preview
    import csv as csv_module
    reader = csv_module.DictReader(io.StringIO(csv_content))
    rows = list(reader)

    # Match players to our DB
    all_players = Player.query.all()
    player_map = {p.name.lower(): p for p in all_players}

    preview_data = []
    for row in rows:
        name = row["player_name"].strip()
        matched = player_map.get(name.lower())
        if not matched:
            # Try partial match
            for db_name, db_player in player_map.items():
                if name.lower() in db_name or db_name in name.lower():
                    matched = db_player
                    break
        preview_data.append({
            "row": row,
            "matched_player": matched,
            "name_in_csv": name
        })

    from_cache = session.pop("from_cache", False)
    match_api_id = session.pop("scrape_match_api_id", "")

    return render_template("scrape_preview.html",
                           match=match,
                           preview_data=preview_data,
                           from_cache=from_cache,
                           match_api_id=match_api_id)

@app.route("/admin/scrape-confirm", methods=["POST"])
@admin_required
def scrape_confirm():
    csv_content = session.get("scraped_csv")
    match_id = session.get("scrape_match_id")

    if not csv_content or not match_id:
        flash("No scraped data found!", "error")
        return redirect(url_for("admin"))

    # Use existing upload_csv logic by creating a fake file object
    import csv as csv_module
    match = Match.query.get(match_id)
    reader = csv_module.DictReader(io.StringIO(csv_content))
    reader.fieldnames = [h.strip() for h in reader.fieldnames]

    all_players = Player.query.all()
    player_map = {p.name.lower().strip(): p for p in all_players}

    success_count = 0
    not_found = []

    for row in reader:
        row = {k.strip(): v.strip() for k, v in row.items()}
        player_name = row.get("player_name", "").lower().strip()

        player = player_map.get(player_name)
        if not player:
            for db_name, db_player in player_map.items():
                if player_name in db_name or db_name in player_name:
                    player = db_player
                    break

        if not player:
            not_found.append(row.get("player_name", "Unknown"))
            continue
        
        motm_player = request.form.get("motm_player", "").strip().lower()
        is_motm = motm_player and (
            motm_player in player_name or player_name in motm_player)
        
        stats_dict = {
            "runs": int(row.get("runs", 0) or 0),
            "balls_faced": int(row.get("balls_faced", 0) or 0),
            "fours": int(row.get("fours", 0) or 0),
            "sixes": int(row.get("sixes", 0) or 0),
            "wickets": int(row.get("wickets", 0) or 0),
            "overs_bowled": float(row.get("overs_bowled", 0) or 0),
            "runs_conceded": int(row.get("runs_conceded", 0) or 0),
            "maidens": int(row.get("maidens", 0) or 0),
            "wides": int(row.get("wides", 0)),
            "no_balls": int(row.get("no_balls", 0)),
            "dot_balls": int(row.get("dot_balls", 0)),
            "catches": int(row.get("catches", 0) or 0),
            "stumpings": int(row.get("stumpings", 0) or 0),
            "run_outs": int(row.get("run_outs", 0) or 0),
                        "is_motm": is_motm,
            "is_winner": row.get("is_winner", "0") in ["1", "true", "True", "yes"],
            "did_play": row.get("did_play", "0") in ["1", "true", "True", "yes"],
            "role": player.role
        }

        existing = {s.player_id: s for s in
                   PlayerMatchStats.query.filter_by(match_id=match.id).all()}
        save_player_stats(player, match.id, stats_dict, existing)
        success_count += 1

    db.session.commit()
    recalculate_user_points(match.id, snapshot_teams_for_match)
    match.status = "completed"
    db.session.commit()

    # Clear session
    session.pop("scraped_csv", None)
    session.pop("scrape_match_id", None)

    msg = f"✅ {success_count} players imported successfully!"
    if not_found:
        msg += f" ⚠️ Not found: {', '.join(not_found)}"
    flash(msg, "success")
    return redirect(url_for("admin"))

@app.route("/admin/users")
@admin_required
def admin_users():
    users = User.query.order_by(User.username).all()
    return render_template("admin_users.html", users=users, 
                            current_user_id=session["user_id"])

@app.route("/admin/toggle-admin/<int:user_id>")
@admin_required
def toggle_admin(user_id):
    user = User.query.get(user_id)
    if user.id == session["user_id"]:
        flash("You cannot change your own admin status!", "error")
        return redirect(url_for("admin_users"))
    user.is_admin = not user.is_admin
    db.session.commit()
    status = "granted" if user.is_admin else "revoked"
    flash(f"Admin access {status} for {user.username}!", "success")
    return redirect(url_for("admin_users"))

@app.route("/admin/scoring", methods=["GET", "POST"])
@admin_required
def admin_scoring():
    from scoring_config import SCORING_CONFIG
    import json, os

    if request.method == "POST":
        new_config = {}
        # Fields to skip from form (keep existing values)
        skip_fields = ["preseason_transfers", "sr_applicable_roles", 
                       "economy_applicable_roles"]
        
        for key, value in SCORING_CONFIG.items():
            if key in skip_fields:
                new_config[key] = value
            elif isinstance(value, list):
                new_config[key] = value
            elif isinstance(value, bool) or value in (True, False):
                new_config[key] = value
            elif isinstance(value, int):
                try:
                    new_config[key] = int(request.form.get(key, value))
                except (ValueError, TypeError):
                    new_config[key] = value
            elif isinstance(value, float):
                try:
                    new_config[key] = float(request.form.get(key, value))
                except (ValueError, TypeError):
                    new_config[key] = value
            else:
                new_config[key] = request.form.get(key, value)

        # Write back to scoring_config.py
        config_path = os.path.join(os.path.dirname(__file__), "scoring_config.py")
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("# Fantasy IPL - Scoring Configuration\n")
            f.write("# Configurable via Admin UI\n\n")
            f.write("SCORING_CONFIG = ")
            f.write(repr(new_config))
            f.write("\n")

        flash("✅ Scoring rules updated successfully!", "success")
        return redirect(url_for("admin_scoring"))

    return render_template("admin_scoring.html", config=SCORING_CONFIG)

@app.route("/rules")
def rules():
    from scoring_config import SCORING_CONFIG as c
    return render_template("rules.html", c=c)

@app.route("/admin/clear-match-cache/<match_api_id>")
@admin_required
def clear_match_cache(match_api_id):
    import os
    cache_file = os.path.join("scorecard_cache", f"{match_api_id}.json")
    if os.path.exists(cache_file):
        os.remove(cache_file)
        flash("✅ Cache cleared! Re-fetch to get fresh data from CricAPI.", "success")
    else:
        flash("No cache found for this match.", "info")
    return redirect(url_for("admin"))

@app.route("/admin/clear-all-cache")
@admin_required
def clear_all_cache():
    import os, shutil
    cache_dir = "scorecard_cache"
    count = len(os.listdir(cache_dir)) if os.path.exists(cache_dir) else 0
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
    os.makedirs(cache_dir, exist_ok=True)
    flash(f"✅ Cleared {count} cached scorecard(s)!", "success")
    return redirect(url_for("admin"))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")