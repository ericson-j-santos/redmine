import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4

from app.core.config import settings
from app.api.propostas import router as propostas_router
from app.db.session import engine
from app.db.base import Base

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    cid = request.headers.get("x-correlation-id") or str(uuid4())
    request.state.correlation_id = cid
    response = await call_next(request)
    response.headers["X-Correlation-Id"] = cid
    return response


@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


app.include_router(propostas_router, prefix=settings.API_PREFIX)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
