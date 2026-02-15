"""
MCP Image Generation Server - HTTP Transport Implementation.

This module implements the MCP server with Streamable HTTP transport,
migrated from FastMCP (stdio) to native Server class for remote access support.
"""

import os
import sys
import base64
import time
import json
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path

from mcp.server import Server
import mcp.types as types
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.middleware import Middleware
import uvicorn

from ..config import ServerConfig
from .session_manager import SessionManager
from .auth import create_auth_middleware, AuthRequiredMiddleware, OriginValidationMiddleware
from .http import MCPHTTPHandler, health_check
from ..providers import ProviderManager


def debug_print(*args, **kwargs):
    """Print debug messages to stderr."""
    print(*args, file=sys.stderr, **kwargs)


class MCPImageServerHTTP:
    """MCP Image Generation Server with HTTP transport."""

    TOOL_RESULT_VERSION = "1.0"

    def __init__(self, config: ServerConfig):
        """
        Initialize HTTP server.

        Args:
            config: Server configuration
        """
        self.config = config

        # Initialize MCP Server
        self.server = Server("Multi-API Image Generation MCP Service")

        # Initialize provider manager
        self.provider_manager = ProviderManager()

        # Initialize session manager
        self.session_manager = SessionManager(
            timeout=config.session_timeout,
            cleanup_interval=config.session_cleanup_interval
        )

        # Initialize HTTP handler
        self.http_handler = MCPHTTPHandler(
            session_manager=self.session_manager,
            enable_sse=config.enable_sse,
            debug=config.debug
        )

        # Set JSON-RPC handler
        self.http_handler.set_json_rpc_handler(self._handle_json_rpc)

        # Register server capabilities
        self._register_capabilities()

        debug_print(f"Server initialized: {config}")

    def _register_capabilities(self) -> None:
        """Register all server capabilities (tools, resources, prompts)."""
        # Register list_tools handler
        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            return await self._list_tools()

        # Register call_tool handler
        @self.server.call_tool()
        async def handle_call_tool(
            name: str,
            arguments: dict
        ) -> list[types.TextContent | types.ImageContent]:
            return await self._call_tool(name, arguments)

        # Register list_resources handler
        @self.server.list_resources()
        async def handle_list_resources() -> list[types.Resource]:
            return await self._list_resources()

        # Register read_resource handler
        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            return await self._read_resource(uri)

        # Register list_prompts handler
        @self.server.list_prompts()
        async def handle_list_prompts() -> list[types.Prompt]:
            return await self._list_prompts()

        # Register get_prompt handler
        @self.server.get_prompt()
        async def handle_get_prompt(
            name: str,
            arguments: dict
        ) -> types.GetPromptResult:
            return await self._get_prompt(name, arguments)

    async def _list_tools(self) -> list[types.Tool]:
        """List available tools."""
        return [
            types.Tool(
                name="generate_image",
                description="Generate image based on prompt using multiple API providers (Hunyuan, OpenAI, Doubao)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "Image description text"
                        },
                        "provider": {
                            "type": "string",
                            "description": "API provider to use. Available: hunyuan, openai, doubao. Leave empty to use default provider",
                            "default": ""
                        },
                        "style": {
                            "type": "string",
                            "description": "Image style. Format: 'provider:style' or just 'style' for default provider",
                            "default": ""
                        },
                        "resolution": {
                            "type": "string",
                            "description": "Image resolution. Format: 'provider:resolution' or just 'resolution' for default provider",
                            "default": ""
                        },
                        "negative_prompt": {
                            "type": "string",
                            "description": "Negative prompt, describes content you don't want in the image",
                            "default": ""
                        },
                        "file_prefix": {
                            "type": "string",
                            "description": "Optional prefix for the output filename (English only)",
                            "default": ""
                        }
                    },
                    "required": ["prompt"]
                },
                outputSchema=self._build_generate_image_output_schema()
            )
        ]

    def _build_generate_image_output_schema(self) -> Dict[str, Any]:
        """Build the fixed output schema for generate_image."""
        return {
            "type": "object",
            "properties": {
                "version": {"type": "string"},
                "ok": {"type": "boolean"},
                "images": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "provider": {"type": "string"},
                            "mime_type": {"type": "string"},
                            "file_name": {"type": ["string", "null"]},
                            "local_path": {"type": ["string", "null"]},
                            "url": {"type": ["string", "null"]},
                            "size_bytes": {"type": "integer"},
                            "revised_prompt": {"type": ["string", "null"]},
                            "save_error": {"type": ["string", "null"]}
                        },
                        "required": [
                            "id",
                            "provider",
                            "mime_type",
                            "file_name",
                            "local_path",
                            "url",
                            "size_bytes",
                            "revised_prompt",
                            "save_error"
                        ]
                    }
                },
                "error": {
                    "type": ["object", "null"],
                    "properties": {
                        "code": {"type": "string"},
                        "message": {"type": "string"},
                        "details": {"type": "object"}
                    },
                    "required": ["code", "message", "details"]
                }
            },
            "required": ["version", "ok", "images", "error"]
        }

    def _build_tool_success_result(self, images: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build a successful fixed-structure tool result."""
        return {
            "version": self.TOOL_RESULT_VERSION,
            "ok": True,
            "images": images,
            "error": None
        }

    def _build_tool_error_result(
        self,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build a failed fixed-structure tool result."""
        return {
            "version": self.TOOL_RESULT_VERSION,
            "ok": False,
            "images": [],
            "error": {
                "code": code,
                "message": message,
                "details": details or {}
            }
        }

    def _strip_binary_fields(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Remove binary-only fields from structured payload."""
        payload: Dict[str, Any] = {
            "version": result.get("version"),
            "ok": result.get("ok"),
            "images": [],
            "error": result.get("error")
        }

        images = result.get("images")
        if isinstance(images, list):
            for image in images:
                if isinstance(image, dict):
                    payload["images"].append({
                        key: value
                        for key, value in image.items()
                        if key != "base64_data"
                    })
                else:
                    payload["images"].append(image)

        return payload

    def _tool_result_to_content(
        self,
        result: Dict[str, Any],
        text_payload: Optional[Dict[str, Any]] = None
    ) -> list[types.TextContent | types.ImageContent]:
        """Convert fixed tool result to text + optional image content payload."""
        content: list[types.TextContent | types.ImageContent] = []

        if text_payload is None:
            text_payload = self._strip_binary_fields(result)
        content.append(
            types.TextContent(
                type="text",
                text=json.dumps(text_payload, ensure_ascii=False)
            )
        )

        images = result.get("images", [])
        if isinstance(images, list):
            for image in images:
                if not isinstance(image, dict):
                    continue
                base64_data = image.get("base64_data")
                if not base64_data:
                    continue
                content.append(
                    types.ImageContent(
                        type="image",
                        data=base64_data,
                        mimeType=image.get("mime_type", "image/jpeg")
                    )
                )

        return content

    def _image_extension_from_mime(self, mime_type: str) -> str:
        """Infer filename extension from image MIME type."""
        mime = (mime_type or "").lower()
        extension_map = {
            "image/jpeg": "jpg",
            "image/jpg": "jpg",
            "image/png": "png",
            "image/webp": "webp",
            "image/gif": "gif",
            "image/bmp": "bmp"
        }
        return extension_map.get(mime, "img")

    async def _call_tool_structured(
        self,
        name: str,
        arguments: dict
    ) -> Dict[str, Any]:
        """Execute tool and return fixed structured result."""
        if name == "generate_image":
            return await self._generate_image(**arguments)

        return self._build_tool_error_result(
            code="unknown_tool",
            message=f"Unknown tool: {name}",
            details={"tool_name": name}
        )

    async def _call_tool(
        self,
        name: str,
        arguments: dict
    ) -> list[types.TextContent | types.ImageContent]:
        """Execute tool by name."""
        structured_result = await self._call_tool_structured(name, arguments)
        return self._tool_result_to_content(structured_result)

    async def _generate_image(
        self,
        prompt: str,
        provider: str = "",
        style: str = "",
        resolution: str = "",
        negative_prompt: str = "",
        file_prefix: str = ""
    ) -> Dict[str, Any]:
        """Generate image using provider APIs."""
        debug_print(f"generate_image called: prompt={prompt}, provider={provider}, style={style}, resolution={resolution}")

        # Parse provider from style/resolution if not explicitly specified
        actual_provider = provider
        actual_style = style
        actual_resolution = resolution

        # Parse provider:style format
        if ":" in style and not actual_provider:
            provider_from_style, actual_style = style.split(":", 1)
            actual_provider = provider_from_style

        # Parse provider:resolution format
        if ":" in resolution and not actual_provider:
            provider_from_res, actual_resolution = resolution.split(":", 1)
            if not actual_provider:
                actual_provider = provider_from_res

        # Use default provider if none specified
        if not actual_provider:
            actual_provider = self.provider_manager.default_provider
            if not actual_provider:
                available_providers = self.provider_manager.get_available_providers()
                error_text = f"No provider specified and no default provider available. Available providers: {available_providers}"
                debug_print(f"[ERROR] {error_text}")
                return self._build_tool_error_result(
                    code="provider_missing",
                    message=error_text,
                    details={"available_providers": available_providers}
                )

        # Get the provider instance
        provider_instance = self.provider_manager.get_provider(actual_provider)
        if not provider_instance:
            available_providers = self.provider_manager.get_available_providers()
            error_text = f"Provider '{actual_provider}' not available. Available providers: {available_providers}"
            debug_print(f"[ERROR] {error_text}")
            return self._build_tool_error_result(
                code="provider_unavailable",
                message=error_text,
                details={
                    "provider": actual_provider,
                    "available_providers": available_providers
                }
            )

        #  Validate style
        if actual_style and not provider_instance.validate_style(actual_style):
            available_styles = provider_instance.get_available_styles()
            error_text = f"Invalid style '{actual_style}' for provider '{actual_provider}'. Available styles: {list(available_styles.keys())}"
            debug_print(f"[ERROR] {error_text}")
            return self._build_tool_error_result(
                code="invalid_style",
                message=error_text,
                details={
                    "provider": actual_provider,
                    "style": actual_style,
                    "available_styles": list(available_styles.keys())
                }
            )

        # Validate resolution
        if actual_resolution and not provider_instance.validate_resolution(actual_resolution):
            available_resolutions = provider_instance.get_available_resolutions()
            error_text = f"Invalid resolution '{actual_resolution}' for provider '{actual_provider}'. Available resolutions: {list(available_resolutions.keys())}"
            debug_print(f"[ERROR] {error_text}")
            return self._build_tool_error_result(
                code="invalid_resolution",
                message=error_text,
                details={
                    "provider": actual_provider,
                    "resolution": actual_resolution,
                    "available_resolutions": list(available_resolutions.keys())
                }
            )

        # Set defaults if not provided
        if not actual_style:
            default_styles = provider_instance.get_available_styles()
            actual_style = list(default_styles.keys())[0] if default_styles else "default"

        if not actual_resolution:
            default_resolutions = provider_instance.get_available_resolutions()
            actual_resolution = list(default_resolutions.keys())[0] if default_resolutions else "1024x1024"

        debug_print(f"Using provider: {actual_provider}, style: {actual_style}, resolution: {actual_resolution}")

        try:
            # Progress tracking
            async def print_progress():
                count = 0
                while True:
                    count += 1
                    debug_print(f"[Progress] Generating image with {actual_provider}... waited {count*5} seconds")
                    await asyncio.sleep(5)

            progress_task = asyncio.create_task(print_progress())

            try:
                # Call image generation
                debug_print(f"Calling {actual_provider} provider...")
                result = await self.provider_manager.generate_images(
                    query=prompt,
                    provider_name=actual_provider,
                    style=actual_style,
                    resolution=actual_resolution,
                    negative_prompt=negative_prompt
                )

                # Cancel progress task
                progress_task.cancel()
                try:
                    await progress_task
                except asyncio.CancelledError:
                    pass

                debug_print(f"Image generation completed, result type: {type(result)}")

                # Check result
                if not result or len(result) == 0:
                    error_msg = "Image generation failed: No result"
                    return self._build_tool_error_result(
                        code="generation_failed",
                        message=error_msg
                    )

                # Check for errors
                if "error" in result[0]:
                    error_msg = result[0]["error"]
                    debug_print(f"[ERROR] {error_msg}")
                    return self._build_tool_error_result(
                        code="provider_error",
                        message=f"Image generation error: {error_msg}",
                        details={"provider": actual_provider}
                    )

                # Check image content
                if "content" in result[0]:
                    # Base64 encoded image
                    image_data = result[0]["content"]
                    image_mime_type = result[0].get("content_type", "image/jpeg")

                    try:
                        # Decode image first so errors are explicit and size is available.
                        image_data_bytes = base64.b64decode(image_data)
                    except Exception as e:
                        error_msg = f"Failed to decode image content: {str(e)}"
                        debug_print(f"[ERROR] {error_msg}")
                        return self._build_tool_error_result(
                            code="decode_failed",
                            message=error_msg,
                            details={"provider": actual_provider}
                        )

                    # Build filename using MIME type.
                    timestamp = int(time.time())
                    extension = self._image_extension_from_mime(image_mime_type)
                    if file_prefix:
                        safe_prefix = "".join(c if c.isalnum() or c == "_" else "_" for c in file_prefix)
                        filename = f"{safe_prefix}_{actual_provider}_{timestamp}.{extension}"
                    else:
                        filename = f"img_{actual_provider}_{timestamp}.{extension}"

                    save_dir = Path(self.config.image_save_dir)
                    file_path = save_dir / filename
                    local_path: Optional[str] = None
                    save_error: Optional[str] = None

                    try:
                        save_dir.mkdir(parents=True, exist_ok=True)
                        with open(file_path, "wb") as f:
                            f.write(image_data_bytes)
                        local_path = str(file_path.resolve())
                        debug_print(f"Image successfully saved to {local_path}")
                    except Exception as e:
                        save_error = str(e)
                        debug_print(f"[ERROR] Failed to save image to disk: {save_error}")

                    image_info = {
                        "id": f"img_{actual_provider}_{timestamp}",
                        "provider": actual_provider,
                        "mime_type": image_mime_type,
                        "file_name": filename if local_path else None,
                        "local_path": local_path,
                        "url": None,
                        "size_bytes": len(image_data_bytes),
                        # Internal field used to build ImageContent, stripped from structured output.
                        "base64_data": image_data,
                        "revised_prompt": result[0].get("revised_prompt"),
                        "save_error": save_error
                    }
                    return self._build_tool_success_result(images=[image_info])
                else:
                    error_msg = "No image content in the generation result"
                    return self._build_tool_error_result(
                        code="missing_content",
                        message=error_msg,
                        details={"provider": actual_provider}
                    )
            finally:
                if not progress_task.done():
                    progress_task.cancel()

        except Exception as e:
            import traceback
            traceback.print_exc(file=sys.stderr)
            error_msg = f"Exception during image generation: {str(e)}"
            return self._build_tool_error_result(
                code="internal_error",
                message=error_msg
            )

    async def _list_resources(self) -> list[types.Resource]:
        """List available resources."""
        return [
            types.Resource(
                uri="providers://list",
                name="Available Providers",
                description="List of available image generation API providers",
                mimeType="application/json"
            ),
            types.Resource(
                uri="styles://list",
                name="All Styles",
                description="All available image styles from all providers",
                mimeType="application/json"
            ),
            types.Resource(
                uri="resolutions://list",
                name="All Resolutions",
                description="All available image resolutions from all providers",
                mimeType="application/json"
            )
        ]

    async def _read_resource(self, uri: str) -> str:
        """Read resource content by URI."""
        debug_print(f"Reading resource: {uri}")

        if uri == "providers://list":
            providers = self.provider_manager.get_available_providers()
            return json.dumps(providers, ensure_ascii=False, indent=2)

        elif uri == "styles://list":
            styles = self.provider_manager.get_all_styles()
            return json.dumps(styles, ensure_ascii=False, indent=2)

        elif uri == "resolutions://list":
            resolutions = self.provider_manager.get_all_resolutions()
            return json.dumps(resolutions, ensure_ascii=False, indent=2)

        elif uri.startswith("styles://provider/"):
            provider_name = uri.replace("styles://provider/", "")
            provider = self.provider_manager.get_provider(provider_name)
            if provider:
                styles = provider.get_available_styles()
                return json.dumps(styles, ensure_ascii=False, indent=2)
            else:
                raise ValueError(f"Provider '{provider_name}' not found")

        elif uri.startswith("resolutions://provider/"):
            provider_name = uri.replace("resolutions://provider/", "")
            provider = self.provider_manager.get_provider(provider_name)
            if provider:
                resolutions = provider.get_available_resolutions()
                return json.dumps(resolutions, ensure_ascii=False, indent=2)
            else:
                raise ValueError(f"Provider '{provider_name}' not found")

        else:
            raise ValueError(f"Unknown resource URI: {uri}")

    async def _list_prompts(self) -> list[types.Prompt]:
        """List available prompts."""
        return [
            types.Prompt(
                name="image_generation_prompt",
                description="Create image generation prompt template with provider and style information",
                arguments=[
                    types.PromptArgument(
                        name="description",
                        description="Image description",
                        required=True
                    ),
                    types.PromptArgument(
                        name="provider",
                        description="API provider to use",
                        required=False
                    ),
                    types.PromptArgument(
                        name="style",
                        description="Image style",
                        required=False
                    ),
                    types.PromptArgument(
                        name="resolution",
                        description="Image resolution",
                        required=False
                    ),
                    types.PromptArgument(
                        name="file_prefix",
                        description="Filename prefix",
                        required=False
                    )
                ]
            )
        ]

    async def _get_prompt(
        self,
        name: str,
        arguments: dict
    ) -> types.GetPromptResult:
        """Get prompt template by name."""
        if name == "image_generation_prompt":
            description = arguments.get("description", "")
            provider = arguments.get("provider", "")
            style = arguments.get("style", "")
            resolution = arguments.get("resolution", "")
            file_prefix = arguments.get("file_prefix", "")

            available_providers = self.provider_manager.get_available_providers()
            all_styles = self.provider_manager.get_all_styles()
            all_resolutions = self.provider_manager.get_all_resolutions()

            provider_text = f"Provider: {provider}" if provider else f"Provider: Auto-select from {available_providers}"
            style_text = f"Style: {style}" if style else "Style: Default for selected provider"
            resolution_text = f"Resolution: {resolution}" if resolution else "Resolution: Default for selected provider"
            prefix_text = f"Filename Prefix: {file_prefix}" if file_prefix else "Filename Prefix: [AI will generate if not provided]"

            prompt_text = f"""
Please use the following prompt to generate an image using multiple API providers:

Description: {description}
{provider_text}
{style_text}
{resolution_text}
Save Path: {self.config.image_save_dir}
{prefix_text}

Available Providers: {available_providers}

Available Styles by Provider:
{json.dumps(all_styles, ensure_ascii=False, indent=2)}

Available Resolutions by Provider:
{json.dumps(all_resolutions, ensure_ascii=False, indent=2)}

You can use the generate_image tool to generate this image and save it.
You can specify provider:style or provider:resolution format, or let the system auto-select.
"""

            return types.GetPromptResult(
                description=f"Image generation prompt for: {description}",
                messages=[
                    types.PromptMessage(
                        role="user",
                        content=types.TextContent(type="text", text=prompt_text)
                    )
                ]
            )
        else:
            raise ValueError(f"Unknown prompt: {name}")

    async def _handle_json_rpc(
        self,
        message: Dict[str, Any],
        session: Any
    ) -> Dict[str, Any]:
        """
        Handle JSON-RPC message from client.

        Args:
            message: JSON-RPC message
            session: Client session

        Returns:
            JSON-RPC response
        """
        method = message.get("method")
        params = message.get("params", {})
        request_id = message.get("id")

        debug_print(f"[JSON-RPC] Method: {method}, ID: {request_id}")

        try:
            # Route to appropriate handler
            if method == "initialize":
                result = await self._handle_initialize(params)
            elif method == "tools/list":
                tools = await self._list_tools()
                result = {"tools": [tool.model_dump(mode='json') for tool in tools]}
            elif method == "tools/call":
                tool_name = params.get("name")
                tool_arguments = params.get("arguments", {})
                structured_result = await self._call_tool_structured(tool_name, tool_arguments)
                safe_structured_result = self._strip_binary_fields(structured_result)
                content_result = self._tool_result_to_content(
                    structured_result,
                    text_payload=safe_structured_result
                )
                result = {
                    "content": [c.model_dump(mode="json") for c in content_result],
                    "structuredContent": safe_structured_result,
                    "isError": not safe_structured_result.get("ok", False)
                }
            elif method == "resources/list":
                resources = await self._list_resources()
                result = {"resources": [r.model_dump(mode='json') for r in resources]}
            elif method == "resources/read":
                uri = params.get("uri")
                content = await self._read_resource(uri)
                result = {
                    "contents": [{
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": content
                    }]
                }
            elif method == "prompts/list":
                prompts = await self._list_prompts()
                result = {"prompts": [p.model_dump(mode='json') for p in prompts]}
            elif method == "prompts/get":
                prompt_name = params.get("name")
                prompt_arguments = params.get("arguments", {})
                prompt_result = await self._get_prompt(prompt_name, prompt_arguments)
                result = prompt_result.model_dump(mode='json')
            else:
                raise ValueError(f"Unknown method: {method}")

            # Return success response
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }

        except Exception as e:
            debug_print(f"[JSON-RPC] Error: {e}")
            import traceback
            traceback.print_exc(file=sys.stderr)

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }

    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize handshake."""
        protocol_version = params.get("protocolVersion", "unknown")
        client_info = params.get("clientInfo", {})

        debug_print(f"[Initialize] Protocol: {protocol_version}, Client: {client_info}")

        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
                "resources": {},
                "prompts": {}
            },
            "serverInfo": {
                "name": "multi-api-image-mcp-http",
                "version": "0.2.0"
            }
        }

    def create_app(self) -> Starlette:
        """Create Starlette application with routes and middleware."""
        routes = [
            Route("/mcp/v1/messages", self.http_handler.handle_post, methods=["POST"]),
            Route("/mcp/v1/messages", self.http_handler.handle_get, methods=["GET"]),
            Route("/mcp/v1/messages", self.http_handler.handle_delete, methods=["DELETE"]),
            Route("/health", health_check, methods=["GET"]),
        ]

        middleware = []

        # Add origin validation middleware
        if self.config.allowed_origins:
            middleware.append(
                Middleware(
                    OriginValidationMiddleware,
                    allowed_origins=self.config.allowed_origins
                )
            )

        # Add authentication middleware
        if self.config.auth_enabled():
            middleware.append(create_auth_middleware(self.config.auth_token))
            middleware.append(Middleware(AuthRequiredMiddleware))

        return Starlette(routes=routes, middleware=middleware)

    async def start(self) -> None:
        """Start the HTTP server."""
        # Start session cleanup task
        await self.session_manager.start_cleanup_task()

        # Print startup info
        debug_print("=" * 50)
        debug_print("Multi-API Image Generation MCP HTTP Server Starting...")
        debug_print(f"Configuration: {self.config}")
        debug_print(f"Available providers: {self.provider_manager.get_available_providers()}")
        debug_print(f"Image save directory: {self.config.image_save_dir}")
        debug_print(f"HTTP server: {self.config.host}:{self.config.port}")
        debug_print(f"Authentication: {'Enabled' if self.config.auth_enabled() else 'Disabled'}")
        debug_print("=" * 50)

    async def stop(self) -> None:
        """Stop the HTTP server."""
        await self.session_manager.stop_cleanup_task()
        debug_print("Server stopped")


def run_http_server(config: ServerConfig) -> None:
    """
    Run MCP image generation server with HTTP transport.

    Args:
        config: Server configuration
    """
    # Create server instance
    server = MCPImageServerHTTP(config)

    # Create Starlette app
    app = server.create_app()

    # Add startup/shutdown handlers
    @app.on_event("startup")
    async def startup():
        await server.start()

    @app.on_event("shutdown")
    async def shutdown():
        await server.stop()

    # Run server
    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        log_level=config.log_level.lower()
    )


# Export for convenience
__all__ = ["MCPImageServerHTTP", "run_http_server"]
