from pathlib import Path

import yaml
from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse

from app.auth import verify_internal_auth
from app.routers import details, recent, search

app = FastAPI(
    title="ISLI Maroc Marchés Publics Scanner",
    description="USR v2.0 skill for searching Moroccan public procurement announcements.",
    version="1.0.0",
)

app.include_router(search.router, dependencies=[Depends(verify_internal_auth)])
app.include_router(details.router, dependencies=[Depends(verify_internal_auth)])
app.include_router(recent.router, dependencies=[Depends(verify_internal_auth)])


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/.well-known/isli-manifest")
async def manifest() -> dict:
    manifest_path = Path(__file__).resolve().parent.parent / "isli-skill.yaml"
    with manifest_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@app.exception_handler(ValueError)
async def value_error_handler(_, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})
