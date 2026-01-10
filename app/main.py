from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router

ROOT_DIR = Path(__file__).resolve().parents[1]

app = FastAPI(title="Emoji Art Generator")

app.include_router(api_router)
app.mount("/", StaticFiles(directory=str(ROOT_DIR / "web"), html=True), name="static")
