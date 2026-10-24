import datetime as dt
from flask import Flask, request, jsonify, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix

from web.db import sb

app = Flask(__name__, static_folder="static")
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)   # Render proxy er pichone asol IP

limiter = Limiter(get_remote_address, app=app, default_limits=["200 per hour"],
                  storage_uri="memory://")

MAX_Q_LEN = 5000
HEARTBEAT_TIMEOUT_SEC = 60


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.post("/api/ask")
@limiter.limit("10 per minute")
def ask():
    data = request.get_json(silent=True) or {}
    q = (data.get("question") or "").strip()
    if not q or len(q) > MAX_Q_LEN:
        return jsonify(error="Question khali ba onek boro"), 400

    options = data.get("options") if isinstance(data.get("options"), dict) else {}
    job = sb.table("jobs").insert({
        "input_type": "text",
        "question": q,
        "options": options,
    }).execute().data[0]
    return jsonify(job_id=job["id"])


@app.get("/api/result/<job_id>")
@limiter.limit("120 per minute")
def result(job_id):
    try:
        rows = (sb.table("jobs").select("status,answer,error")
                .eq("id", job_id).execute().data)
    except Exception:
        return jsonify(error="Invalid id"), 400
    if not rows:
        return jsonify(error="Not found"), 404
    row = rows[0]
    if row.get("error"):
        row["error"] = "Solve korte somossa hoyeche. Abar try koro."  # internal trace user ke dekhabo na
    return jsonify(row)


@app.get("/api/status")
def status():
    cutoff = (dt.datetime.now(dt.timezone.utc)
              - dt.timedelta(seconds=HEARTBEAT_TIMEOUT_SEC)).isoformat()
    rows = (sb.table("worker_heartbeat").select("worker_id")
            .gte("last_seen", cutoff).execute().data)
    return jsonify(worker_online=bool(rows))


if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
