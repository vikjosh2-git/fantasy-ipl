# ─────────────────────────────────────────────
# Fantasy IPL — Scoring Configuration
# Edit values here to adjust points system
# ─────────────────────────────────────────────


SCORING_CONFIG = {
    # ── Season Settings ────────────────────────
    "season_transfers": 150,        # Total transfers allowed per season
    "preseason_transfers": True,    # Allow unlimited transfers before first match

    # ── Basic Batting ──────────────────────────
    "run": 1,                # per run scored
    "four_bonus": 1,         # per boundary
    "six_bonus": 2,          # per six

    # ── Batting Milestones ─────────────────────
    "century": 16,           # 100+ runs
    "seventy_five": 8,        # 75-99 runs
    "half_century": 4,       # 50-74 runs
    "twenty_five": 2,        # 25-49 runs

# ── Batting Strike Rate ────────────────────
    # Minimum balls faced to qualify
    "sr_applicable_roles": ["batsman", "keeper", "allrounder"],
    "sr_min_balls": 10,
    "sr_above_170": 6,
    "sr_150_170": 4,
    "sr_130_150": 2,
    "sr_60_70": -2,
    "sr_50_60": -4,
    "sr_below_50": -6,

    # ── Duck Penalty ───────────────────────────
    # Applies to batsman, keeper, allrounder
    "duck": -2,

    # ── Basic Bowling ──────────────────────────
    "wicket": 25,            # per wicket
    "maiden": 12,            # per maiden over

    # ── Bowling Milestones ─────────────────────
    "five_wickets": 16,      # 5+ wickets
    "four_wickets": 8,       # 4 wickets
    "three_wickets": 4,      # 3 wickets

    # ── Bowling Economy ────────────────────────
    # Minimum overs bowled to qualify
    "economy_applicable_roles": ["bowler", "allrounder"],
    "economy_min_overs": 2,
    "economy_below_5": 6,
    "economy_5_6": 4,
    "economy_6_7": 2,
    "economy_10_11": -2,
    "economy_11_12": -4,
    "economy_above_12": -6,

    # ── Fielding ───────────────────────────────
    "catch": 8,
    "stumping": 12,
    "run_out": 6,

    # ── Bonus Points ───────────────────────────
    "playing_bonus": 4,      # just for playing
    "motm": 25,              # Man of the Match
    "winning_team": 4,       # each player in winning team

    # ── Captain/VC Multipliers ─────────────────
    "captain_multiplier": 2.0,
    "vc_multiplier": 1.5,
}