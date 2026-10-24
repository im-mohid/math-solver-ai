import datetime as dt
import os
import uuid

from flask import Flask, request, jsonify, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix

from web.db import sb

app = Flask(__name__, static_folder="static")
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)

MAX_FILE_BYTES = 10 * 1024 * 1024
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_BYTES + 2 * 1024 * 1024

limiter = Limiter(get_remote_address, app=app, default_limits=["200 per hour"],
                  storage_uri="memory://")

MAX_Q_LEN = 5000
HEARTBEAT_TIMEOUT_SEC = 60
BUCKET = "uploads"

MIME = {
    "pdf": "application/pdf", "txt": "text/plain", "md": "text/plain", "tex": "text/plain",
    "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp",
}
TEXT_EXT = {"txt", "md", "tex"}
IMAGE_EXT = {"png", "jpg", "jpeg", "webp"}


def looks_valid(ext, data):
    """Extension er shathe file er asol content mele kina (basic check)."""
    if ext == "pdf":
        return data[:5] == b"%PDF-"
    if ext == "png":
        return data[:8] == b"\x89PNG\r\n\x1a\n"
    if ext in ("jpg", "jpeg"):
        return data[:3] == b"\xff\xd8\xff"
    if ext == "webp":
        return data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    if ext in TEXT_EXT:
        return b"\x00" not in data[:2000]
    return False


@app.errorhandler(413)
def too_large(_):
    return jsonify(error="File onek boro (max 10 MB)"), 413


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.post("/api/ask")
@limiter.limit("10 per minute")
def ask():
    q = (request.form.get("question") or "").strip()
    language = request.form.get("language", "bn")
    if language not in ("bn", "en"):
        language = "bn"
    f = request.files.get("file")

    if len(q) > MAX_Q_LEN:
        return jsonify(error="Question onek boro"), 400
    if not q and not f:
        return jsonify(error="Question likho ba file upload koro"), 400

    input_type, file_path = "text", None
    if f and f.filename:
        name = f.filename.lower()
        ext = name.rsplit(".", 1)[-1] if "." in name else ""
        if ext not in MIME:
            return jsonify(error="Ei file type support kora hoy na (pdf, txt, md, tex, png, jpg, webp)"), 400
        data = f.read()
        if not data or len(data) > MAX_FILE_BYTES:
            return jsonify(error="File khali ba 10 MB er beshi"), 400
        if not looks_valid(ext, data):
            return jsonify(error="File ta thik format e na"), 400

        file_path = f"{uuid.uuid4().hex}.{ext}"          # user er file name use kora hoy na
        sb.storage.from_(BUCKET).upload(
            path=file_path, file=data, file_options={"content-type": MIME[ext]})
        input_type = "pdf" if ext == "pdf" else ("image" if ext in IMAGE_EXT else "txt")

    job = sb.table("jobs").insert({
        "input_type": input_type,
        "question": q,
        "file_url": file_path,
        "options": {"language": language},
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
    err = row.get("error")
    if err:
        # "USER: ..." = user ke dekhanor moto message; baki internal trace, dekhabo na
        row["error"] = err[6:] if err.startswith("USER: ") else "Solve korte somossa hoyeche. Abar try koro."
    return jsonify(row)


@app.get("/api/status")
def status():
    cutoff = (dt.datetime.now(dt.timezone.utc)
              - dt.timedelta(seconds=HEARTBEAT_TIMEOUT_SEC)).isoformat()
    rows = (sb.table("worker_heartbeat").select("worker_id")
            .gte("last_seen", cutoff).execute().data)
    return jsonify(worker_online=bool(rows))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
