from __future__ import annotations

import logging
import os
from pathlib import Path

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


def _load_dotenv() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()

from api.deps import load_state
from api.routers import developers, mortgages, overview, properties, rents, supply, transactions

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(name)s | %(message)s",
)

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
DATA_DIR = os.getenv("DATA_DIR", "data")
PREPROCESS_RAW = os.getenv("PREPROCESS_RAW", "").lower() in ("1", "true", "yes")
STATIC_DIR = os.getenv("STATIC_DIR", "")


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_state(data_dir=DATA_DIR, preprocess_raw=PREPROCESS_RAW)
    yield


app = FastAPI(
    title="Modon Market API",
    version="1.0.0",
    description="Real-estate market analytics API backed by DLD open data.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(overview.router, prefix="/api")
app.include_router(developers.router, prefix="/api")
app.include_router(transactions.router, prefix="/api")
app.include_router(mortgages.router, prefix="/api")
app.include_router(properties.router, prefix="/api")
app.include_router(rents.router, prefix="/api")
app.include_router(supply.router, prefix="/api")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# Serve React SPA — must be registered last so /api/* routes take priority
if STATIC_DIR and Path(STATIC_DIR).is_dir():
    app.mount("/assets", StaticFiles(directory=f"{STATIC_DIR}/assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str) -> FileResponse:
        index = Path(STATIC_DIR) / "index.html"
        return FileResponse(index)
