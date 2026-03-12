import httpx
from fastapi import APIRouter, Depends, HTTPException
from libs.schemas.auth import (
    AuthenticatedUser,
    AuthLoginRequest,
    AuthLoginResponse,
    CurrentUserResponse,
)
from services.platform.service import PlatformService
from sqlalchemy.ext.asyncio import AsyncSession

from airbeeps_api.api.auth import get_current_user
from airbeeps_api.db.session import get_db_session
from airbeeps_api.dependencies import ServiceContainer, get_container

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AuthLoginResponse)
async def login_with_password(
    request: AuthLoginRequest,
    container: ServiceContainer = Depends(get_container),
) -> AuthLoginResponse:
    supabase_url = container.settings.supabase_url.rstrip("/")
    login_url = f"{supabase_url}/auth/v1/token?grant_type=password"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                login_url,
                headers={
                    "apikey": container.settings.supabase_publishable_key,
                    "Content-Type": "application/json",
                },
                json={"email": request.email, "password": request.password},
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Failed to reach auth provider") from exc

    if response.status_code >= 400:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    payload = response.json()
    token = payload.get("access_token")
    if not isinstance(token, str) or not token:
        raise HTTPException(status_code=502, detail="Auth provider returned no access token")

    refresh_token = payload.get("refresh_token")
    token_type = payload.get("token_type")
    expires_in = payload.get("expires_in")
    return AuthLoginResponse(
        access_token=token,
        refresh_token=refresh_token if isinstance(refresh_token, str) else None,
        token_type=token_type if isinstance(token_type, str) else "bearer",
        expires_in=expires_in if isinstance(expires_in, int) else None,
    )


@router.get("/me", response_model=CurrentUserResponse)
async def get_me(
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CurrentUserResponse:
    service = PlatformService(session)
    workspaces = await service.list_user_workspaces(user_id=user.user_id)
    return CurrentUserResponse(user_id=user.user_id, email=user.email, workspaces=workspaces)
