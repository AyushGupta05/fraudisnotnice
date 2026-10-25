"""Plant a demo person with a week of history, without sending any texts.

    .venv/bin/python demo.py

Nana gets five settled drills (four left alone, one tapped) and one still out, so every state
shows in the app. Run it again to reset her. Your own number can then be enrolled alongside her.
"""

import os
from datetime import timedelta

import engine
import sms
import store

sms.send = lambda to_phone, body: True   # nothing leaves the building

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DB_PATH", os.path.join(HERE, "scamcheck.db"))
LINK_BASE = os.environ.get("BASE_URL", "https://scamcheck.example")

NANA = {
    "name": "Nana", "phone": "+447700900123", "grandchild": "Ayush", "nickname": "Jamie",
    "bank": "Lloyds", "parcel_firm": "Evri", "wake_hour": 9, "sleep_hour": 21,
}
# (days ago it was sent, how it ended)
HISTORY = [(9, "passed"), (7, "clicked"), (6, "passed"), (4, "passed"), (2, "passed"), (0.3, "pending")]


def main():
    db = store.connect(DB_PATH)
    now = store.now()

    old = store.target_by_phone(db, NANA["phone"])
    if old:
        db.execute("DELETE FROM drills WHERE target_id = ?", (old["id"],))
        db.execute("DELETE FROM targets WHERE id = ?", (old["id"],))

    target_id = engine.enrol(db, NANA, now - timedelta(days=10))
    target = store.target_by_id(db, target_id)
    engine.verify(db, target, target["otp"], now - timedelta(days=10))

    for days_ago, outcome in HISTORY:
        sent_at = now - timedelta(days=days_ago)
        drill = engine.send_drill(db, store.target_by_id(db, target_id), sent_at, LINK_BASE)
        if outcome != "pending":
            engine.resolve(db, drill, outcome, sent_at + timedelta(hours=6 if outcome == "clicked" else 48))

    db.commit()
    print(f"Nana is ready with {len(HISTORY)} drills.")


if __name__ == "__main__":
    main()
