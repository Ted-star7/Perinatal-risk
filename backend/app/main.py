"""FastAPI entry point — wires CORS, the routers, and DB startup."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, init_db
from app.routers import accounts, metrics, predictions
from app.seeding import seed_cohorts


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()               # clinics, doctors, predictions
    seed_cohorts(engine)    # combined_* cohort tables (same DB)
    yield


app = FastAPI(title="Perinatal risk API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    # Prod: the deployed frontend origin (set FRONTEND_ORIGIN on Render).
    allow_origins=[settings.frontend_origin],
    # Dev: allow any localhost port (4200 for ng serve, 3000 for the preview).
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(accounts.router)
app.include_router(predictions.router)
app.include_router(metrics.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
