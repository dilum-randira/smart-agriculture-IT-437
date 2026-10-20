
"""Shared API entry point for the Nai Miris Smart Agriculture system."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# C2 - Yield Prediction Router
from app.c2.yield_prediction.routes import router as yield_router


app = FastAPI(
    title="Nai Miris Smart Agriculture API",
    version="0.1.0",
    description=(
        "Shared API for C1-C4 research components. "
        "Individual component routers are maintained by their owners."
    ),
)

# Development-only browser origins for the Vite frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# Register C2 Yield Prediction API
app.include_router(yield_router)


# System health endpoint
@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "shared-backend",
    }
