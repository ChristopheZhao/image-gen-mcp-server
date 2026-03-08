"""
Lightweight stdio transport for MCP Image Generation Server.

This implementation handles line-delimited JSON-RPC directly so the server can
start quickly and remain compatible with local Codex stdio hosting.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from dotenv import load_dotenv

from ..config import ServerConfig


def debug_print(*args, **kwargs) -> None:
    """Print debug messages to stderr."""
    print(*args, file=sys.stderr, flush=True, **kwargs)


class MCPImageServerStdio:
    """MCP image generation server over raw stdio JSON-RPC."""

    TOOL_RESULT_VERSION = "1.0"
    RELOADABLE_CONFIG_FIELDS = frozenset(
        {
            "tencent_secret_id",
            "tencent_secret_key",
            "openai_api_key",
            "openai_base_url",
            "openai_model",
            "doubao_api_key",
            "doubao_endpoint",
            "doubao_model",
            "doubao_fallback_model",
            "default_provider",
            "public_base_url",
            "image_record_ttl",
            "get_image_data_max_bytes",
        }
    )

    def __init__(self, config: ServerConfig):
        self.config = config
        self.image_save_dir = Path(self.config.image_save_dir).resolve()
        self._image_records: Dict[str, Dict[str, Any]] = {}
        self._provider_manager = None

    @property
    def provider_manager(self):
        """Initialize provider manager lazily so stdio handshake stays fast."""
        if self._provider_manager is None:
            from ..providers.provider_manager import ProviderManager

            self._provider_manager = ProviderManager(config=self.config)
        return self._provider_manager

    def _build_generate_image_output_schema(self) -> Dict[str, Any]:
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
                            "save_error": {"type": ["string", "null"]},
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
                            "save_error",
                        ],
                    },
                },
                "error": {
                    "type": ["object", "null"],
                    "properties": {
                        "code": {"type": "string"},
                        "message": {"type": "string"},
                        "details": {"type": "object"},
                    },
                    "required": ["code", "message", "details"],
                },
            },
            "required": ["version", "ok", "images", "error"],
        }

    def _build_get_image_data_output_schema(self) -> Dict[str, Any]:
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
                            "file_name": {"type": "string"},
                            "local_path": {"type": "string"},
                            "url": {"type": ["string", "null"]},
                            "size_bytes": {"type": "integer"},
                            "base64_data": {"type": "string"},
                        },
                        "required": [
                            "id",
                            "provider",
                            "mime_type",
                            "file_name",
                            "local_path",
                            "url",
                            "size_bytes",
                            "base64_data",
                        ],
                    },
                },
                "error": {
                    "type": ["object", "null"],
                    "properties": {
                        "code": {"type": "string"},
                        "message": {"type": "string"},
                        "details": {"type": "object"},
                    },
                    "required": ["code", "message", "details"],
                },
            },
            "required": ["version", "ok", "images", "error"],
        }

    def _build_reload_config_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "version": {"type": "string"},
                "ok": {"type": "boolean"},
                "result": {
                    "type": ["object", "null"],
                    "properties": {
                        "changed_fields": {"type": "array", "items": {"type": "string"}},
                        "providers": {"type": "array", "items": {"type": "string"}},
                        "default_provider": {"type": ["string", "null"]},
                        "provider_models": {"type": "object"},
                        "restart_required_fields": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": [
                        "changed_fields",
                        "providers",
                        "default_provider",
                        "provider_models",
                        "restart_required_fields",
                    ],
                },
                "error": {
                    "type": ["object", "null"],
                    "properties": {
                        "code": {"type": "string"},
                        "message": {"type": "string"},
                        "details": {"type": "object"},
                    },
                    "required": ["code", "message", "details"],
                },
            },
            "required": ["version", "ok", "result", "error"],
        }

    def _list_tools_payload(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "generate_image",
                "description": (
                    "Generate image based on prompt using multiple API providers "
                    "(Hunyuan, OpenAI, Doubao)"
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "Image description text"},
                        "provider": {
                            "type": "string",
                            "description": (
                                "API provider to use. Available: hunyuan, openai, doubao. "
                                "Leave empty to use default provider"
                            ),
                            "default": "",
                        },
                        "style": {
                            "type": "string",
                            "description": (
                                "Provider style keyword (prompt-level style guidance). "
                                "Format: 'provider:style' or just 'style' for default provider"
                            ),
                            "default": "",
                        },
                        "resolution": {
                            "type": "string",
                            "description": (
                                "Image resolution. Format: 'provider:resolution' or just "
                                "'resolution' for default provider"
                            ),
                            "default": "",
                        },
                        "negative_prompt": {
                            "type": "string",
                            "description": "Negative prompt, describes content you don't want in the image",
                            "default": "",
                        },
                        "file_prefix": {
                            "type": "string",
                            "description": "Optional prefix for the output filename (English only)",
                            "default": "",
                        },
                        "background": {
                            "type": "string",
                            "description": "OpenAI-only: image background mode (`transparent`, `opaque`, `auto`)",
                            "default": "",
                        },
                        "output_format": {
                            "type": "string",
                            "description": "OpenAI-only: output image format (`png`, `jpeg`, `webp`)",
                            "default": "",
                        },
                        "output_compression": {
                            "type": ["integer", "null"],
                            "description": (
                                "OpenAI-only: compression level 0-100 "
                                "(requires `output_format` as `jpeg` or `webp`)"
                            ),
                            "minimum": 0,
                            "maximum": 100,
                        },
                        "moderation": {
                            "type": "string",
                            "description": "OpenAI-only: moderation level (`auto`, `low`)",
                            "default": "",
                        },
                    },
                    "required": ["prompt"],
                },
                "outputSchema": self._build_generate_image_output_schema(),
            },
            {
                "name": "get_image_data",
                "description": (
                    "Get base64 text data for a previously generated image by image_id "
                    "(for programmable artifact use)"
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "image_id": {
                            "type": "string",
                            "description": (
                                "Image id returned by generate_image, for example: "
                                "img_openai_1771140000"
                            ),
                        }
                    },
                    "required": ["image_id"],
                },
                "outputSchema": self._build_get_image_data_output_schema(),
            },
            {
                "name": "reload_config",
                "description": (
                    "Reload runtime configuration from environment/.env without restarting "
                    "the process. Only provider/model related settings and a small safe "
                    "subset are hot-reloadable."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "dotenv_override": {
                            "type": "boolean",
                            "description": (
                                "When true, force refresh environment variables from .env "
                                "before reloading config"
                            ),
                            "default": True,
                        }
                    },
                },
                "outputSchema": self._build_reload_config_output_schema(),
            },
        ]

    def _build_tool_success_result(self, images: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "version": self.TOOL_RESULT_VERSION,
            "ok": True,
            "images": images,
            "error": None,
        }

    def _build_tool_error_result(
        self,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {
            "version": self.TOOL_RESULT_VERSION,
            "ok": False,
            "images": [],
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            },
        }

    def _strip_binary_fields(
        self,
        result: Dict[str, Any],
        preserve_base64: bool = False,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "version": result.get("version"),
            "ok": result.get("ok"),
            "images": [],
            "error": result.get("error"),
        }

        images = result.get("images")
        if isinstance(images, list):
            for image in images:
                if isinstance(image, dict):
                    payload["images"].append(
                        {
                            key: value
                            for key, value in image.items()
                            if preserve_base64 or key != "base64_data"
                        }
                    )
                else:
                    payload["images"].append(image)

        return payload

    def _build_structured_payload_for_tool(
        self,
        tool_name: str,
        structured_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        if tool_name in {"generate_image", "get_image_data"}:
            preserve_base64 = tool_name == "get_image_data"
            return self._strip_binary_fields(structured_result, preserve_base64=preserve_base64)
        return structured_result

    def _tool_result_to_content(
        self,
        result: Dict[str, Any],
        text_payload: Optional[Dict[str, Any]] = None,
        include_image_blocks: bool = True,
    ) -> List[Dict[str, Any]]:
        content: List[Dict[str, Any]] = []

        if text_payload is None:
            text_payload = self._strip_binary_fields(result)
        content.append({"type": "text", "text": json.dumps(text_payload, ensure_ascii=False)})

        if not include_image_blocks:
            return content

        images = result.get("images", [])
        if isinstance(images, list):
            for image in images:
                if not isinstance(image, dict):
                    continue
                base64_data = image.get("base64_data")
                if not base64_data:
                    continue
                content.append(
                    {
                        "type": "image",
                        "data": base64_data,
                        "mimeType": image.get("mime_type", "image/jpeg"),
                    }
                )

        return content

    def _cleanup_expired_image_records(self) -> None:
        ttl_seconds = self.config.image_record_ttl
        if ttl_seconds <= 0:
            return

        now = time.time()
        expired_ids: List[str] = []
        for image_id, record in self._image_records.items():
            created_at = float(record.get("created_at", 0))
            if now - created_at > ttl_seconds:
                expired_ids.append(image_id)

        for image_id in expired_ids:
            self._image_records.pop(image_id, None)

    def _register_image_record(self, image: Dict[str, Any]) -> None:
        image_id = image.get("id")
        if not image_id:
            return

        self._cleanup_expired_image_records()
        self._image_records[image_id] = {
            "id": image.get("id"),
            "provider": image.get("provider"),
            "mime_type": image.get("mime_type"),
            "file_name": image.get("file_name"),
            "local_path": image.get("local_path"),
            "url": image.get("url"),
            "size_bytes": image.get("size_bytes"),
            "created_at": time.time(),
        }

    def _get_image_record(self, image_id: str) -> Optional[Dict[str, Any]]:
        self._cleanup_expired_image_records()
        return self._image_records.get(image_id)

    def _is_under_image_save_dir(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self.image_save_dir)
            return True
        except ValueError:
            return False

    def _image_extension_from_mime(self, mime_type: str) -> str:
        mime = (mime_type or "").lower()
        extension_map = {
            "image/jpeg": "jpg",
            "image/jpg": "jpg",
            "image/png": "png",
            "image/webp": "webp",
            "image/gif": "gif",
            "image/bmp": "bmp",
        }
        return extension_map.get(mime, "img")

    def _resolve_public_base_url(self) -> Optional[str]:
        configured = (self.config.public_base_url or "").strip()
        if configured:
            return configured.rstrip("/")

        host = (self.config.host or "").strip()
        if host in {"", "0.0.0.0", "::"}:
            return None

        host_part = host
        if ":" in host and not host.startswith("["):
            host_part = f"[{host}]"

        return f"http://{host_part}:{self.config.port}"

    def _build_public_image_url(self, file_name: str) -> Optional[str]:
        base_url = self._resolve_public_base_url()
        if not base_url:
            return None
        return f"{base_url}/images/{quote(file_name)}"

    def _mask_config_value(self, field_name: str, value: Any) -> Any:
        lowered = field_name.lower()
        if any(token in lowered for token in ("secret", "token", "key", "password")):
            if value is None:
                return None
            return "<set>" if str(value).strip() else "<empty>"
        return value

    def _collect_changed_config_fields(
        self,
        old_config: ServerConfig,
        new_config: ServerConfig,
    ) -> Dict[str, Dict[str, Any]]:
        changed: Dict[str, Dict[str, Any]] = {}
        for field_name in ServerConfig.model_fields.keys():
            old_value = getattr(old_config, field_name)
            new_value = getattr(new_config, field_name)
            if old_value != new_value:
                changed[field_name] = {
                    "before": self._mask_config_value(field_name, old_value),
                    "after": self._mask_config_value(field_name, new_value),
                }
        return changed

    def _build_reload_result(
        self,
        ok: bool,
        result: Optional[Dict[str, Any]] = None,
        code: Optional[str] = None,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        error_payload = None
        if not ok:
            error_payload = {
                "code": code or "reload_failed",
                "message": message or "Failed to reload configuration",
                "details": details or {},
            }
        return {
            "version": self.TOOL_RESULT_VERSION,
            "ok": ok,
            "result": result,
            "error": error_payload,
        }

    def _summarize_provider_models(self) -> Dict[str, Any]:
        summary: Dict[str, Any] = {}
        openai_provider = self.provider_manager.get_provider("openai")
        if openai_provider:
            summary["openai"] = {"model": getattr(openai_provider, "model", None)}
        doubao_provider = self.provider_manager.get_provider("doubao")
        if doubao_provider:
            summary["doubao"] = {
                "model": getattr(doubao_provider, "model", None),
                "fallback_model": getattr(doubao_provider, "fallback_model", None),
            }
        return summary

    async def _reload_config(self, dotenv_override: bool = True) -> Dict[str, Any]:
        if not isinstance(dotenv_override, bool):
            return self._build_reload_result(
                ok=False,
                code="invalid_arguments",
                message="dotenv_override must be a boolean",
                details={"dotenv_override": dotenv_override},
            )

        if dotenv_override:
            load_dotenv(override=True)

        try:
            new_config = ServerConfig()
            new_config.validate_transport_config()
        except Exception as e:
            return self._build_reload_result(
                ok=False,
                code="invalid_config",
                message=f"Failed to parse configuration: {e}",
            )

        changed_fields = self._collect_changed_config_fields(self.config, new_config)
        changed_names = sorted(changed_fields.keys())
        restart_required_fields = sorted(
            name for name in changed_names if name not in self.RELOADABLE_CONFIG_FIELDS
        )

        if restart_required_fields:
            return self._build_reload_result(
                ok=False,
                code="restart_required",
                message=(
                    "Configuration includes non hot-reloadable changes. "
                    "Please restart the MCP server."
                ),
                details={
                    "changed_fields": changed_names,
                    "restart_required_fields": restart_required_fields,
                    "field_diffs": changed_fields,
                },
            )

        try:
            from ..providers.provider_manager import ProviderManager

            new_provider_manager = ProviderManager(config=new_config)
        except Exception as e:
            return self._build_reload_result(
                ok=False,
                code="invalid_config",
                message=f"Failed to initialize providers from configuration: {e}",
            )

        self.config = new_config
        self.image_save_dir = Path(self.config.image_save_dir).resolve()
        self._provider_manager = new_provider_manager

        debug_print(
            "[INFO] Runtime config reloaded. "
            f"changed_fields={changed_names}, providers={self.provider_manager.get_available_providers()}"
        )

        return self._build_reload_result(
            ok=True,
            result={
                "changed_fields": changed_names,
                "providers": self.provider_manager.get_available_providers(),
                "default_provider": self.provider_manager.default_provider,
                "provider_models": self._summarize_provider_models(),
                "restart_required_fields": [],
            },
        )

    async def _call_tool_structured(self, name: str, arguments: dict) -> Dict[str, Any]:
        if name == "generate_image":
            return await self._generate_image(**arguments)
        if name == "get_image_data":
            return await self._get_image_data(**arguments)
        if name == "reload_config":
            return await self._reload_config(**arguments)
        return self._build_tool_error_result(
            code="unknown_tool",
            message=f"Unknown tool: {name}",
            details={"tool_name": name},
        )

    async def _get_image_data(self, image_id: str) -> Dict[str, Any]:
        if not image_id or not isinstance(image_id, str):
            return self._build_tool_error_result(
                code="invalid_arguments",
                message="image_id is required and must be a string",
            )

        record = self._get_image_record(image_id)
        if not record:
            return self._build_tool_error_result(
                code="image_not_found",
                message=f"Image id '{image_id}' not found or expired",
                details={"image_id": image_id},
            )

        local_path = record.get("local_path")
        if not local_path:
            return self._build_tool_error_result(
                code="missing_local_path",
                message=f"Image id '{image_id}' does not have a local file path",
                details={"image_id": image_id},
            )

        file_path = Path(local_path).resolve()
        if not self._is_under_image_save_dir(file_path):
            return self._build_tool_error_result(
                code="path_outside_save_dir",
                message="Resolved file path is outside MCP_IMAGE_SAVE_DIR",
                details={"image_id": image_id},
            )

        if not file_path.exists() or not file_path.is_file():
            return self._build_tool_error_result(
                code="file_not_found",
                message=f"Image file does not exist for id '{image_id}'",
                details={"image_id": image_id, "local_path": str(file_path)},
            )

        file_size = file_path.stat().st_size
        if file_size > self.config.get_image_data_max_bytes:
            return self._build_tool_error_result(
                code="payload_too_large",
                message=(
                    "Image is too large for get_image_data response. "
                    "Use images[].url to access the file directly."
                ),
                details={
                    "image_id": image_id,
                    "size_bytes": file_size,
                    "max_bytes": self.config.get_image_data_max_bytes,
                },
            )

        try:
            encoded = base64.b64encode(file_path.read_bytes()).decode("ascii")
        except Exception as e:
            return self._build_tool_error_result(
                code="read_failed",
                message=f"Failed to read image bytes: {e}",
                details={"image_id": image_id},
            )

        image_info = {
            "id": record.get("id"),
            "provider": record.get("provider"),
            "mime_type": record.get("mime_type") or "image/jpeg",
            "file_name": record.get("file_name"),
            "local_path": str(file_path),
            "url": record.get("url"),
            "size_bytes": file_size,
            "base64_data": encoded,
        }
        return self._build_tool_success_result(images=[image_info])

    async def _generate_image(
        self,
        prompt: str,
        provider: str = "",
        style: str = "",
        resolution: str = "",
        negative_prompt: str = "",
        file_prefix: str = "",
        background: str = "",
        output_format: str = "",
        output_compression: Optional[int] = None,
        moderation: str = "",
    ) -> Dict[str, Any]:
        debug_print(
            f"generate_image called: prompt={prompt}, provider={provider}, style={style}, "
            f"resolution={resolution}, background={background}, output_format={output_format}, "
            f"output_compression={output_compression}, moderation={moderation}"
        )

        actual_provider = provider
        actual_style = style
        actual_resolution = resolution

        if ":" in style and not actual_provider:
            provider_from_style, actual_style = style.split(":", 1)
            actual_provider = provider_from_style

        if ":" in resolution and not actual_provider:
            provider_from_res, actual_resolution = resolution.split(":", 1)
            if not actual_provider:
                actual_provider = provider_from_res

        if not actual_provider:
            actual_provider = self.provider_manager.default_provider
            if not actual_provider:
                available_providers = self.provider_manager.get_available_providers()
                error_text = (
                    "No provider specified and no default provider available. "
                    f"Available providers: {available_providers}"
                )
                debug_print(f"[ERROR] {error_text}")
                return self._build_tool_error_result(
                    code="provider_missing",
                    message=error_text,
                    details={"available_providers": available_providers},
                )

        provider_instance = self.provider_manager.get_provider(actual_provider)
        if not provider_instance:
            available_providers = self.provider_manager.get_available_providers()
            error_text = (
                f"Provider '{actual_provider}' not available. "
                f"Available providers: {available_providers}"
            )
            debug_print(f"[ERROR] {error_text}")
            return self._build_tool_error_result(
                code="provider_unavailable",
                message=error_text,
                details={
                    "provider": actual_provider,
                    "available_providers": available_providers,
                },
            )

        if actual_style and not provider_instance.validate_style(actual_style):
            available_styles = provider_instance.get_available_styles()
            error_text = (
                f"Invalid style '{actual_style}' for provider '{actual_provider}'. "
                f"Available styles: {list(available_styles.keys())}"
            )
            debug_print(f"[ERROR] {error_text}")
            return self._build_tool_error_result(
                code="invalid_style",
                message=error_text,
                details={
                    "provider": actual_provider,
                    "style": actual_style,
                    "available_styles": list(available_styles.keys()),
                },
            )

        if actual_resolution and not provider_instance.validate_resolution(actual_resolution):
            available_resolutions = provider_instance.get_available_resolutions()
            error_text = (
                f"Invalid resolution '{actual_resolution}' for provider '{actual_provider}'. "
                f"Available resolutions: {list(available_resolutions.keys())}"
            )
            debug_print(f"[ERROR] {error_text}")
            return self._build_tool_error_result(
                code="invalid_resolution",
                message=error_text,
                details={
                    "provider": actual_provider,
                    "resolution": actual_resolution,
                    "available_resolutions": list(available_resolutions.keys()),
                },
            )

        if not actual_style:
            default_styles = provider_instance.get_available_styles()
            actual_style = list(default_styles.keys())[0] if default_styles else "default"

        if not actual_resolution:
            default_resolutions = provider_instance.get_available_resolutions()
            actual_resolution = list(default_resolutions.keys())[0] if default_resolutions else "1024x1024"

        openai_options: Dict[str, Any] = {}
        if isinstance(background, str):
            background = background.strip()
        if isinstance(output_format, str):
            output_format = output_format.strip()
        if isinstance(moderation, str):
            moderation = moderation.strip()
        if background:
            openai_options["background"] = background
        if output_format:
            openai_options["output_format"] = output_format
        if output_compression is not None and output_compression != "":
            openai_options["output_compression"] = output_compression
        if moderation:
            openai_options["moderation"] = moderation

        if openai_options and actual_provider != "openai":
            return self._build_tool_error_result(
                code="invalid_parameters",
                message="OpenAI-specific parameters are only supported when provider=openai.",
                details={
                    "provider": actual_provider,
                    "openai_parameters": sorted(openai_options.keys()),
                },
            )

        debug_print(
            f"Using provider: {actual_provider}, style: {actual_style}, resolution: {actual_resolution}"
        )

        try:
            progress_task = None

            async def print_progress():
                count = 0
                while True:
                    count += 1
                    debug_print(
                        f"[Progress] Generating image with {actual_provider}... waited {count*5} seconds"
                    )
                    await asyncio.sleep(5)

            progress_task = asyncio.create_task(print_progress())

            try:
                debug_print(f"Calling {actual_provider} provider...")
                result = await self.provider_manager.generate_images(
                    query=prompt,
                    provider_name=actual_provider,
                    style=actual_style,
                    resolution=actual_resolution,
                    negative_prompt=negative_prompt,
                    **openai_options,
                )

                progress_task.cancel()
                try:
                    await progress_task
                except asyncio.CancelledError:
                    pass

                if not result or len(result) == 0:
                    return self._build_tool_error_result(
                        code="generation_failed",
                        message="Image generation failed: No result",
                    )

                if "error" in result[0]:
                    error_msg = result[0]["error"]
                    debug_print(f"[ERROR] {error_msg}")
                    return self._build_tool_error_result(
                        code="provider_error",
                        message=f"Image generation error: {error_msg}",
                        details={"provider": actual_provider},
                    )

                if "content" not in result[0]:
                    return self._build_tool_error_result(
                        code="missing_content",
                        message="No image content in the generation result",
                        details={"provider": actual_provider},
                    )

                image_data = result[0]["content"]
                image_mime_type = result[0].get("content_type", "image/jpeg")

                try:
                    image_data_bytes = base64.b64decode(image_data)
                except Exception as e:
                    error_msg = f"Failed to decode image content: {str(e)}"
                    debug_print(f"[ERROR] {error_msg}")
                    return self._build_tool_error_result(
                        code="decode_failed",
                        message=error_msg,
                        details={"provider": actual_provider},
                    )

                timestamp = int(time.time())
                extension = self._image_extension_from_mime(image_mime_type)
                if file_prefix:
                    safe_prefix = "".join(c if c.isalnum() or c == "_" else "_" for c in file_prefix)
                    filename = f"{safe_prefix}_{actual_provider}_{timestamp}.{extension}"
                else:
                    filename = f"img_{actual_provider}_{timestamp}.{extension}"

                save_dir = self.image_save_dir
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
                    "url": self._build_public_image_url(filename) if local_path else None,
                    "size_bytes": len(image_data_bytes),
                    "base64_data": image_data,
                    "revised_prompt": result[0].get("revised_prompt"),
                    "save_error": save_error,
                }
                if local_path:
                    self._register_image_record(image_info)
                return self._build_tool_success_result(images=[image_info])
            finally:
                if progress_task is not None and not progress_task.done():
                    progress_task.cancel()
        except Exception as e:
            import traceback

            traceback.print_exc(file=sys.stderr)
            return self._build_tool_error_result(
                code="internal_error",
                message=f"Exception during image generation: {str(e)}",
            )

    def _list_resources_payload(self) -> List[Dict[str, Any]]:
        return [
            {
                "uri": "providers://list",
                "name": "Available Providers",
                "description": "List of available image generation API providers",
                "mimeType": "application/json",
            },
            {
                "uri": "styles://list",
                "name": "All Styles",
                "description": "All available image styles from all providers",
                "mimeType": "application/json",
            },
            {
                "uri": "resolutions://list",
                "name": "All Resolutions",
                "description": "All available image resolutions from all providers",
                "mimeType": "application/json",
            },
        ]

    def _read_resource_content(self, uri: str) -> str:
        if uri == "providers://list":
            providers = self.provider_manager.get_available_providers()
            return json.dumps(providers, ensure_ascii=False, indent=2)
        if uri == "styles://list":
            styles = self.provider_manager.get_all_styles()
            return json.dumps(styles, ensure_ascii=False, indent=2)
        if uri == "resolutions://list":
            resolutions = self.provider_manager.get_all_resolutions()
            return json.dumps(resolutions, ensure_ascii=False, indent=2)
        if uri.startswith("styles://provider/"):
            provider_name = uri.replace("styles://provider/", "")
            provider = self.provider_manager.get_provider(provider_name)
            if provider:
                return json.dumps(provider.get_available_styles(), ensure_ascii=False, indent=2)
            raise ValueError(f"Provider '{provider_name}' not found")
        if uri.startswith("resolutions://provider/"):
            provider_name = uri.replace("resolutions://provider/", "")
            provider = self.provider_manager.get_provider(provider_name)
            if provider:
                return json.dumps(provider.get_available_resolutions(), ensure_ascii=False, indent=2)
            raise ValueError(f"Provider '{provider_name}' not found")
        raise ValueError(f"Unknown resource URI: {uri}")

    def _list_prompts_payload(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "image_generation_prompt",
                "description": "Create image generation prompt template with provider and style information",
                "arguments": [
                    {"name": "description", "description": "Image description", "required": True},
                    {"name": "provider", "description": "API provider to use", "required": False},
                    {"name": "style", "description": "Image style", "required": False},
                    {"name": "resolution", "description": "Image resolution", "required": False},
                    {"name": "file_prefix", "description": "Filename prefix", "required": False},
                ],
            }
        ]

    def _get_prompt_payload(self, name: str, arguments: dict) -> Dict[str, Any]:
        if name != "image_generation_prompt":
            raise ValueError(f"Unknown prompt: {name}")

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

        return {
            "description": f"Image generation prompt for: {description}",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": prompt_text,
                    },
                }
            ],
        }

    def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        protocol_version = params.get("protocolVersion", "unknown")
        client_info = params.get("clientInfo", {})
        debug_print(f"[Initialize] Protocol: {protocol_version}, Client: {client_info}")
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
                "resources": {},
                "prompts": {},
            },
            "serverInfo": {
                "name": "multi-api-image-mcp-stdio",
                "version": "0.2.0",
            },
        }

    def _is_notification(self, message: Dict[str, Any]) -> bool:
        """Check if a JSON-RPC message is a notification (no 'id' field)."""
        return "id" not in message

    async def _handle_json_rpc(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        method = message.get("method")
        params = message.get("params", {})
        request_id = message.get("id")

        # JSON-RPC notifications must not receive a response
        if self._is_notification(message):
            if method and method.startswith("notifications/"):
                debug_print(f"[JSON-RPC] Received notification: {method}")
            return None

        try:
            if method == "initialize":
                result = self._handle_initialize(params)
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": self._list_tools_payload()}
            elif method == "tools/call":
                tool_name = params.get("name")
                tool_arguments = params.get("arguments", {})
                structured_result = await self._call_tool_structured(tool_name, tool_arguments)
                safe_structured_result = self._build_structured_payload_for_tool(tool_name, structured_result)
                include_image_blocks = tool_name != "get_image_data"
                content_result = self._tool_result_to_content(
                    structured_result,
                    text_payload=safe_structured_result,
                    include_image_blocks=include_image_blocks,
                )
                result = {
                    "content": content_result,
                    "structuredContent": safe_structured_result,
                    "isError": not safe_structured_result.get("ok", False),
                }
            elif method == "resources/list":
                result = {"resources": self._list_resources_payload()}
            elif method == "resources/read":
                uri = params.get("uri")
                content = self._read_resource_content(uri)
                result = {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": content,
                        }
                    ]
                }
            elif method == "prompts/list":
                result = {"prompts": self._list_prompts_payload()}
            elif method == "prompts/get":
                prompt_name = params.get("name")
                prompt_arguments = params.get("arguments", {})
                result = self._get_prompt_payload(prompt_name, prompt_arguments)
            else:
                raise ValueError(f"Unknown method: {method}")

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result,
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
                    "message": str(e),
                },
            }

    def serve_forever(self) -> None:
        debug_print("=" * 50)
        debug_print("Multi-API Image Generation MCP Server Starting...")
        debug_print(f"Configuration: {self.config}")
        debug_print(f"Image save directory: {self.image_save_dir}")
        debug_print("Transport mode: stdio (native)")
        debug_print("Provider manager: lazy initialization")
        debug_print("=" * 50)

        # Use a single event loop for the server lifetime to allow async resource
        # reuse (e.g., HTTP connection pools in providers)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue

                try:
                    message = json.loads(line)
                except json.JSONDecodeError as exc:
                    debug_print(f"[STDIO] Invalid JSON-RPC line: {exc}")
                    continue

                response = loop.run_until_complete(self._handle_json_rpc(message))
                if response is None:
                    continue

                sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
                sys.stdout.flush()
        finally:
            loop.close()

        debug_print("Server stopped")


def run_stdio_server(config: ServerConfig) -> None:
    """Run MCP image generation server with native stdio transport."""
    server = MCPImageServerStdio(config)
    server.serve_forever()


__all__ = ["MCPImageServerStdio", "run_stdio_server"]
