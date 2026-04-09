from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))


def _create_snapshots(match, db, User, UserTeam, UserMatchTeam):
    """Create team snapshots for all users for a given match."""
    count = 0
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
            count += 1
    print(f"📸 {count} snapshots for Match {match.match_number}")
    return count


def update_match_statuses(app):
    with app.app_context():
        from database import db, Match, User, UserTeam, UserMatchTeam
        now = datetime.now(timezone.utc)
        changed = 0

        # ── Process upcoming → live and live → completed ───────
        matches = Match.query.filter(
            Match.status.in_(["upcoming", "live"])
        ).all()

        for match in matches:
            match_utc = match.match_date.replace(
                tzinfo=IST).astimezone(timezone.utc)
            match_end = match_utc + timedelta(hours=3, minutes=30)

            if match.status == "upcoming" and now >= match_utc:
                match.status = "live"
                changed += 1
                print(f"🟢 Match {match.match_number} LIVE: "
                      f"{match.team1} vs {match.team2}")
                _create_snapshots(match, db, User, UserTeam, UserMatchTeam)

            elif match.status == "live" and now >= match_end:
                match.status = "completed"
                changed += 1
                print(f"✅ Match {match.match_number} COMPLETED: "
                      f"{match.team1} vs {match.team2}")

        # ── Backfill: fix completed matches with 0 snapshots ───
        # Catches cases where scheduler missed a match start
        # e.g. Railway redeployed after match started
        completed_matches = Match.query.filter_by(status="completed").all()
        users_with_teams = User.query.join(
            UserTeam, User.id == UserTeam.user_id
        ).count()

        for match in completed_matches:
            snap_count = UserMatchTeam.query.filter_by(
                match_id=match.id).count()
            if snap_count == 0 and users_with_teams > 0:
                print(f"⚠️ Match {match.match_number} has 0 snapshots "
                      f"— backfilling now...")
                _create_snapshots(match, db, User, UserTeam, UserMatchTeam)
                changed += 1

        if changed:
            db.session.commit()
            print(f"✅ Scheduler run complete — {changed} changes made")
        else:
            print("✅ Scheduler run complete — no changes needed")

        reschedule_next_check(app)


def reschedule_next_check(app):
    with app.app_context():
        from database import Match
        from apscheduler.triggers.date import DateTrigger

        now = datetime.now(timezone.utc)
        trigger_times = []

        # ALL upcoming match starts
        for match in Match.query.filter_by(status="upcoming").all():
            match_utc = match.match_date.replace(
                tzinfo=IST).astimezone(timezone.utc)
            if match_utc > now:
                trigger_times.append(
                    ("start", match.match_number, match_utc))

        # ALL live match ends
        for match in Match.query.filter_by(status="live").all():
            match_utc = match.match_date.replace(
                tzinfo=IST).astimezone(timezone.utc)
            match_end = match_utc + timedelta(hours=3, minutes=30)
            if match_end > now:
                trigger_times.append(
                    ("end", match.match_number, match_end))

        if not trigger_times:
            print("📅 No upcoming matches — scheduler idle")
            return

        # Sort by time and pick the NEXT trigger
        trigger_times.sort(key=lambda x: x[2])
        next_type, next_num, next_time = trigger_times[0]

        # Add 2 min buffer
        next_run = next_time + timedelta(minutes=2)

        # Warn about double-headers
        if len(trigger_times) > 1:
            second_time = trigger_times[1][2]
            gap = (second_time - next_time).total_seconds() / 60
            if gap < 240:  # within 4 hours = same day
                print(f"⚠️ Back-to-back matches — next two triggers "
                      f"{gap:.0f} min apart")

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

        # Check for matches that SHOULD be live but aren't
        overdue_matches = []
        for match in Match.query.filter_by(status="upcoming").all():
            match_utc = match.match_date.replace(
                tzinfo=IST).astimezone(timezone.utc)
            if match_utc <= now:
                overdue_matches.append(match)

        if overdue_matches:
            for m in overdue_matches:
                print(f"⚠️ Overdue match: {m.match_number} "
                      f"{m.team1} vs {m.team2}")
            next_run = now + timedelta(minutes=1)
            print(f"⚠️ Running overdue check in 1 min")
        else:
            # Find next upcoming trigger
            trigger_times = []

            for match in Match.query.filter_by(status="upcoming").all():
                match_utc = match.match_date.replace(
                    tzinfo=IST).astimezone(timezone.utc)
                if match_utc > now:
                    trigger_times.append(match_utc)

            for match in Match.query.filter_by(status="live").all():
                match_utc = match.match_date.replace(
                    tzinfo=IST).astimezone(timezone.utc)
                match_end = match_utc + timedelta(hours=3, minutes=30)
                if match_end > now:
                    trigger_times.append(match_end)

            if trigger_times:
                next_run = min(trigger_times) + timedelta(minutes=2)
            else:
                next_run = now + timedelta(hours=24)

        ist_display = next_run.astimezone(IST)
        print(f"⏰ Match scheduler: first check at "
              f"{ist_display.strftime('%b %d %I:%M %p')} IST")

    # Always add a 5-minute fallback interval job
    scheduler_instance.add_job(
        func=lambda: update_match_statuses(app),
        trigger="interval",
        minutes=5,
        id="match_status_fallback",
        replace_existing=True
    )

    # Primary date-based trigger
    scheduler_instance.add_job(
        func=lambda: update_match_statuses(app),
        trigger="date",
        run_date=next_run,
        id="match_status_updater",
        replace_existing=True
    )

    scheduler_instance.start()
    print("⏰ Match status scheduler started!")
    return scheduler_instance