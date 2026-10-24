def solve(job, models, features, download=None):
    ctx = {
        "job": job,
        "models": models,
        "download": download,            # Storage theke file nambanor function
        "user_question": (job.get("question") or "").strip(),
        "question": (job.get("question") or "").strip(),
        "options": job.get("options") or {},
        "images": [],
        "document_text": "",
        "sources": [],
        "answer": {},
    }
    for stage in ("pre", "solve", "post"):
        for f in features:
            if f.stage == stage and f.should_run(ctx):
                ctx = f.run(ctx)
    return ctx["answer"]
