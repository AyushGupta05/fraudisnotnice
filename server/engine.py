"""The rules: when drills go out, what each outcome does, and what an incoming text means."""

import difflib
import random
import re
import secrets
from datetime import timedelta
from zoneinfo import ZoneInfo

import mail
import store
from drills import SCAM_TYPES, make_drill

LONDON = ZoneInfo("Europe/London")

START_INTERVAL_HOURS = 72           # the first drill lands within three days of consent
MIN_INTERVAL_HOURS = 24
MAX_INTERVAL_HOURS = 24 * 60        # never more than about two months apart; awareness fades after that
RESPONSE_WINDOW = timedelta(hours=48)  # silence for this long counts as a miss

CODE_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"   # no look-alike characters
LINK_CODE = re.compile(r"/r/([a-z2-9]{6})")
URL_LIKE = re.compile(r"https?://|www\.|\.co\.uk|\.com\b|\.uk/|\.net\b")
SCAM_WORDS = (
    "bank", "account", "card", "payment", "parcel", "delivery", "redeliver", "customs",
    "hmrc", "tax", "refund", "gov", "prize", "won", "winner", "voucher", "claim",
    "urgent", "suspended", "verify", "confirm", "click", "password", "pin", "pay",
    "new number", "nicked", "stolen",
)
SCAM_WORD = re.compile(r"\b(" + "|".join(map(re.escape, SCAM_WORDS)) + r")\b")   # whole words, so "won" is not "wonderful"
STOP_WORDS = {"STOP", "STOP ALL", "UNSUBSCRIBE", "NO"}

RESULTS = ("unknown_sender", "stopped", "drill_forwarded", "drill_already_counted", "real_scam", "ignored")


# ---------------------------------------------------------------- consent

def enrol(db, details, at):
    """Create a target and queue the consent text. Returns the new target id."""
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
    store.queue(
        db, details["phone"],
        f"Scam Check: {details['grandchild']} would like to send you the occasional practice scam text, "
        f"so you get good at spotting the real ones. Your code is {otp}. "
        f"Tell {details['grandchild']} the code to agree, or reply STOP to say no.",
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


def stop(db, target, at):
    db.execute("UPDATE targets SET status = 'stopped', next_due_at = NULL WHERE id = ?", (target["id"],))
    store.queue(db, target["phone"], f"Scam Check: no problem {target['name']}, no more practice texts.", "reply", at)


# ---------------------------------------------------------------- sending drills

def tick(db, link_base):
    """Run whenever the phone checks in: expire stale drills, then write any that are due."""
    at = store.now()
    for drill in db.execute("SELECT * FROM drills WHERE status = 'pending'").fetchall():
        if at - store.parse(drill["sent_at"]) > RESPONSE_WINDOW:
            resolve(db, drill, "missed", at)
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
    """Write a drill aimed at the target's weakest scam type and queue it for the phone."""
    scam_type = weakest_type(db, target["id"])
    code = unused_code(db)
    body, tell = make_drill(scam_type, target, f"{link_base}/r/{code}")
    cursor = db.execute(
        "INSERT INTO drills (target_id, code, scam_type, body, tell, status, sent_at)"
        " VALUES (?, ?, ?, ?, ?, 'pending', ?)",
        (target["id"], code, scam_type, body, tell, store.iso(at)),
    )
    store.queue(db, target["phone"], body, "drill", at)
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

    if outcome == "forwarded":
        interval = min(interval * 1.5, MAX_INTERVAL_HOURS)
        streak += 1
        points += 10 + (5 if streak >= 3 else 0)
    elif outcome == "clicked":
        interval = max(interval / 2, MIN_INTERVAL_HOURS)
        streak = 0
    elif outcome == "missed":
        interval = max(interval * 0.75, MIN_INTERVAL_HOURS)

    db.execute("UPDATE drills SET status = ?, resolved_at = ? WHERE id = ?", (outcome, store.iso(at), drill["id"]))
    db.execute("UPDATE targets SET streak = ?, points = ? WHERE id = ?", (streak, points, target["id"]))
    schedule(db, target["id"], interval, at)
    return store.target_by_id(db, target["id"])


def scorecard(db, target_id):
    """Per scam type: how many drills, how each ended, and immunity as the percentage forwarded."""
    card = {
        scam_type: {"label": label, "attempts": 0, "forwarded": 0, "clicked": 0, "missed": 0, "immunity": None}
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
            entry["immunity"] = round(100 * entry["forwarded"] / entry["attempts"])
    return card


def weakest_type(db, target_id):
    """Untried types first, then the lowest immunity, ties broken at random."""
    def rank(item):
        immunity = item[1]["immunity"]
        return (-1 if immunity is None else immunity, random.random())
    return min(scorecard(db, target_id).items(), key=rank)[0]


# ---------------------------------------------------------------- incoming texts

def handle_inbound(db, from_phone, body, at):
    """Work out what a text from a target means, act on it, and return (result, drill_id)."""
    target = store.target_by_phone(db, from_phone)
    drill = None

    if target is None or not body:
        result = "unknown_sender"
    elif body.upper().rstrip(".!") in STOP_WORDS:
        stop(db, target, at)
        result = "stopped"
    elif (drill := matching_drill(db, target["id"], body)) is not None:
        result = reward(db, target, drill, at)
    elif looks_like_scam(body):
        alert_family(db, target, body, at)
        result = "real_scam"
    else:
        result = "ignored"

    db.execute(
        "INSERT INTO inbound (from_phone, body, result, drill_id, received_at) VALUES (?, ?, ?, ?, ?)",
        (from_phone, body, result, drill["id"] if drill else None, store.iso(at)),
    )
    return result, drill["id"] if drill else None


def matching_drill(db, target_id, body):
    """Find the drill a forwarded text came from: by its link code, else by how similar the words are."""
    found = LINK_CODE.search(body)
    if found:
        drill = db.execute(
            "SELECT * FROM drills WHERE code = ? AND target_id = ?", (found.group(1), target_id)
        ).fetchone()
        if drill:
            return drill

    def similarity(drill):
        return difflib.SequenceMatcher(None, squash(body), squash(drill["body"])).ratio()

    best = max(store.recent_drills(db, target_id), key=similarity, default=None)
    return best if best is not None and similarity(best) >= 0.6 else None


def squash(text):
    return re.sub(r"\s+", " ", text.lower())


def reward(db, target, drill, at):
    if drill["status"] != "pending":
        return "drill_already_counted"
    updated = resolve(db, drill, "forwarded", at)
    gained = updated["points"] - target["points"]
    store.queue(
        db, target["phone"],
        f"Scam Check: well spotted {target['name']}! That was practice from {target['grandchild']}. "
        f"+{gained} points, streak {updated['streak']}.",
        "reply", at,
    )
    return "drill_forwarded"


def looks_like_scam(body):
    lower = body.lower()
    return bool(URL_LIKE.search(lower) or SCAM_WORD.search(lower))


def alert_family(db, target, body, at):
    """Text every family number, email them if set up, and reassure the target."""
    alert = (
        f"Scam Check: {target['name']} just received this text and forwarded it. "
        f"It is not one of our drills, so treat it as real. Please call {target['name']}.\n\n{body[:400]}"
    )
    for member in store.family(db):
        store.queue(db, member["phone"], alert, "alert", at)
    mail.send(f"Scam Check: {target['name']} got a real scam text", alert)
    store.queue(
        db, target["phone"],
        f"Scam Check: thank you {target['name']}, that one was NOT from us, so it is probably a real scam. "
        f"Don't reply or tap anything. {target['grandchild']} has been told and will call you.",
        "reply", at,
    )
