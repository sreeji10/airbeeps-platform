from fastapi import APIRouter

from airbeeps_api.api.routes.agents import router as agents_router
from airbeeps_api.api.routes.auth import router as auth_router
from airbeeps_api.api.routes.chat import router as chat_router
from airbeeps_api.api.routes.datasets import router as datasets_router
from airbeeps_api.api.routes.evaluations import router as evaluations_router
from airbeeps_api.api.routes.health import router as health_router
from airbeeps_api.api.routes.ingestion import router as ingestion_router
from airbeeps_api.api.routes.jobs import router as jobs_router
from airbeeps_api.api.routes.memory import router as memory_router
from airbeeps_api.api.routes.projects import router as projects_router
from airbeeps_api.api.routes.prompts import router as prompts_router
from airbeeps_api.api.routes.usage import router as usage_router
from airbeeps_api.api.routes.workspaces import router as workspaces_router


def build_api_router(api_prefix: str) -> APIRouter:
    router = APIRouter()
    router.include_router(health_router)
    versioned = APIRouter(prefix=api_prefix)
    versioned.include_router(agents_router)
    versioned.include_router(auth_router)
    versioned.include_router(chat_router)
    versioned.include_router(datasets_router)
    versioned.include_router(evaluations_router)
    versioned.include_router(ingestion_router)
    versioned.include_router(jobs_router)
    versioned.include_router(memory_router)
    versioned.include_router(prompts_router)
    versioned.include_router(projects_router)
    versioned.include_router(usage_router)
    versioned.include_router(workspaces_router)
    router.include_router(versioned)
    return router
