"""
Modular, auth-ready security abstractions for the monitoring system.
Allows current prototype workflows while structuring clean injection points
for future JWT, OAuth2, or API Key authentication without route changes.
"""

from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

# Optional bearer scheme that does not block requests when credentials are absent
optional_bearer = HTTPBearer(auto_error=False)
optional_api_key = APIKeyHeader(name="X-API-Key", auto_error=False)


class UserContext(BaseModel):
    """Authenticated user/service account context model."""

    user_id: str = Field("anonymous", description="Unique user or service account identifier")
    role: str = Field("viewer", description="Access role (admin, operator, viewer)")
    is_authenticated: bool = Field(False, description="Authentication status flag")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional context claims")


async def get_current_user_optional(
    token: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
    api_key: str | None = Depends(optional_api_key),
) -> UserContext:
    """
    Dependency extracting user identity if credentials are provided.
    Permits unauthenticated traffic in the prototype phase while establishing
    the foundation for JWT / API-key verification.
    """
    if token and token.credentials:
        # Placeholder for future JWT signature verification / decoding
        return UserContext(
            user_id="bearer_authenticated_client",
            role="operator",
            is_authenticated=True,
            metadata={"auth_type": "bearer"},
        )

    if api_key:
        return UserContext(
            user_id=f"api_key_client_{api_key[:6]}",
            role="operator",
            is_authenticated=True,
            metadata={"auth_type": "api_key"},
        )

    return UserContext(user_id="anonymous", role="viewer", is_authenticated=False)


async def require_authenticated_user(
    user: UserContext = Depends(get_current_user_optional),
) -> UserContext:
    """
    Dependency that enforces authentication when activated on sensitive routes.
    """
    if not user.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a valid Bearer token or X-API-Key header.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
