"""SQLite storage: one file next to the server, created on first run."""

import re
import sqlite3
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS targets (
    id             INTEGER PRIMARY KEY,
    name           TEXT NOT NULL,              -- what the family calls them, e.g. Nana
    phone          TEXT NOT NULL UNIQUE,       -- +44 form, see normalise_phone
    grandchild     TEXT NOT NULL,              -- who set this up
    nickname       TEXT NOT NULL,              -- what the target calls the grandchild
    bank           TEXT NOT NULL,
    parcel_firm    TEXT NOT NULL,
    wake_hour      INTEGER NOT NULL,           -- drills only land between these two London hours
    sleep_hour     INTEGER NOT NULL,
    status         TEXT NOT NULL,              -- pending | active | stopped
    otp            TEXT,                       -- consent code, cleared once verified
    interval_hours REAL NOT NULL,              -- current gap between drills
    next_due_at    TEXT,                       -- NULL while a drill is waiting for a response
    streak         INTEGER NOT NULL DEFAULT 0,
    points         INTEGER NOT NULL DEFAULT 0,
    created_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS drills (
    id          INTEGER PRIMARY KEY,
    target_id   INTEGER NOT NULL REFERENCES targets(id),
    code        TEXT NOT NULL UNIQUE,          -- the part of the link after /r/
    scam_type   TEXT NOT NULL,
    body        TEXT NOT NULL,
    tell        TEXT NOT NULL,                 -- the one-line lesson shown on the reveal page
    status      TEXT NOT NULL,                 -- pending | forwarded | clicked | missed
    sent_at     TEXT NOT NULL,
    resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS outbox (
    id         INTEGER PRIMARY KEY,
    to_phone   TEXT NOT NULL,
    body       TEXT NOT NULL,
    kind       TEXT NOT NULL,                  -- otp | drill | reply | alert
    status     TEXT NOT NULL,                  -- queued | sent
    created_at TEXT NOT NULL,
    sent_at    TEXT
);

CREATE TABLE IF NOT EXISTS family (
    id    INTEGER PRIMARY KEY,
    name  TEXT NOT NULL,
    phone TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS inbound (
    id          INTEGER PRIMARY KEY,
    from_phone  TEXT NOT NULL,
    body        TEXT NOT NULL,
    result      TEXT NOT NULL,                 -- one of engine.RESULTS
    drill_id    INTEGER,
    received_at TEXT NOT NULL
);
"""


def connect(path):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    return db


# Times are stored as ISO 8601 strings in UTC, so they sort correctly as text.

def now():
    return datetime.now(timezone.utc)


def iso(moment):
    return moment.isoformat(timespec="seconds")


def parse(text):
    return datetime.fromisoformat(text)


def normalise_phone(raw):
    """Reduce any way of writing a UK number to +447..., so a forward matches its enrolment."""
    digits = re.sub(r"[^\d+]", "", raw or "")
    if digits.startswith("00"):
        digits = "+" + digits[2:]
    if digits.startswith("0"):
        digits = "+44" + digits[1:]
    elif digits.startswith("44"):
        digits = "+" + digits
    return digits


def target_by_id(db, target_id):
    return db.execute("SELECT * FROM targets WHERE id = ?", (target_id,)).fetchone()


def target_by_phone(db, phone):
    return db.execute("SELECT * FROM targets WHERE phone = ?", (phone,)).fetchone()


def pending_drill(db, target_id):
    return db.execute(
        "SELECT * FROM drills WHERE target_id = ? AND status = 'pending'", (target_id,)
    ).fetchone()


def recent_drills(db, target_id, limit=10):
    return db.execute(
        "SELECT * FROM drills WHERE target_id = ? ORDER BY id DESC LIMIT ?", (target_id, limit)
    ).fetchall()


def family(db):
    return db.execute("SELECT * FROM family ORDER BY id").fetchall()


def queue(db, to_phone, body, kind, at):
    """Put a text in the outbox for the phone to send."""
    db.execute(
        "INSERT INTO outbox (to_phone, body, kind, status, created_at) VALUES (?, ?, ?, 'queued', ?)",
        (to_phone, body, kind, iso(at)),
    )
