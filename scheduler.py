from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timezone, timedelta

def update_match_statuses(app):
    with app.app_context():
        from database import db, Match, User, UserTeam, UserMatchTeam
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

                # ── Snapshot teams at match start ──────────────
                snapshot_count = 0
                all_users = User.query.all()
                for user in all_users:
                    team = UserTeam.query.filter_by(user_id=user.id).first()
                    if not team or not team.player_ids:
                        continue
                    # Only snapshot if user had a team BEFORE match started
                    existing = UserMatchTeam.query.filter_by(
                        user_id=user.id, match_id=match.id
                    ).first()
                    if not existing:
                        snapshot = UserMatchTeam(
                            user_id=user.id,
                            match_id=match.id,
                            player_ids=team.player_ids,
                            captain_id=team.captain_id,
                            vice_captain_id=team.vice_captain_id
                        )
                        db.session.add(snapshot)
                        snapshot_count += 1
                print(f"📸 {snapshot_count} team snapshots created for "
                      f"Match {match.match_number}")

            elif match.status == "live" and now >= match_end:
                match.status = "completed"
                changed += 1
                print(f"✅ Match {match.match_number} COMPLETED: "
                      f"{match.team1} vs {match.team2}")

        if changed:
            db.session.commit()

        reschedule_next_check(app)

def reschedule_next_check(app):
    with app.app_context():
        from database import Match
        from apscheduler.triggers.date import DateTrigger

        ist = timezone(timedelta(hours=5, minutes=30))
        now = datetime.now(timezone.utc)
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

        next_run = min(trigger_times) + timedelta(minutes=2)
        try:
            scheduler_instance.reschedule_job(
                "match_status_updater",
                trigger=DateTrigger(run_date=next_run)
            )
            ist_display = next_run.astimezone(ist)
            print(f"⏰ Next check at: "
                  f"{ist_display.strftime('%b %d %I:%M %p')} IST")
        except Exception as e:
            print(f"⚠️ Reschedule error: {e}")

scheduler_instance = None

def start_scheduler(app):
    global scheduler_instance
    scheduler_instance = BackgroundScheduler()

    with app.app_context():
        from database import Match
        ist = timezone(timedelta(hours=5, minutes=30))
        now = datetime.now(timezone.utc)
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
    print("Match status scheduler started!")
    return scheduler_instance