
"""Shared API entry point for the Nai Miris Smart Agriculture system."""

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

# C2 - Yield Prediction Router
from app.c2.yield_prediction.routes import router as yield_router
from app.c2.microclimate.api.routes import router as microclimate_router
from app.c2.microclimate.api.http import MicroclimateBodyLimit
from app.c2.access.http import AccessHTTP, validation_error_handler
from app.c2.access.routes import router as access_router
from app.c2.access.routes import local_only, research_access, yield_access


app = FastAPI(
    title="Nai Miris Smart Agriculture API",
    version="0.1.0",
    description=(
        "Shared API for C1-C4 research components. "
        "Individual component routers are maintained by their owners."
    ),
)

app.add_middleware(MicroclimateBodyLimit)
app.add_middleware(AccessHTTP)
app.add_exception_handler(RequestValidationError, validation_error_handler)

# Development-only browser origins for the Vite frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["*"],
    allow_credentials=True,
)


# Register C2 Yield Prediction API
app.include_router(yield_router,dependencies=[Depends(local_only),Depends(yield_access)])
app.include_router(microclimate_router,dependencies=[Depends(local_only),Depends(research_access)])
app.include_router(access_router)


# System health endpoint
@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "shared-backend",
    }
