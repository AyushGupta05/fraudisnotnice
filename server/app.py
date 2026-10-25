"""Scam Check backend. Routes only; the rules live in engine.py.

Run ./run.sh to start this together with the public tunnel, or `python app.py` for localhost only.

Environment (run.sh loads .env):
  SCAMCHECK_TOKEN     shared secret the app sends in the X-Token header
  PORT                default 5055
  BASE_URL            public address used in drill links; defaults to wherever the request came in
  DB_PATH             SQLite file; defaults to scamcheck.db next to this file
  AWS_SENDER_ID       sender ID texts come from (default SCAMCHECK); AWS_REGION default us-east-1
  DRILL_WINDOW_HOURS  how long an untouched drill counts as passed (default 48)
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
    passed = sum(entry["passed"] for entry in card.values())
    waiting = store.pending_drill(db(), target["id"])
    return {
        "id": target["id"],
        "name": target["name"],
        "phone": target["phone"],
        "grandchild": target["grandchild"],
        "status": target["status"],
        "points": target["points"],
        "streak": target["streak"],
        "immunity": round(100 * passed / attempts) if attempts else None,
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


# ---------------------------------------------------------------- routes

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
    engine.tick(db(), link_base())
    return jsonify(detail(target_or_404(target_id)))


@app.post("/targets/<int:target_id>/send-now")
@protected
def send_now(target_id):
    """A drill right now, waking hours or not."""
    target = target_or_404(target_id)
    if target["status"] != "active":
        abort(400, "this person has not agreed yet")
    if store.pending_drill(db(), target_id):
        abort(409, "a drill is already out")
    return jsonify(drill_view(engine.send_drill(db(), target, store.now(), link_base()))), 201


@app.delete("/targets/<int:target_id>")
@protected
def forget_target(target_id):
    """Wipe someone completely."""
    target_or_404(target_id)
    db().execute("DELETE FROM drills WHERE target_id = ?", (target_id,))
    db().execute("DELETE FROM targets WHERE id = ?", (target_id,))
    return jsonify(deleted=target_id)


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
    app.run(host="0.0.0.0", port=PORT)
