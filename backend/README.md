# Shared FastAPI backend

This directory contains the shared backend shell for the four research components.
Members own their own component implementation and routes. No C1–C4 router,
service, model, or placeholder code is included in this scaffold.

## Run locally

From `backend/`:

```bash
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

- System health: http://localhost:8000/health
- Interactive API documentation: http://localhost:8000/docs

The backend intentionally has **no component routes** until their owners implement
and integrate them. Add new routers in a reviewed integration change rather than
importing non-existent feature modules.
