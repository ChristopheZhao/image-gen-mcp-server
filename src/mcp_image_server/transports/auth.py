"""
Authentication and authorization for MCP HTTP server.

This module provides:
- Bearer token authentication
- Origin header validation (prevents DNS rebinding attacks)
- Starlette middleware integration
"""

import secrets
from typing import List, Optional
from starlette.authentication import (
    AuthenticationBackend,
    AuthenticationError,
    AuthCredentials,
    BaseUser,
    SimpleUser
)
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.requests import HTTPConnection, Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp


def _is_whitelisted_path(path: str, whitelist_paths: List[str]) -> bool:
    """
    Check if request path is whitelisted.

    Supports exact match and prefix wildcard pattern:
    - exact: /health
    - prefix: /images*
    """
    for pattern in whitelist_paths:
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            if path.startswith(prefix):
                return True
        elif path == pattern:
            return True
    return False


class BearerTokenUser(BaseUser):
    """User authenticated via Bearer token."""

    def __init__(self, username: str = "api_user"):
        self.username = username

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def display_name(self) -> str:
        return self.username


class BearerTokenAuthBackend(AuthenticationBackend):
    """Authentication backend that validates Bearer tokens."""

    def __init__(self, expected_token: str):
        """
        Initialize authentication backend.

        Args:
            expected_token: The expected Bearer token
        """
        self.expected_token = expected_token

    async def authenticate(
        self, conn: HTTPConnection
    ) -> Optional[tuple[AuthCredentials, BaseUser]]:
        """
        Authenticate request based on Authorization header.

        Args:
            conn: HTTP connection

        Returns:
            Optional tuple of (credentials, user) if authenticated, None otherwise
        """
        # Skip authentication for health check endpoint
        if conn.url.path == "/health":
            return None

        # Get Authorization header
        auth_header = conn.headers.get("Authorization")

        if not auth_header:
            # No auth header provided
            return None

        # Parse Bearer token
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            # Invalid format
            return None

        token = parts[1]

        # Validate token using constant-time comparison (prevents timing attacks)
        if not secrets.compare_digest(token, self.expected_token):
            # Invalid token
            return None

        # Token is valid
        return AuthCredentials(["authenticated"]), BearerTokenUser()


def validate_bearer_token(token: str, expected: str) -> bool:
    """
    Validate a Bearer token using constant-time comparison.

    Args:
        token: The token to validate
        expected: The expected token

    Returns:
        bool: True if token is valid
    """
    if not token or not expected:
        return False

    return secrets.compare_digest(token, expected)


def validate_origin(origin: str, allowed_origins: List[str]) -> bool:
    """
    Validate Origin header against allowed origins.

    This prevents DNS rebinding attacks and ensures requests come from
    trusted origins.

    Args:
        origin: The Origin header value
        allowed_origins: List of allowed origins (supports wildcards)

    Returns:
        bool: True if origin is allowed
    """
    if not origin:
        # No origin header - allow (typically for non-browser clients)
        return True

    # Check if wildcard is allowed
    if "*" in allowed_origins:
        return True

    # Check exact match
    if origin in allowed_origins:
        return True

    # Check for localhost variants (development)
    if origin in ["http://localhost", "http://127.0.0.1", "https://localhost", "https://127.0.0.1"]:
        localhost_found = any(
            o in ["http://localhost", "http://127.0.0.1", "https://localhost", "https://127.0.0.1", "*"]
            for o in allowed_origins
        )
        if localhost_found:
            return True

    # Check for pattern matching (basic wildcard support)
    for allowed in allowed_origins:
        if "*" in allowed:
            # Simple wildcard matching (e.g., "https://*.example.com")
            pattern = allowed.replace("*", ".*")
            import re
            if re.match(pattern, origin):
                return True

    return False


class AuthRequiredMiddleware:
    """
    Middleware that requires authentication for all requests except whitelisted paths.

    Returns 401 Unauthorized if authentication is missing or invalid.
    """

    def __init__(
        self,
        app: ASGIApp,
        whitelist_paths: Optional[List[str]] = None
    ):
        """
        Initialize auth middleware.

        Args:
            app: ASGI application
            whitelist_paths: Paths that don't require authentication
        """
        self.app = app
        self.whitelist_paths = whitelist_paths or ["/health"]

    async def __call__(self, scope, receive, send):
        """Process request with authentication check."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Check if path is whitelisted
        path = scope["path"]
        if _is_whitelisted_path(path, self.whitelist_paths):
            await self.app(scope, receive, send)
            return

        # Check if user is authenticated
        user = scope.get("user")
        if user is None or not user.is_authenticated:
            # Return 401 Unauthorized
            response = JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32001,
                        "message": "Unauthorized: Missing or invalid authentication"
                    },
                    "id": None
                },
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"}
            )
            await response(scope, receive, send)
            return

        # User is authenticated, continue
        await self.app(scope, receive, send)


class OriginValidationMiddleware:
    """
    Middleware that validates Origin header to prevent DNS rebinding attacks.

    Returns 403 Forbidden if origin is not allowed.
    """

    def __init__(
        self,
        app: ASGIApp,
        allowed_origins: List[str],
        whitelist_paths: Optional[List[str]] = None
    ):
        """
        Initialize origin validation middleware.

        Args:
            app: ASGI application
            allowed_origins: List of allowed origins
            whitelist_paths: Paths that don't require origin validation
        """
        self.app = app
        self.allowed_origins = allowed_origins
        self.whitelist_paths = whitelist_paths or ["/health"]

    async def __call__(self, scope, receive, send):
        """Process request with origin validation."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Check if path is whitelisted
        path = scope["path"]
        if _is_whitelisted_path(path, self.whitelist_paths):
            await self.app(scope, receive, send)
            return

        # Get Origin header
        headers = dict(scope.get("headers", []))
        origin = headers.get(b"origin", b"").decode("utf-8")

        # Validate origin
        if not validate_origin(origin, self.allowed_origins):
            # Return 403 Forbidden
            response = JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32002,
                        "message": f"Forbidden: Origin '{origin}' is not allowed"
                    },
                    "id": None
                },
                status_code=403
            )
            await response(scope, receive, send)
            return

        # Origin is valid, continue
        await self.app(scope, receive, send)


def create_auth_middleware(auth_token: str) -> Middleware:
    """
    Create authentication middleware with Bearer token backend.

    Args:
        auth_token: Expected Bearer token

    Returns:
        Middleware: Starlette authentication middleware
    """
    return Middleware(
        AuthenticationMiddleware,
        backend=BearerTokenAuthBackend(auth_token)
    )


# Export for convenience
__all__ = [
    "BearerTokenAuthBackend",
    "BearerTokenUser",
    "validate_bearer_token",
    "validate_origin",
    "AuthRequiredMiddleware",
    "OriginValidationMiddleware",
    "create_auth_middleware"
]
