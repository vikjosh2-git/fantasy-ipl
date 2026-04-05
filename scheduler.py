from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

def update_match_statuses(app):
    with app.app_context():
        from database import db, Match, User, UserTeam, UserMatchTeam
        now = datetime.now(timezone.utc)
        changed = 0

        matches = Match.query.filter(
            Match.status.in_(["upcoming", "live"])
        ).all()

        for match in matches:
            match_utc = match.match_date.replace(tzinfo=IST).astimezone(timezone.utc)
            match_end = match_utc + timedelta(hours=3, minutes=30)

            if match.status == "upcoming" and now >= match_utc:
                match.status = "live"
                changed += 1
                print(f"🟢 Match {match.match_number} LIVE: "
                      f"{match.team1} vs {match.team2}")

                # Snapshot all users with teams
                snapshot_count = 0
                for user in User.query.all():
                    team = UserTeam.query.filter_by(user_id=user.id).first()
                    if not team or not team.player_ids:
                        continue
                    existing = UserMatchTeam.query.filter_by(
                        user_id=user.id, match_id=match.id
                    ).first()
                    if not existing:
                        db.session.add(UserMatchTeam(
                            user_id=user.id,
                            match_id=match.id,
                            player_ids=team.player_ids,
                            captain_id=team.captain_id,
                            vice_captain_id=team.vice_captain_id
                        ))
                        snapshot_count += 1
                print(f"📸 {snapshot_count} snapshots for Match {match.match_number}")

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

        now = datetime.now(timezone.utc)
        trigger_times = []

        # ALL upcoming match starts
        for match in Match.query.filter_by(status="upcoming").all():
            match_utc = match.match_date.replace(tzinfo=IST).astimezone(timezone.utc)
            if match_utc > now:
                trigger_times.append(("start", match.match_number, match_utc))

        # ALL live match ends
        for match in Match.query.filter_by(status="live").all():
            match_utc = match.match_date.replace(tzinfo=IST).astimezone(timezone.utc)
            match_end = match_utc + timedelta(hours=3, minutes=30)
            if match_end > now:
                trigger_times.append(("end", match.match_number, match_end))

        if not trigger_times:
            print("📅 No upcoming matches — scheduler idle")
            return

        # Sort by time and pick the NEXT trigger
        trigger_times.sort(key=lambda x: x[2])
        next_type, next_num, next_time = trigger_times[0]

        # Add 2 min buffer
        next_run = next_time + timedelta(minutes=2)

        # Safety: if two triggers are within 30 min of each other
        # (double header), schedule a mid-check too
        if len(trigger_times) > 1:
            second_time = trigger_times[1][2]
            gap = (second_time - next_time).total_seconds() / 60
            if gap < 30:
                # Schedule at first trigger + 2min, will catch both
                print(f"⚠️ Double-header detected — triggers "
                      f"{gap:.0f} min apart, scheduling closely")

        try:
            scheduler_instance.reschedule_job(
                "match_status_updater",
                trigger=DateTrigger(run_date=next_run)
            )
            ist_display = next_run.astimezone(IST)
            print(f"⏰ Next check: {next_type} of Match {next_num} "
                  f"at {ist_display.strftime('%b %d %I:%M %p')} IST")
        except Exception as e:
            print(f"⚠️ Reschedule error: {e}")


scheduler_instance = None


def start_scheduler(app):
    global scheduler_instance
    scheduler_instance = BackgroundScheduler()

    with app.app_context():
        from database import Match
        now = datetime.now(timezone.utc)
        trigger_times = []

        for match in Match.query.filter_by(status="upcoming").all():
            match_utc = match.match_date.replace(tzinfo=IST).astimezone(timezone.utc)
            if match_utc > now:
                trigger_times.append(match_utc)

        for match in Match.query.filter_by(status="live").all():
            match_utc = match.match_date.replace(tzinfo=IST).astimezone(timezone.utc)
            match_end = match_utc + timedelta(hours=3, minutes=30)
            if match_end > now:
                trigger_times.append(match_end)

        if trigger_times:
            # Always run immediately on startup to catch any missed transitions
            next_run = datetime.now(timezone.utc) + timedelta(minutes=1)
            ist_display = next_run.astimezone(IST)
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
    print("⏰ Match status scheduler started!")
    return scheduler_instance