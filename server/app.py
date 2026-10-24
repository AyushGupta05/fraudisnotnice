"""Scam Check backend. Routes only; the rules live in engine.py.

Run ./run.sh to start this together with the public tunnel, or `python app.py` for localhost only.

Environment (run.sh loads .env):
  SCAMCHECK_TOKEN   shared secret the app and the phone shortcuts send in the X-Token header
  PORT              default 5055
  BASE_URL          public address used in drill links; defaults to wherever the request came in
  DB_PATH           SQLite file; defaults to scamcheck.db next to this file
"""

import os
from functools import wraps

from flask import Flask, abort, g, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

import engine
import store
from drills import SCAM_TYPES

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", "5055"))
TOKEN = os.environ.get("SCAMCHECK_TOKEN", "dev-token")
BASE_URL = os.environ.get("BASE_URL", "").rstrip("/")
DB_PATH = os.environ.get("DB_PATH", os.path.join(HERE, "scamcheck.db"))

app = Flask(__name__)


# ---------------------------------------------------------------- plumbing

def db():
    if "db" not in g:
        g.db = store.connect(DB_PATH)
    return g.db


@app.teardown_appcontext
def finish(error):
    connection = g.pop("db", None)
    if connection is None:
        return
    connection.rollback() if error else connection.commit()
    connection.close()


def protected(view):
    @wraps(view)
    def guarded(*args, **kwargs):
        if request.headers.get("X-Token") != TOKEN:
            abort(401, "missing or wrong X-Token header")
        return view(*args, **kwargs)
    return guarded


def link_base():
    """Where drill links point: the configured address, else wherever this request came in."""
    return BASE_URL or request.host_url.rstrip("/")


def body():
    return request.get_json(force=True, silent=True) or {}


def target_or_404(target_id):
    target = store.target_by_id(db(), target_id)
    if target is None:
        abort(404, "no such target")
    return target


@app.errorhandler(HTTPException)
def as_json(error):
    return jsonify(error=error.description), error.code


# ---------------------------------------------------------------- what the app sees

def summary(target):
    card = engine.scorecard(db(), target["id"])
    attempts = sum(entry["attempts"] for entry in card.values())
    forwarded = sum(entry["forwarded"] for entry in card.values())
    waiting = store.pending_drill(db(), target["id"])
    return {
        "id": target["id"],
        "name": target["name"],
        "phone": target["phone"],
        "grandchild": target["grandchild"],
        "status": target["status"],
        "points": target["points"],
        "streak": target["streak"],
        "immunity": round(100 * forwarded / attempts) if attempts else None,
        "interval_hours": round(target["interval_hours"]),
        "next_due_at": target["next_due_at"],
        "waiting_drill": drill_view(waiting) if waiting else None,
    }


def detail(target):
    view = summary(target)
    view["by_type"] = engine.scorecard(db(), target["id"])
    view["recent_drills"] = [drill_view(d) for d in store.recent_drills(db(), target["id"])]
    return view


def drill_view(drill):
    return {
        "id": drill["id"],
        "scam_type": drill["scam_type"],
        "label": SCAM_TYPES[drill["scam_type"]],
        "status": drill["status"],
        "body": drill["body"],
        "sent_at": drill["sent_at"],
        "resolved_at": drill["resolved_at"],
    }


# ---------------------------------------------------------------- routes: targets

@app.get("/health")
def health():
    db()
    return jsonify(ok=True, link_base=link_base(), time=store.iso(store.now()))


@app.post("/enrol")
@protected
def enrol():
    data = body()
    phone = store.normalise_phone(data.get("phone", ""))
    if not (phone and data.get("name") and data.get("grandchild")):
        abort(400, "name, phone and grandchild are required")
    if store.target_by_phone(db(), phone):
        abort(409, "that number is already enrolled; forget it first to start again")

    grandchild = data["grandchild"].strip()
    details = {
        "name": data["name"].strip(),
        "phone": phone,
        "grandchild": grandchild,
        "nickname": (data.get("nickname") or grandchild).strip(),
        "bank": (data.get("bank") or "your bank").strip(),
        "parcel_firm": (data.get("parcel_firm") or "Royal Mail").strip(),
        "wake_hour": int(data.get("wake_hour", 9)),
        "sleep_hour": int(data.get("sleep_hour", 21)),
    }
    target_id = engine.enrol(db(), details, store.now())
    return jsonify(summary(target_or_404(target_id))), 201


@app.post("/verify")
@protected
def verify():
    data = body()
    target = target_or_404(int(data.get("target_id", 0)))
    if target["status"] == "stopped":
        abort(400, "this person said no")
    if target["status"] == "pending" and not engine.verify(db(), target, str(data.get("code", "")).strip(), store.now()):
        abort(400, "wrong code")
    return jsonify(summary(target_or_404(target["id"])))


@app.get("/targets")
@protected
def list_targets():
    engine.tick(db(), link_base())
    return jsonify([summary(t) for t in db().execute("SELECT * FROM targets ORDER BY id").fetchall()])


@app.get("/targets/<int:target_id>")
@protected
def show_target(target_id):
    return jsonify(detail(target_or_404(target_id)))


@app.post("/targets/<int:target_id>/send-now")
@protected
def send_now(target_id):
    """The demo button: a drill right now, waking hours or not."""
    target = target_or_404(target_id)
    if target["status"] != "active":
        abort(400, "this person has not agreed yet")
    if store.pending_drill(db(), target_id):
        abort(409, "a drill is already waiting for a response")
    return jsonify(drill_view(engine.send_drill(db(), target, store.now(), link_base()))), 201


@app.delete("/targets/<int:target_id>")
@protected
def forget_target(target_id):
    """Wipe someone completely, for judges who have finished playing."""
    target = target_or_404(target_id)
    db().execute("DELETE FROM drills WHERE target_id = ?", (target_id,))
    db().execute("DELETE FROM inbound WHERE from_phone = ?", (target["phone"],))
    db().execute("DELETE FROM outbox WHERE to_phone = ? AND status = 'queued'", (target["phone"],))
    db().execute("DELETE FROM targets WHERE id = ?", (target_id,))
    return jsonify(deleted=target_id)


# ---------------------------------------------------------------- routes: the phone

@app.get("/outbox/next")
@protected
def outbox_next():
    """The pump shortcut calls this until it gets an empty object, sending each message it receives."""
    engine.tick(db(), link_base())
    message = db().execute("SELECT * FROM outbox WHERE status = 'queued' ORDER BY id LIMIT 1").fetchone()
    if message is None:
        return jsonify({})
    db().execute("UPDATE outbox SET status = 'sent', sent_at = ? WHERE id = ?", (store.iso(store.now()), message["id"]))
    return jsonify(id=message["id"], to=message["to_phone"], body=message["body"], kind=message["kind"])


@app.post("/inbound")
@protected
def inbound():
    """The message automation posts every text from a target here."""
    data = body()
    result, drill_id = engine.handle_inbound(
        db(), store.normalise_phone(data.get("from", "")), (data.get("body") or "").strip(), store.now()
    )
    return jsonify(result=result, drill_id=drill_id)


# ---------------------------------------------------------------- routes: family

@app.get("/family")
@protected
def list_family():
    return jsonify([dict(member) for member in store.family(db())])


@app.post("/family")
@protected
def add_family():
    data = body()
    phone = store.normalise_phone(data.get("phone", ""))
    if not (phone and data.get("name")):
        abort(400, "name and phone are required")
    db().execute("INSERT OR REPLACE INTO family (name, phone) VALUES (?, ?)", (data["name"].strip(), phone))
    return jsonify([dict(member) for member in store.family(db())]), 201


@app.delete("/family/<int:member_id>")
@protected
def remove_family(member_id):
    db().execute("DELETE FROM family WHERE id = ?", (member_id,))
    return jsonify(deleted=member_id)


# ---------------------------------------------------------------- the one public page

@app.get("/r/<code>")
def reveal(code):
    drill = db().execute("SELECT * FROM drills WHERE code = ?", (code,)).fetchone()
    if drill is None:
        return render_template("missing.html"), 404
    if drill["status"] == "pending":
        engine.resolve(db(), drill, "clicked", store.now())
    target = store.target_by_id(db(), drill["target_id"])
    return render_template(
        "reveal.html", grandchild=target["grandchild"], tell=drill["tell"], label=SCAM_TYPES[drill["scam_type"]]
    )


if __name__ == "__main__":
    if TOKEN == "dev-token":
        print("Using the default token. Set SCAMCHECK_TOKEN in .env before exposing this server.")
    app.run(host="127.0.0.1", port=PORT)
