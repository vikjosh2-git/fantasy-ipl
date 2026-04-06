from app import app
from database import User, TransferWindow, Match, TransferHistory
app.app_context().push()

u = User.query.get(1)  # change to your user_id
print(f"user_id: {u.id}")
print(f"first_transfer_window_id: {u.first_transfer_window_id}")
print(f"transfers_remaining: {u.transfers_remaining}")

last_match = Match.query.filter(
    Match.status.in_(["live", "completed"])
).order_by(Match.match_date.desc()).first()
print(f"last_match id: {last_match.id if last_match else None}")
print(f"window_match_id: {last_match.id if last_match else 0}")

windows = TransferWindow.query.filter_by(user_id=u.id).all()
for w in windows:
    print(f"window id={w.id} match={w.window_start_match} "
          f"used={w.transfers_used} "
          f"baseline_count={len(w.baseline_player_ids.split(','))}")

transfers = TransferHistory.query.filter_by(user_id=u.id).all()
print(f"TransferHistory rows: {len(transfers)}")
for t in transfers:
    print(f"  in={t.player_in_id} out={t.player_out_id} window={t.window_match_id}")