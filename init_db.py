from database import db, app
with app.app_context():
    # Create all missing tables
    db.create_all()
    print("✅ All tables created/verified!")
    