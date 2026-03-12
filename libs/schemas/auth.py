from pydantic import BaseModel


class AuthenticatedUser(BaseModel):
    user_id: str
    email: str | None = None
    role: str | None = None


class WorkspaceMembership(BaseModel):
    workspace_id: str
    role: str


class CurrentUserResponse(BaseModel):
    user_id: str
    email: str | None = None
    workspaces: list[WorkspaceMembership]


class AuthLoginRequest(BaseModel):
    email: str
    password: str


class AuthLoginResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int | None = None
