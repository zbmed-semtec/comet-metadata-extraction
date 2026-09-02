"""
Layer 4 — API entry: FastAPI app wiring (`app.layer_4` routes and middleware).
"""
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.layer_4.endpoints import metadata
from app.layer_4.services.metadata_service import initialize
from app.layer_3.plugins.llm.bootstrap import bootstrap_ollama_if_configured

app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Include routers
app.include_router(metadata.router)


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize services and opportunistically start Ollama when configured."""
    initialize()
    if bootstrap_ollama_if_configured(log_prefix="startup", strict=False):
        return
    print("[startup] Ollama bootstrap was skipped or failed.", file=sys.stderr)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to the Metadata Extractor API",
        "version": settings.api_version,
        "docs": "/docs",
        "health": "/api/health"
    }

