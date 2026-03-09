from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from jose import jwt
from jose.exceptions import JOSEError

from airbeeps_api.core.config import Settings
from libs.schemas.auth import AuthenticatedUser


class AuthError(Exception):
    pass


@dataclass
class JwksCache:
    keys_by_kid: dict[str, dict[str, Any]]
    expires_at: datetime


class SupabaseJwtVerifier:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.jwks_url = (
            f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
        )
        self.issuer = f"{settings.supabase_url.rstrip('/')}/auth/v1"
        self._cache: JwksCache | None = None

    async def _get_jwks(self) -> dict[str, dict[str, Any]]:
        now = datetime.now(UTC)
        if self._cache and self._cache.expires_at > now:
            return self._cache.keys_by_kid

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(self.jwks_url)
            response.raise_for_status()
            payload = response.json()

        keys = payload.get("keys", [])
        keys_by_kid = {
            key["kid"]: key for key in keys if isinstance(key, dict) and "kid" in key
        }
        if not keys_by_kid:
            raise AuthError("No keys found in Supabase JWKS")

        self._cache = JwksCache(
            keys_by_kid=keys_by_kid,
            expires_at=now + timedelta(minutes=10),
        )
        return keys_by_kid

    async def verify(self, token: str) -> AuthenticatedUser:
        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            algorithm = header.get("alg")
            if not isinstance(kid, str):
                raise AuthError("JWT header missing kid")
            if not isinstance(algorithm, str):
                raise AuthError("JWT header missing alg")

            jwks = await self._get_jwks()
            key = jwks.get(kid)
            if key is None:
                raise AuthError("No matching key for JWT kid")

            claims = jwt.decode(
                token,
                key=key,
                algorithms=[algorithm],
                audience=self.settings.supabase_jwt_audience,
                issuer=self.issuer,
            )
        except JOSEError as exc:
            raise AuthError("Invalid Supabase JWT") from exc
        except httpx.HTTPError as exc:
            raise AuthError("Failed to fetch Supabase JWKS") from exc

        subject = claims.get("sub")
        if not isinstance(subject, str):
            raise AuthError("JWT missing subject")

        email = claims.get("email")
        role = claims.get("role")
        return AuthenticatedUser(
            user_id=subject,
            email=email if isinstance(email, str) else None,
            role=role if isinstance(role, str) else None,
        )
