# Backend

The Phase 0 backend intentionally contains only a liveness endpoint. Database,
RAG, agent, and AWS integrations begin in later milestones.

Run locally after Python 3.12 and dependencies are available:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
uvicorn app.main:app --reload
```
