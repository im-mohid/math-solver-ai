def solve(job, model, features):
    ctx = {
        "job": job,
        "model": model,
        "question": job["question"],
        "options": job.get("options") or {},
        "sources": [],
        "answer": {},
    }
    for stage in ("pre", "solve", "post"):
        for f in features:
            if f.stage == stage and f.should_run(ctx):
                ctx = f.run(ctx)
    return ctx["answer"]
