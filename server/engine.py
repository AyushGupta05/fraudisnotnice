"""The rules: when drills go out and what happens when the link is, or is not, tapped."""

import os
import random
import secrets
from datetime import timedelta
from zoneinfo import ZoneInfo

import sms
import store
from drills import SCAM_TYPES, make_drill

LONDON = ZoneInfo("Europe/London")

START_INTERVAL_HOURS = 72           # the first drill lands within three days of consent
MIN_INTERVAL_HOURS = 24
MAX_INTERVAL_HOURS = 24 * 60        # never more than about two months apart; awareness fades after that
RESPONSE_WINDOW = timedelta(hours=float(os.environ.get("DRILL_WINDOW_HOURS", "48")))  # untouched for this long = passed

CODE_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"   # no look-alike characters


def send_text(db, to_phone, body, kind, at):
    sent = sms.send(to_phone, body)
    store.log_text(db, to_phone, body, kind, sent, at)
    return sent


# ---------------------------------------------------------------- consent

def enrol(db, details, at):
    """Create a target and text them the consent code. Returns the new target id."""
    otp = f"{secrets.randbelow(1_000_000):06d}"
    cursor = db.execute(
        "INSERT INTO targets (name, phone, grandchild, nickname, bank, parcel_firm, wake_hour, sleep_hour,"
        " status, otp, interval_hours, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)",
        (
            details["name"], details["phone"], details["grandchild"], details["nickname"],
            details["bank"], details["parcel_firm"], details["wake_hour"], details["sleep_hour"],
            otp, START_INTERVAL_HOURS, store.iso(at),
        ),
    )
    send_text(
        db, details["phone"],
        f"Scam Check: {details['grandchild']} would like to send you the occasional practice scam text, "
        f"so you get good at spotting the real ones. Your code is {otp}. "
        f"Tell {details['grandchild']} the code to agree.",
        "otp", at,
    )
    return cursor.lastrowid


def verify(db, target, code, at):
    """Activate a target whose consent code matches. Returns True on success."""
    if code != target["otp"]:
        return False
    db.execute("UPDATE targets SET status = 'active', otp = NULL WHERE id = ?", (target["id"],))
    schedule(db, target["id"], START_INTERVAL_HOURS, at)
    return True


# ---------------------------------------------------------------- sending drills

def tick(db, link_base):
    """Run on every app request: settle drills nobody tapped, then send any that are due."""
    at = store.now()
    for drill in db.execute("SELECT * FROM drills WHERE status = 'pending'").fetchall():
        if at - store.parse(drill["sent_at"]) > RESPONSE_WINDOW:
            resolve(db, drill, "passed", at)
    due = db.execute(
        "SELECT * FROM targets WHERE status = 'active' AND next_due_at <= ?", (store.iso(at),)
    ).fetchall()
    for target in due:
        if awake(target, at):
            send_drill(db, target, at, link_base)


def awake(target, at):
    hour = at.astimezone(LONDON).hour
    return target["wake_hour"] <= hour < target["sleep_hour"]


def send_drill(db, target, at, link_base):
    """Write a drill aimed at the target's weakest scam type and text it."""
    scam_type = weakest_type(db, target["id"])
    code = unused_code(db)
    body, tell = make_drill(scam_type, target, f"{link_base}/r/{code}")
    cursor = db.execute(
        "INSERT INTO drills (target_id, code, scam_type, body, tell, status, sent_at)"
        " VALUES (?, ?, ?, ?, ?, 'pending', ?)",
        (target["id"], code, scam_type, body, tell, store.iso(at)),
    )
    send_text(db, target["phone"], body, "drill", at)
    # The next drill is scheduled when this one resolves, so park the due date until then.
    db.execute("UPDATE targets SET next_due_at = NULL WHERE id = ?", (target["id"],))
    return db.execute("SELECT * FROM drills WHERE id = ?", (cursor.lastrowid,)).fetchone()


def unused_code(db):
    while True:
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
        if db.execute("SELECT 1 FROM drills WHERE code = ?", (code,)).fetchone() is None:
            return code


def schedule(db, target_id, interval_hours, at):
    """Pick the next drill time somewhere in the back half of the interval, so it never feels like clockwork."""
    due = at + timedelta(hours=interval_hours * random.uniform(0.5, 1.0))
    db.execute(
        "UPDATE targets SET interval_hours = ?, next_due_at = ? WHERE id = ?",
        (interval_hours, store.iso(due), target_id),
    )


# ---------------------------------------------------------------- outcomes and scores

def resolve(db, drill, outcome, at):
    """Close a drill and adjust the target's rhythm and score. Returns the updated target."""
    target = store.target_by_id(db, drill["target_id"])
    interval, streak, points = target["interval_hours"], target["streak"], target["points"]

    if outcome == "passed":
        interval = min(interval * 1.5, MAX_INTERVAL_HOURS)
        streak += 1
        points += 10 + (5 if streak >= 3 else 0)
    elif outcome == "clicked":
        interval = max(interval / 2, MIN_INTERVAL_HOURS)
        streak = 0

    db.execute("UPDATE drills SET status = ?, resolved_at = ? WHERE id = ?", (outcome, store.iso(at), drill["id"]))
    db.execute("UPDATE targets SET streak = ?, points = ? WHERE id = ?", (streak, points, target["id"]))
    schedule(db, target["id"], interval, at)
    return store.target_by_id(db, target["id"])


def scorecard(db, target_id):
    """Per scam type: how many drills, how each ended, and immunity as the percentage passed."""
    card = {
        scam_type: {"label": label, "attempts": 0, "passed": 0, "clicked": 0, "immunity": None}
        for scam_type, label in SCAM_TYPES.items()
    }
    rows = db.execute(
        "SELECT scam_type, status, COUNT(*) AS n FROM drills"
        " WHERE target_id = ? AND status != 'pending' GROUP BY scam_type, status",
        (target_id,),
    )
    for row in rows:
        entry = card[row["scam_type"]]
        entry[row["status"]] += row["n"]
        entry["attempts"] += row["n"]
    for entry in card.values():
        if entry["attempts"]:
            entry["immunity"] = round(100 * entry["passed"] / entry["attempts"])
    return card


def weakest_type(db, target_id):
    """Untried types first, then the lowest immunity, ties broken at random."""
    def rank(item):
        immunity = item[1]["immunity"]
        return (-1 if immunity is None else immunity, random.random())
    return min(scorecard(db, target_id).items(), key=rank)[0]
