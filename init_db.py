import os
if os.environ.get("RUN_SEED") == "true":
    print("🌱 Running seed...")
    from seed_players import seed_players, seed_matches
    seed_players()
    seed_matches()
    print("✅ Seed complete!")