from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.auth import Session, router as auth_router
from app.db import engine
from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(title="Async CRM", version="0.1.0", lifespan=lifespan)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}


@app.get("/ready", tags=["Health"])
async def ready(session: Session):
    try:
        await session.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError):
        raise HTTPException(503, "Database unavailable")
    return {"status": "ready"}
