"""
Configuration management for MCP Image Generation Server.

This module provides a centralized configuration system using Pydantic BaseSettings,
supporting both environment variables and .env files.
"""

import os
from typing import List, Literal, Optional
from urllib.parse import urlparse
from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerConfig(BaseSettings):
    """
    Configuration for MCP Image Generation Server.

    Supports both stdio and HTTP transports with flexible configuration
    through environment variables or .env files.
    """

    # ========== Transport Configuration ==========
    transport: Literal["http", "stdio"] = Field(
        default="http",
        description="Transport protocol to use (http or stdio)",
        validation_alias=AliasChoices('MCP_TRANSPORT', 'transport')
    )

    host: str = Field(
        default="127.0.0.1",
        description="Host to bind HTTP server (only for http transport)",
        validation_alias=AliasChoices('MCP_HOST', 'host')
    )

    port: int = Field(
        default=8000,
        description="Port to bind HTTP server (only for http transport)",
        validation_alias=AliasChoices('MCP_PORT', 'port')
    )

    # ========== Security Configuration ==========
    auth_token: Optional[str] = Field(
        default=None,
        description="Bearer token for authentication (optional, recommended for production)",
        validation_alias=AliasChoices('MCP_AUTH_TOKEN', 'auth_token')
    )

    allowed_origins: List[str] = Field(
        default=["*"],
        description="Allowed origins for CORS and Origin validation",
        validation_alias=AliasChoices('MCP_ALLOWED_ORIGINS', 'allowed_origins')
    )

    # ========== Session Management ==========
    session_timeout: int = Field(
        default=3600,
        description="Session timeout in seconds (default: 1 hour)",
        validation_alias=AliasChoices('MCP_SESSION_TIMEOUT', 'session_timeout')
    )

    enable_sessions: bool = Field(
        default=True,
        description="Enable session management for HTTP transport",
        validation_alias=AliasChoices('MCP_ENABLE_SESSIONS', 'enable_sessions')
    )

    session_cleanup_interval: int = Field(
        default=300,
        description="Interval in seconds between session cleanup runs (default: 5 minutes)",
        validation_alias=AliasChoices('MCP_SESSION_CLEANUP_INTERVAL', 'session_cleanup_interval')
    )

    # ========== SSE Configuration ==========
    enable_sse: bool = Field(
        default=True,
        description="Enable Server-Sent Events for streaming responses",
        validation_alias=AliasChoices('MCP_ENABLE_SSE', 'enable_sse')
    )

    sse_keepalive_interval: int = Field(
        default=30,
        description="SSE keepalive ping interval in seconds",
        validation_alias=AliasChoices('MCP_SSE_KEEPALIVE', 'sse_keepalive_interval')
    )

    # ========== Image Generation Configuration ==========
    image_save_dir: str = Field(
        default="./generated_images",
        description="Directory to save generated images",
        validation_alias=AliasChoices('MCP_IMAGE_SAVE_DIR', 'image_save_dir')
    )

    public_base_url: Optional[str] = Field(
        default=None,
        description=(
            "Public base URL for generated image access in HTTP mode "
            "(for example: https://mcp.example.com)"
        ),
        validation_alias=AliasChoices('MCP_PUBLIC_BASE_URL', 'public_base_url')
    )

    image_record_ttl: int = Field(
        default=86400,
        description="Image metadata cache TTL in seconds for get_image_data tool",
        validation_alias=AliasChoices('MCP_IMAGE_RECORD_TTL', 'image_record_ttl')
    )

    get_image_data_max_bytes: int = Field(
        default=10 * 1024 * 1024,
        description="Maximum image size in bytes allowed for get_image_data base64 response",
        validation_alias=AliasChoices('MCP_GET_IMAGE_DATA_MAX_BYTES', 'get_image_data_max_bytes')
    )

    # ========== Provider Configuration ==========
    # Tencent Hunyuan
    tencent_secret_id: Optional[str] = Field(
        default=None,
        description="Tencent Cloud Secret ID for Hunyuan API",
        validation_alias=AliasChoices('TENCENT_SECRET_ID', 'tencent_secret_id')
    )

    tencent_secret_key: Optional[str] = Field(
        default=None,
        description="Tencent Cloud Secret Key for Hunyuan API",
        validation_alias=AliasChoices('TENCENT_SECRET_KEY', 'tencent_secret_key')
    )

    # OpenAI DALL-E
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key for DALL-E 3",
        validation_alias=AliasChoices('OPENAI_API_KEY', 'openai_api_key')
    )

    openai_base_url: Optional[str] = Field(
        default=None,
        description="Custom OpenAI API base URL (optional)",
        validation_alias=AliasChoices('OPENAI_BASE_URL', 'openai_base_url')
    )

    # Doubao (ByteDance) - New Ark API
    doubao_api_key: Optional[str] = Field(
        default=None,
        description="Doubao API Key for ByteDance Ark API",
        validation_alias=AliasChoices('DOUBAO_API_KEY', 'doubao_api_key')
    )

    doubao_endpoint: Optional[str] = Field(
        default=None,
        description="Custom Doubao API endpoint (optional, default: https://ark.cn-beijing.volces.com)",
        validation_alias=AliasChoices('DOUBAO_ENDPOINT', 'doubao_endpoint')
    )

    doubao_model: str = Field(
        default="doubao-seedream-4.0",
        description="Doubao model name (doubao-seedream-4.0, doubao-seedream-4.5, etc.)",
        validation_alias=AliasChoices('DOUBAO_MODEL', 'doubao_model')
    )

    # ========== Logging Configuration ==========
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
        validation_alias=AliasChoices('MCP_LOG_LEVEL', 'log_level')
    )

    # ========== Development/Debug Configuration ==========
    debug: bool = Field(
        default=False,
        description="Enable debug mode with verbose logging",
        validation_alias=AliasChoices('MCP_DEBUG', 'debug')
    )

    # Pydantic v2 configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore extra environment variables
    )

    def is_http_transport(self) -> bool:
        """Check if HTTP transport is configured."""
        return self.transport == "http"

    def is_stdio_transport(self) -> bool:
        """Check if stdio transport is configured."""
        return self.transport == "stdio"

    def auth_enabled(self) -> bool:
        """Check if authentication is enabled."""
        return self.auth_token is not None and len(self.auth_token) > 0

    def get_provider_credentials(self) -> dict:
        """
        Get all provider credentials as a dictionary.

        Returns:
            dict: Dictionary containing available provider credentials
        """
        credentials = {}

        # Hunyuan credentials
        if self.tencent_secret_id and self.tencent_secret_key:
            credentials["hunyuan"] = {
                "secret_id": self.tencent_secret_id,
                "secret_key": self.tencent_secret_key
            }

        # OpenAI credentials
        if self.openai_api_key:
            credentials["openai"] = {
                "api_key": self.openai_api_key,
                "base_url": self.openai_base_url
            }

        # Doubao credentials (New Ark API)
        if self.doubao_api_key:
            credentials["doubao"] = {
                "api_key": self.doubao_api_key,
                "endpoint": self.doubao_endpoint,
                "model": self.doubao_model
            }

        return credentials

    def validate_transport_config(self) -> None:
        """
        Validate transport-specific configuration.

        Raises:
            ValueError: If configuration is invalid for selected transport
        """
        if self.is_http_transport():
            # Validate HTTP configuration
            if self.port < 1 or self.port > 65535:
                raise ValueError(f"Invalid port number: {self.port}")

            if not self.host:
                raise ValueError("Host cannot be empty for HTTP transport")

            # Warn if authentication is disabled in non-localhost deployments
            if not self.auth_enabled() and self.host != "127.0.0.1" and self.host != "localhost":
                import sys
                print(
                    "WARNING: Authentication is disabled for non-localhost deployment. "
                    "Consider setting MCP_AUTH_TOKEN for security.",
                    file=sys.stderr
                )

            if self.public_base_url:
                parsed = urlparse(self.public_base_url)
                if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                    raise ValueError(
                        "Invalid MCP_PUBLIC_BASE_URL. Expected absolute http(s) URL, "
                        f"got: {self.public_base_url}"
                    )

            if self.image_record_ttl <= 0:
                raise ValueError("MCP_IMAGE_RECORD_TTL must be greater than 0")

            if self.get_image_data_max_bytes <= 0:
                raise ValueError("MCP_GET_IMAGE_DATA_MAX_BYTES must be greater than 0")

    def __str__(self) -> str:
        """String representation of config (safe, no secrets)."""
        return (
            f"ServerConfig(transport={self.transport}, "
            f"host={self.host if self.is_http_transport() else 'N/A'}, "
            f"port={self.port if self.is_http_transport() else 'N/A'}, "
            f"auth_enabled={self.auth_enabled()}, "
            f"public_base_url={'configured' if self.public_base_url else 'auto'}, "
            f"image_record_ttl={self.image_record_ttl}, "
            f"get_image_data_max_bytes={self.get_image_data_max_bytes}, "
            f"providers={list(self.get_provider_credentials().keys())})"
        )


def load_config() -> ServerConfig:
    """
    Load configuration from environment variables and .env file.

    Returns:
        ServerConfig: Loaded and validated configuration
    """
    config = ServerConfig()
    config.validate_transport_config()
    return config


# Export for convenience
__all__ = ["ServerConfig", "load_config"]
