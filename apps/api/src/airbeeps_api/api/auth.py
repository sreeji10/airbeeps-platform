from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from libs.schemas.auth import AuthenticatedUser
from services.auth.supabase_jwt import AuthError

from airbeeps_api.dependencies import ServiceContainer, get_container

bearer_scheme = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    container: ServiceContainer = Depends(get_container),
) -> AuthenticatedUser:
    token = credentials.credentials
    try:
        return await container.jwt_verifier.verify(token=token)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
