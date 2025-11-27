"""FastAPI main application."""

from __future__ import annotations

from contextlib import asynccontextmanager
import sys
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import get_settings
from utils.logging import get_logger, setup_logging
from metadata_extractor.routers.hardware_router import router as crawler_router
from .v1.endpoints import hardware, matcher, metadata, models

logger = get_logger(__name__)

# Ensure project src is on sys.path for direct execution/debugging
SRC_ROOT = Path(__file__).resolve().parents[2]
if str(SRC_ROOT) not in sys.path:
    sys.path.append(str(SRC_ROOT))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    setup_logging()
    settings = get_settings()
    logger.info(f"Starting ChooseYourHardware API v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ChooseYourHardware API")


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    settings = get_settings()

    app = FastAPI(
        title="ChooseYourHardware API",
        description="API for analyzing ML models and hardware specifications",
        version=settings.app_version,
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(models.router, prefix="/api/v1", tags=["models"])
    app.include_router(hardware.router, prefix="/api/v1", tags=["hardware"])
    app.include_router(metadata.router, prefix="/api/v1")
    app.include_router(matcher.router, prefix="/api/v1", tags=["matcher"])
    app.include_router(crawler_router, prefix="/api/v1", tags=["hardware-crawler"])

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "version": settings.app_version}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "choose_your_hardware.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development",
    )
