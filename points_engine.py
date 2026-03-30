from database import db, PlayerMatchStats, UserMatchTeam, User
from points import calculate_points
from scoring_config import SCORING_CONFIG

def save_player_stats(player, match_id, stats_dict, existing_stats):
    """Save or update stats for a single player and return points earned."""
    pts = calculate_points(stats_dict)
    stat = existing_stats.get(player.id)

    if stat:
        stat.runs = stats_dict["runs"]
        stat.balls_faced = stats_dict["balls_faced"]
        stat.fours = stats_dict["fours"]
        stat.sixes = stats_dict["sixes"]
        stat.wickets = stats_dict["wickets"]
        stat.overs_bowled = stats_dict["overs_bowled"]
        stat.runs_conceded = stats_dict["runs_conceded"]
        stat.maidens = stats_dict["maidens"]
        stat.catches = stats_dict["catches"]
        stat.stumpings = stats_dict["stumpings"]
        stat.run_outs = stats_dict["run_outs"]
        stat.did_play = stats_dict["did_play"]
        stat.is_motm = stats_dict["is_motm"]
        stat.is_winner = stats_dict["is_winner"]
        stat.points_earned = pts
    else:
        stat = PlayerMatchStats(
            player_id=player.id,
            match_id=match_id,
            runs=stats_dict["runs"],
            balls_faced=stats_dict["balls_faced"],
            fours=stats_dict["fours"],
            sixes=stats_dict["sixes"],
            wickets=stats_dict["wickets"],
            overs_bowled=stats_dict["overs_bowled"],
            runs_conceded=stats_dict["runs_conceded"],
            maidens=stats_dict["maidens"],
            catches=stats_dict["catches"],
            stumpings=stats_dict["stumpings"],
            run_outs=stats_dict["run_outs"],
            did_play=stats_dict["did_play"],
            is_motm=stats_dict["is_motm"],
            is_winner=stats_dict["is_winner"],
            points_earned=pts
        )
        db.session.add(stat)

    return pts

def recalculate_user_points(match_id, snapshot_fn):
    """Recalculate all user points for a given match."""
    snapshot_fn(match_id)

    all_stats = PlayerMatchStats.query.filter_by(match_id=match_id).all()
    match_player_points = {s.player_id: s.points_earned for s in all_stats}

    user_teams = UserMatchTeam.query.filter_by(match_id=match_id).all()
    for ut in user_teams:
        pid_list = [int(x) for x in ut.player_ids.split(",") if x.strip()]
        total = 0
        for pid in pid_list:
            pts = match_player_points.get(pid, 0)
            if pid == ut.captain_id:
                pts *= SCORING_CONFIG["captain_multiplier"]
            elif pid == ut.vice_captain_id:
                pts *= SCORING_CONFIG["vc_multiplier"]
            total += pts
        old_points = ut.points_scored
        ut.points_scored = round(total, 1)
        user = User.query.get(ut.user_id)
        if user:
            user.total_points = round(
                user.total_points - old_points + total, 1)

    db.session.commit()
    return len(user_teams)