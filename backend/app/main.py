"""Shared API entry point. Individual C1–C4 routers are not created here."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Nai Miris Smart Agriculture API",
    version="0.1.0",
    description="Shared API skeleton; research components will be integrated by their owners.",
)

# Development-only browser origins for the Vite frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "shared-backend"}
