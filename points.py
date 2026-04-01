from scoring_config import SCORING_CONFIG

def calculate_points(stats):
    c = SCORING_CONFIG
    points = 0

    # ── Playing & Match Bonus ──────────────────────────────────
    if stats.get("did_play"):
        points += c["playing_bonus"]
    if stats.get("is_motm"):
        points += c["motm"]
    if stats.get("is_winner"):
        points += c["winning_team"]

    # ── Batting ───────────────────────────────────────────────
    runs = stats.get("runs", 0)
    points += runs * c["run"]
    points += stats.get("fours", 0) * c["four_bonus"]
    points += stats.get("sixes", 0) * c["six_bonus"]

    # Duck penalty
    if runs == 0 and stats.get("did_play") and \
       stats.get("role") in ["batsman", "keeper", "allrounder"]:
        points += c["duck"]

    # Batting milestones (cumulative — each threshold adds on top)
    if runs >= 125: points += c["milestone_125"]
    elif runs >= 105: points += c["milestone_105"]
    elif runs >= 80: points += c["milestone_80"]
    elif runs >= 60: points += c["milestone_60"]
    elif runs >= 40: points += c["milestone_40"]
    elif runs >= 25: points += c["milestone_25"]

    # Batting strike rate
    balls_faced = stats.get("balls_faced", 0)
    if stats.get("role") in c["sr_applicable_roles"]:
        qualifies = balls_faced >= c["sr_min_balls"] or runs >= c["sr_min_runs"]
        if qualifies and balls_faced > 0:
            sr = (runs / balls_faced) * 100
            if sr > 200:
                points += c["sr_above_200"]
            elif sr > 160:
                points += c["sr_160_200"]
            elif sr > 130:
                points += c["sr_130_160"]
            elif sr > 100:
                points += c["sr_100_130"]
            else:
                points += c["sr_below_100"]

    # ── Bowling ───────────────────────────────────────────────
    wickets = stats.get("wickets", 0)
    points += wickets * c["wicket"]
    points += stats.get("maidens", 0) * c["maiden"]
    points += stats.get("wides", 0) * c["wide"]
    points += stats.get("no_balls", 0) * c["no_ball"]

    # Bowling milestones
    if wickets >= 6:   points += c["wicket_milestone_6"]
    elif wickets >= 5: points += c["wicket_milestone_5"]
    elif wickets >= 4: points += c["wicket_milestone_4"]
    elif wickets >= 3: points += c["wicket_milestone_3"]
    elif wickets >= 2: points += c["wicket_milestone_2"]

    # Bowling economy
    overs = stats.get("overs_bowled", 0)
    runs_conceded = stats.get("runs_conceded", 0)
    if overs >= c["economy_min_overs"] and \
       stats.get("role") in c["economy_applicable_roles"]:
        eco = runs_conceded / overs
        if eco <= 3:    points += c["economy_below_3"]
        elif eco <= 5:  points += c["economy_3_5"]
        elif eco <= 7:  points += c["economy_5_7"]
        elif eco <= 9:  points += c["economy_7_9"]
        elif eco <= 11: points += c["economy_9_11"]
        elif eco <= 13: points += c["economy_11_13"]
        else:           points += c["economy_above_13"]

    # ── Fielding ──────────────────────────────────────────────
    points += stats.get("catches", 0) * c["catch"]
    points += stats.get("stumpings", 0) * c["stumping"]
    points += stats.get("run_outs", 0) * c["run_out"]

    return round(points, 1)