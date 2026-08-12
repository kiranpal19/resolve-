from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import init_db
from app.api.auth_router import router as auth_router
from app.api.conversations import router as conversations_router
from app.api.cases import router as cases_router
from app.api.audit import router as audit_router
from app.api.agent_console import router as agent_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup DB initialization
    await init_db()
    yield

app = FastAPI(
    title="Resolve: End-to-End Card Servicing Agent API",
    description="Production-quality card servicing agent with deterministic policy engine and immutable hash-chained audit ledger.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(conversations_router)
app.include_router(cases_router)
app.include_router(audit_router)
app.include_router(agent_router)

@app.get("/health")
def health_check():
    return {
        "status": "HEALTHY",
        "service": "Resolve Card Servicing Engine",
        "version": "2026.07.1",
        "architecture": "Deterministic Policy + Cryptographic Audit Ledger"
    }

@app.get("/")
def root():
    return {
        "message": "Welcome to Resolve Card Servicing API",
        "docs_url": "/docs",
        "health_check": "/health"
    }
