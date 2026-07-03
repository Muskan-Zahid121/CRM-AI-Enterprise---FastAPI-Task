from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from tortoise.contrib.fastapi import register_tortoise

from app.controllers.router import api_router
from app.config import settings
from app.database.pgvector import init_pgvector
from app.database.redis_client import close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_pgvector()
    except Exception as exc:
        print(f"pgvector init warning: {exc}")
    yield
    await close_redis()


app = FastAPI(
    title=settings.APP_NAME,
    description="Enterprise AI Sales CRM Platform — FastAPI + pgvector RAG + LangGraph agents",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

register_tortoise(
    app,
    db_url=settings.DATABASE_URL,
    modules={"models": ["app.models.user", "app.models.crm", "app.models.ai"]},
    generate_schemas=True,
    add_exception_handlers=True,
)


@app.get("/", tags=["health"])      
async def health():
    return {"status": "ok", "app": settings.APP_NAME, "version": "2.0.0"}
