from cricapi import get_match_scorecard
from database import db, Match, Player, PlayerMatchStats, UserMatchTeam, User
from points import calculate_points

def extract_player_stats(scorecard_data):
    """Extract player stats from CricAPI scorecard response."""
    stats = {}
    try:
        innings_list = scorecard_data.get("data", {}).get("scorecard", [])
        for innings in innings_list:
            # Batting stats
            for batter in innings.get("batting", []):
                name = batter.get("batsman", {}).get("name", "")
                if not name:
                    continue
                if name not in stats:
                    stats[name] = {"runs": 0, "fours": 0, "sixes": 0,
                                   "wickets": 0, "maidens": 0, "catches": 0,
                                   "stumpings": 0, "run_outs": 0, "did_play": True}
                stats[name]["runs"] += int(batter.get("r", 0) or 0)
                stats[name]["fours"] += int(batter.get("4s", 0) or 0)
                stats[name]["sixes"] += int(batter.get("6s", 0) or 0)
                stats[name]["did_play"] = True

            # Bowling stats
            for bowler in innings.get("bowling", []):
                name = bowler.get("bowler", {}).get("name", "")
                if not name:
                    continue
                if name not in stats:
                    stats[name] = {"runs": 0, "fours": 0, "sixes": 0,
                                   "wickets": 0, "maidens": 0, "catches": 0,
                                   "stumpings": 0, "run_outs": 0, "did_play": True}
                stats[name]["wickets"] += int(bowler.get("w", 0) or 0)
                stats[name]["maidens"] += int(bowler.get("m", 0) or 0)
                stats[name]["did_play"] = True

            # Fielding stats (from wickets)
            for batter in innings.get("batting", []):
                dismissal = batter.get("dismissal", "")
                fielder = batter.get("fielders", {})
                fielder_name = fielder.get("name", "") if isinstance(fielder, dict) else ""
                if not fielder_name:
                    continue
                if fielder_name not in stats:
                    stats[fielder_name] = {"runs": 0, "fours": 0, "sixes": 0,
                                           "wickets": 0, "maidens": 0, "catches": 0,
                                           "stumpings": 0, "run_outs": 0, "did_play": True}
                if "caught" in dismissal.lower():
                    stats[fielder_name]["catches"] += 1
                elif "stumped" in dismissal.lower():
                    stats[fielder_name]["stumpings"] += 1
                elif "run out" in dismissal.lower():
                    stats[fielder_name]["run_outs"] += 1

    except Exception as e:
        print(f"Error extracting stats: {e}")
    return stats

def process_match_points(match_id):
    """Fetch scorecard, calculate points, update all user scores."""
    match = Match.query.get(match_id)
    if not match or not match.cricapi_match_id:
        print(f"❌ Match {match_id} not found or no API ID")
        return False

    print(f"🔄 Fetching scorecard for Match {match.match_number}...")
    scorecard = get_match_scorecard(match.cricapi_match_id)
    if not scorecard or scorecard.get("status") != "success":
        print(f"❌ Failed to fetch scorecard: {scorecard}")
        return False

    # Extract stats from scorecard
    player_stats = extract_player_stats(scorecard)
    print(f"📊 Found stats for {len(player_stats)} players")

    # Match players to our database by name
    all_players = Player.query.all()
    player_map = {p.name.lower(): p for p in all_players}

    # Save player stats and calculate points
    match_player_points = {}
    for player_name, stats in player_stats.items():
        player = player_map.get(player_name.lower())
        if not player:
            # Try partial name match
            for db_name, db_player in player_map.items():
                if player_name.lower() in db_name or db_name in player_name.lower():
                    player = db_player
                    break

        if not player:
            print(f"⚠️  Player not found in DB: {player_name}")
            continue

        # Check if stats already exist
        existing = PlayerMatchStats.query.filter_by(
            player_id=player.id, match_id=match_id).first()
        if existing:
            continue

        stats["role"] = player.role
        pts = calculate_points(stats)

        stat_record = PlayerMatchStats(
            player_id=player.id,
            match_id=match_id,
            runs=stats.get("runs", 0),
            fours=stats.get("fours", 0),
            sixes=stats.get("sixes", 0),
            wickets=stats.get("wickets", 0),
            catches=stats.get("catches", 0),
            stumpings=stats.get("stumpings", 0),
            maidens=stats.get("maidens", 0),
            run_outs=stats.get("run_outs", 0),
            did_play=stats.get("did_play", False),
            points_earned=pts
        )
        db.session.add(stat_record)
        match_player_points[player.id] = pts
        print(f"✅ {player.name}: {pts} points")

    db.session.commit()

    # Update user points based on their team snapshot
    user_teams = UserMatchTeam.query.filter_by(match_id=match_id).all()
    for user_team in user_teams:
        player_ids = [int(x) for x in user_team.player_ids.split(",")]
        total = 0
        for pid in player_ids:
            pts = match_player_points.get(pid, 0)
            if pid == user_team.captain_id:
                pts *= 2
            elif pid == user_team.vice_captain_id:
                pts *= 1.5
            total += pts
        user_team.points_scored = total
        user = User.query.get(user_team.user_id)
        if user:
            user.total_points += total
        print(f"👤 User {user_team.user_id}: +{total} points")

    # Mark match as completed
    match.status = "completed"
    db.session.commit()
    print(f"🏏 Match {match.match_number} processing complete!")
    return True
