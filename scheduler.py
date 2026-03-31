from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timezone, timedelta

def update_match_statuses(app):
    """Check and update match statuses based on current time."""
    with app.app_context():
        from database import db, Match
        now = datetime.now(timezone.utc)
        ist = timezone(timedelta(hours=5, minutes=30))
        changed = 0

        matches = Match.query.filter(
            Match.status.in_(["upcoming", "live"])
        ).all()

        for match in matches:
            match_date_utc = match.match_date.replace(tzinfo=ist).astimezone(timezone.utc)
            match_end = match_date_utc + timedelta(hours=3, minutes=30)

            if match.status == "upcoming" and now >= match_date_utc:
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

        # Reschedule next check based on upcoming matches
        reschedule_next_check(app)

def reschedule_next_check(app):
    """Schedule next run exactly when needed."""
    with app.app_context():
        from database import Match
        from apscheduler.triggers.date import DateTrigger

        ist = timezone(timedelta(hours=5, minutes=30))
        now = datetime.now(timezone.utc)

        # Find all trigger times we care about:
        # 1. Match start times (upcoming → live)
        # 2. Match end times (live → completed) = start + 3.5 hours
        trigger_times = []

        upcoming = Match.query.filter_by(status="upcoming").all()
        for match in upcoming:
            match_utc = match.match_date.replace(tzinfo=ist).astimezone(timezone.utc)
            if match_utc > now:
                trigger_times.append(match_utc)

        live = Match.query.filter_by(status="live").all()
        for match in live:
            match_utc = match.match_date.replace(tzinfo=ist).astimezone(timezone.utc)
            match_end = match_utc + timedelta(hours=3, minutes=30)
            if match_end > now:
                trigger_times.append(match_end)

        if not trigger_times:
            print("📅 No upcoming matches — scheduler idle")
            return

        # Next trigger = earliest future time
        next_run = min(trigger_times)
        # Add 2 min buffer to ensure match has actually started
        next_run_with_buffer = next_run + timedelta(minutes=2)

        try:
            scheduler_instance.reschedule_job(
                "match_status_updater",
                trigger=DateTrigger(run_date=next_run_with_buffer)
            )
            ist_display = next_run_with_buffer.astimezone(ist)
            print(f"⏰ Next status check scheduled at: "
                  f"{ist_display.strftime('%b %d %I:%M %p')} IST")
        except Exception as e:
            print(f"⚠️ Reschedule error: {e}")

# Global reference needed for rescheduling
scheduler_instance = None

def start_scheduler(app):
    global scheduler_instance
    scheduler_instance = BackgroundScheduler()

    # On startup find the next match time and schedule accordingly
    with app.app_context():
        from database import Match
        ist = timezone(timedelta(hours=5, minutes=30))
        now = datetime.now(timezone.utc)

        # Find next trigger time
        trigger_times = []

        upcoming = Match.query.filter_by(status="upcoming").all()
        for match in upcoming:
            match_utc = match.match_date.replace(tzinfo=ist).astimezone(timezone.utc)
            if match_utc > now:
                trigger_times.append(match_utc)

        live = Match.query.filter_by(status="live").all()
        for match in live:
            match_utc = match.match_date.replace(tzinfo=ist).astimezone(timezone.utc)
            match_end = match_utc + timedelta(hours=3, minutes=30)
            if match_end > now:
                trigger_times.append(match_end)

        if trigger_times:
            next_run = min(trigger_times) + timedelta(minutes=2)
            ist_display = next_run.astimezone(ist)
            print(f"⏰ Match scheduler: first check at "
                  f"{ist_display.strftime('%b %d %I:%M %p')} IST")
            trigger = "date"
            trigger_kwargs = {"run_date": next_run}
        else:
            # No matches — check once a day in case admin adds matches
            print("⏰ No upcoming matches — checking daily")
            trigger = "interval"
            trigger_kwargs = {"hours": 24}

    scheduler_instance.add_job(
        func=lambda: update_match_statuses(app),
        trigger=trigger,
        id="match_status_updater",
        replace_existing=True,
        **trigger_kwargs
    )
    scheduler_instance.start()
    print("⏰ Match status scheduler started!")
    return scheduler_instance