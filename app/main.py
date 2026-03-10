from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import capabilities
from app.registry.capabilities_init import register_capabilities
from app.registry.registry import init_registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    registry = init_registry()
    register_capabilities(registry)
    yield


app = FastAPI(title="agentshop", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(capabilities.router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
