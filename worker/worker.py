import os
import time
import uuid
import datetime as dt
import traceback

from supabase import create_client

from worker.core.registry import load_config, load_features
from worker.core.errors import UserError
from worker.model_loader import ModelManager
from worker.pipeline import solve

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
WORKER_ID = f"colab-{uuid.uuid4().hex[:6]}"


def now_iso():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def heartbeat():
    sb.table("worker_heartbeat").upsert({
        "worker_id": WORKER_ID, "last_seen": now_iso(),
    }).execute()


def requeue_stale(minutes):
    cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=minutes)).isoformat()
    sb.table("jobs").update({"status": "pending", "worker_id": None}) \
        .eq("status", "processing").lt("started_at", cutoff).execute()


def download(path):
    return sb.storage.from_("uploads").download(path)


def main():
    cfg = load_config()
    wcfg = cfg.get("worker", {})
    features = load_features(cfg)
    models = ModelManager(cfg)
    models.preload()

    print(f"[worker] {WORKER_ID} ready. features:", [f.name for f in features])
    last_hb = 0.0
    last_clean = 0.0

    while True:
        t = time.time()
        if t - last_hb > wcfg.get("heartbeat_sec", 20):
            heartbeat(); last_hb = t
        if t - last_clean > 120:
            requeue_stale(wcfg.get("stale_job_minutes", 10)); last_clean = t

        try:
            res = sb.rpc("claim_job", {"p_worker": WORKER_ID}).execute().data
        except Exception as e:
            print("[worker] claim error:", e)
            time.sleep(5)
            continue

        if not res:
            time.sleep(wcfg.get("poll_interval_sec", 2))
            continue

        job = res[0]
        print("[worker] job", job["id"])
        try:
            answer = solve(job, models, features, download=download)
            sb.table("jobs").update({
                "status": "done", "answer": answer, "finished_at": now_iso(),
            }).eq("id", job["id"]).execute()
        except UserError as e:
            sb.table("jobs").update({
                "status": "error", "error": "USER: " + str(e), "finished_at": now_iso(),
            }).eq("id", job["id"]).execute()
        except Exception:
            traceback.print_exc()
            sb.table("jobs").update({
                "status": "error", "error": traceback.format_exc()[-1500:],
                "finished_at": now_iso(),
            }).eq("id", job["id"]).execute()


if __name__ == "__main__":
    main()
