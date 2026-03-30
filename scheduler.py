from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timezone, timedelta

def update_match_statuses(app):
    """Check and update match statuses based on current time."""
    with app.app_context():
        from database import db, Match
        now = datetime.now(timezone.utc)

        matches = Match.query.filter(
            Match.status.in_(["upcoming", "live"])
        ).all()
        changed = 0

        for match in matches:
            # Make match_date timezone aware
            match_date = match.match_date
            if match_date.tzinfo is None:
                match_date = match_date.replace(tzinfo=timezone.utc)

            # Match ends ~3.5 hours after start
            match_end = match_date + timedelta(hours=3, minutes=30)

            if match.status == "upcoming" and now >= match_date:
                match.status = "live"
                changed += 1
                print(f"🟢 Match {match.match_number} LIVE: "
                      f"{match.team1} vs {match.team2}")

            elif match.status == "live" and now >= match_end:
                match.status = "completed"
                changed += 1
                print(f"✅ Match {match.match_number} COMPLETED: "
                      f"{match.team1} vs {match.team2}")

        if changed:
            db.session.commit()

def start_scheduler(app):
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=lambda: update_match_statuses(app),
        trigger="interval",
        minutes=1,
        id="match_status_updater",
        replace_existing=True
    )
    scheduler.start()
    print("⏰ Match status scheduler started!")
    return scheduler