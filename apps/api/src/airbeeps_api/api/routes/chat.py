from fastapi import APIRouter, Depends
from libs.schemas.chat import ChatRunRequest, ChatRunResponse

from airbeeps_api.dependencies import ServiceContainer, get_container

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/runs", response_model=ChatRunResponse)
def create_chat_run(
    request: ChatRunRequest,
    container: ServiceContainer = Depends(get_container),
) -> ChatRunResponse:
    return container.runtime.run(request=request)
