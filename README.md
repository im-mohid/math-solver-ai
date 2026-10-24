# Math Solver AI

Page (Render) <-> Supabase (jobs queue) <-> Worker (Colab, GPU)

## Setup (Phase 0)
1. Supabase SQL Editor e `sql/schema.sql` run koro. (Ager schema already run kora thakle shudhu `sql/002_uploads_bucket.sql` run koro.)
2. GitHub e ei repo push koro.
3. Render: New Web Service -> repo connect
   - Build: `pip install -r requirements-web.txt`
   - Start: `gunicorn web.app:app`
   - Env: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
4. Colab: `training/colab_worker.ipynb` kholo, Secrets e `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` dao, shob cell chalao.
5. Render page kholo -> "Model online" dekhale question dao.

## Notun feature
`worker/features/` e ekta file banao (`Feature` class inherit), `config.yaml` e `features:` er niche on koro.

## Local test (web)
```
pip install -r requirements-web.txt
export SUPABASE_URL=... SUPABASE_SERVICE_KEY=...
python -m web.app
```

## Model gulo (config.yaml > models)
- `language`: Qwen, Bangla/English byakkha
- `expert`: tomar math model (`name` e HF repo ba Drive path, LoRA hole `lora_path`)
- `ocr`: photo/scanned PDF er jonno vision model
Prottek ta `enabled: true` korle load hobe. Flow: expert solve kore -> language model byakkha kore.
