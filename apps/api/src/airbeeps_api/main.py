from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from airbeeps_api.api.router import build_api_router
from airbeeps_api.core.config import get_settings
from airbeeps_api.core.logging import configure_logging


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger = structlog.get_logger("airbeeps.api")
    logger.info("application.startup")
    yield
    logger.info("application.shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
        lifespan=lifespan,
    )
    app.include_router(build_api_router(settings.api_prefix))
    return app


app = create_app()
