from database import engine, ChatUser, ChatSession
from sqlalchemy.orm import Session
from datetime import timedelta

with Session(engine) as db:
    users = db.query(ChatUser).all()
    for u in users:
        u.create_time = u.create_time + timedelta(hours=8)

    sessions = db.query(ChatSession).all()
    for s in sessions:
        s.create_time = s.create_time + timedelta(hours=8)

    db.commit()
    print(f"Migrated {len(users)} users, {len(sessions)} sessions")