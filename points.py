from scoring_config import SCORING_CONFIG

def calculate_points(stats):
    c = SCORING_CONFIG
    points = 0

    # ── Basic Batting ──────────────────────────
    runs = stats.get("runs", 0)
    points += runs * c["run"]
    points += stats.get("fours", 0) * c["four_bonus"]
    points += stats.get("sixes", 0) * c["six_bonus"]

    # ── Batting Milestones ─────────────────────
    if runs >= 100:
        points += c["century"]
    elif runs >= 75:
        points += c["seventy_five"]
    elif runs >= 50:
        points += c["half_century"]
    elif runs >= 25:
        points += c["twenty_five"]

    # ── Batting Strike Rate ────────────────────
    balls_faced = stats.get("balls_faced", 0)
    if balls_faced >= c["sr_min_balls"] and stats.get("role") in c["sr_applicable_roles"]:
        sr = (runs / balls_faced) * 100
        if sr > 170:
            points += c["sr_above_170"]
        elif sr >= 150:
            points += c["sr_150_170"]
        elif sr >= 130:
            points += c["sr_130_150"]
        elif sr >= 60 and sr < 70:
            points += c["sr_60_70"]
        elif sr >= 50 and sr < 60:
            points += c["sr_50_60"]
        elif sr < 50:
            points += c["sr_below_50"]

    # ── Duck Penalty ───────────────────────────
    if runs == 0 and stats.get("did_play") and \
       stats.get("role") in ["sr_applicable_roles"]:
        points += c["duck"]

    # ── Basic Bowling ──────────────────────────
    wickets = stats.get("wickets", 0)
    points += wickets * c["wicket"]
    points += stats.get("maidens", 0) * c["maiden"]

    # ── Bowling Milestones ─────────────────────
    if wickets >= 5:
        points += c["five_wickets"]
    elif wickets >= 4:
        points += c["four_wickets"]
    elif wickets >= 3:
        points += c["three_wickets"]

    # ── Bowling Economy ────────────────────────
    overs_bowled = stats.get("overs_bowled", 0)
    runs_conceded = stats.get("runs_conceded", 0)
    if overs_bowled >= c["economy_min_overs"] and stats.get("role") in c["economy_applicable_roles"]:
        economy = runs_conceded / overs_bowled
        if economy < 5:
            points += c["economy_below_5"]
        elif economy < 6:
            points += c["economy_5_6"]
        elif economy < 7:
            points += c["economy_6_7"]
        elif economy >= 10 and economy < 11:
            points += c["economy_10_11"]
        elif economy >= 11 and economy < 12:
            points += c["economy_11_12"]
        elif economy >= 12:
            points += c["economy_above_12"]

    # ── Fielding ───────────────────────────────
    points += stats.get("catches", 0) * c["catch"]
    points += stats.get("stumpings", 0) * c["stumping"]
    points += stats.get("run_outs", 0) * c["run_out"]

    # ── Bonus Points ───────────────────────────
    if stats.get("did_play"):
        points += c["playing_bonus"]
    if stats.get("is_motm"):
        points += c["motm"]
    if stats.get("is_winner"):
        points += c["winning_team"]

    return points