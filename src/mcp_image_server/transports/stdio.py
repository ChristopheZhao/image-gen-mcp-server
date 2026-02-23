import os
import base64
from typing import Dict, Any, List, Optional, Annotated
import asyncio
import json
import sys
import time
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent, ImageContent
from ..providers import ProviderManager
from ..config import ServerConfig

from dotenv import load_dotenv
from pydantic import Field

load_dotenv()

# Function to print debug messages to stderr instead of stdout
def debug_print(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

# Initialize the MCP server
mcp = FastMCP("Multi-API Image Generation MCP Service")

# Get configuration from MCP if available
try:
    # Try to get imageSaveDir from MCP config
    mcp_config = mcp.get_config()
    image_save_dir = mcp_config.get("imageSaveDir") if mcp_config else None
    debug_print(f"MCP config: {mcp_config}")
except Exception as e:
    debug_print(f"Error getting MCP config: {e}")
    image_save_dir = None

# Configure the default image save directory - priority: MCP config > env var > default
DEFAULT_SAVE_DIR = image_save_dir or os.getenv("MCP_IMAGE_SAVE_DIR", "./generated_images")
debug_print(f"Images will be saved to: {DEFAULT_SAVE_DIR}")

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

# Initialize provider manager
runtime_config = ServerConfig()
provider_manager = ProviderManager(config=runtime_config)

# Register providers and their styles/resolutions as MCP resources
@mcp.resource("providers://list")
def get_available_providers() -> List[str]:
    """Get available image generation providers"""
    return provider_manager.get_available_providers()

@mcp.resource("styles://list")
def get_all_styles() -> Dict[str, Dict[str, str]]:
    """Get available image styles from all providers"""
    return provider_manager.get_all_styles()

@mcp.resource("resolutions://list")
def get_all_resolutions() -> Dict[str, Dict[str, str]]:
    """Get available image resolutions from all providers"""
    return provider_manager.get_all_resolutions()

@mcp.resource("styles://provider/{provider_name}")
def get_provider_styles(provider_name: str) -> Dict[str, str]:
    """Get available image styles for a specific provider"""
    provider = provider_manager.get_provider(provider_name)
    if provider:
        return provider.get_available_styles()
    return {}

@mcp.resource("resolutions://provider/{provider_name}")
def get_provider_resolutions(provider_name: str) -> Dict[str, str]:
    """Get available image resolutions for a specific provider"""
    provider = provider_manager.get_provider(provider_name)
    if provider:
        return provider.get_available_resolutions()
    return {}

def format_options(options_dict: Dict[str, str]) -> str:
    """
    Format dictionary of options into a string for parameter description.
    
    Args:
        options_dict: Dictionary of options where key is the option value and value is the description
        
    Returns:
        String in the format "key (description), key (description), ..."
    """
    return ', '.join(f'"{k}" ({v})' for k, v in options_dict.items())

def get_combined_styles() -> str:
    """Get combined styles from all providers for parameter description"""
    all_styles = provider_manager.get_all_styles()
    combined = {}
    for provider_name, styles in all_styles.items():
        for style_key, style_desc in styles.items():
            combined[f"{provider_name}:{style_key}"] = f"{provider_name} - {style_desc}"
    return format_options(combined)

def get_combined_resolutions() -> str:
    """Get combined resolutions from all providers for parameter description"""
    all_resolutions = provider_manager.get_all_resolutions()
    combined = {}
    for provider_name, resolutions in all_resolutions.items():
        for res_key, res_desc in resolutions.items():
            combined[f"{provider_name}:{res_key}"] = f"{provider_name} - {res_desc}"
    return format_options(combined)


TOOL_RESULT_VERSION = "1.0"


def build_reload_result(
    ok: bool,
    result: Optional[Dict[str, Any]] = None,
    code: Optional[str] = None,
    message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Build fixed-structure result for reload_config tool."""
    error_payload = None
    if not ok:
        error_payload = {
            "code": code or "reload_failed",
            "message": message or "Failed to reload configuration",
            "details": details or {},
        }
    return {
        "version": TOOL_RESULT_VERSION,
        "ok": ok,
        "result": result,
        "error": error_payload,
    }


def mask_config_value(field_name: str, value: Any) -> Any:
    """Mask sensitive values in diagnostics."""
    lowered = field_name.lower()
    if any(token in lowered for token in ("secret", "token", "key", "password")):
        if value is None:
            return None
        return "<set>" if str(value).strip() else "<empty>"
    return value


def collect_changed_config_fields(old_config: ServerConfig, new_config: ServerConfig) -> Dict[str, Dict[str, Any]]:
    """Collect changed field diffs with masked before/after values."""
    changed: Dict[str, Dict[str, Any]] = {}
    for field_name in ServerConfig.model_fields.keys():
        old_value = getattr(old_config, field_name)
        new_value = getattr(new_config, field_name)
        if old_value != new_value:
            changed[field_name] = {
                "before": mask_config_value(field_name, old_value),
                "after": mask_config_value(field_name, new_value),
            }
    return changed


def summarize_provider_models() -> Dict[str, Any]:
    """Return currently active provider model mapping."""
    summary: Dict[str, Any] = {}
    openai_provider = provider_manager.get_provider("openai")
    if openai_provider:
        summary["openai"] = {
            "model": getattr(openai_provider, "model", None)
        }
    doubao_provider = provider_manager.get_provider("doubao")
    if doubao_provider:
        summary["doubao"] = {
            "model": getattr(doubao_provider, "model", None),
            "fallback_model": getattr(doubao_provider, "fallback_model", None),
        }
    return summary


def reload_result_to_content(result: Dict[str, Any]) -> List[TextContent]:
    """Convert reload result to a text-only MCP content payload."""
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]


def build_tool_success_result(images: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build a successful fixed-structure tool result."""
    return {
        "version": TOOL_RESULT_VERSION,
        "ok": True,
        "images": images,
        "error": None
    }


def build_tool_error_result(
    code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Build a failed fixed-structure tool result."""
    return {
        "version": TOOL_RESULT_VERSION,
        "ok": False,
        "images": [],
        "error": {
            "code": code,
            "message": message,
            "details": details or {}
        }
    }


def strip_binary_fields(result: Dict[str, Any]) -> Dict[str, Any]:
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


def tool_result_to_content(result: Dict[str, Any]) -> List[TextContent | ImageContent]:
    """Convert fixed tool result to text + optional image content payload."""
    content: List[TextContent | ImageContent] = []

    text_payload = strip_binary_fields(result)
    content.append(TextContent(type="text", text=json.dumps(text_payload, ensure_ascii=False)))

    images = result.get("images", [])
    if isinstance(images, list):
        for image in images:
            if not isinstance(image, dict):
                continue
            base64_data = image.get("base64_data")
            if not base64_data:
                continue
            content.append(
                ImageContent(
                    type="image",
                    data=base64_data,
                    mimeType=image.get("mime_type", "image/jpeg")
                )
            )

    return content


def image_extension_from_mime(mime_type: str) -> str:
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

@mcp.tool()
async def generate_image(
    prompt: Annotated[str, Field(description="Image description text")],
    provider: Annotated[str, Field(description="API provider to use. Available: hunyuan, openai, doubao. Leave empty to use default provider")] = "",
    style: Annotated[str, Field(description="Image style. Format: 'provider:style' or just 'style' for default provider")] = "",
    resolution: Annotated[str, Field(description="Image resolution. Format: 'provider:resolution' or just 'resolution' for default provider")] = "",
    negative_prompt: Annotated[str, Field(description="Negative prompt, describes content you don't want in the image")] = "",
    file_prefix: Annotated[str, Field(description="Optional prefix for the output filename (English only)")] = ""
):
    """
    Generate image based on prompt using multiple API providers

    Args:
        prompt: Image description text
        provider: API provider to use (hunyuan, openai, doubao, or empty for default)
        style: Image style (can be provider:style format or just style for default provider)
        resolution: Image resolution (can be provider:resolution format or just resolution for default provider)
        negative_prompt: Negative prompt, describes content you don't want in the image
        file_prefix: Optional prefix for the output filename (English only)
    """
    debug_print(f"generate_image called: prompt={prompt}, provider={provider}, style={style}, resolution={resolution}, negative_prompt={negative_prompt}, file_prefix={file_prefix}")

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
        actual_provider = provider_manager.default_provider
        if not actual_provider:
            available_providers = provider_manager.get_available_providers()
            error_text = f"No provider specified and no default provider available. Available providers: {available_providers}"
            debug_print(f"[ERROR] {error_text}")
            return tool_result_to_content(
                build_tool_error_result(
                    code="provider_missing",
                    message=error_text,
                    details={"available_providers": available_providers}
                )
            )

    # Get the provider instance
    provider_instance = provider_manager.get_provider(actual_provider)
    if not provider_instance:
        available_providers = provider_manager.get_available_providers()
        error_text = f"Provider '{actual_provider}' not available. Available providers: {available_providers}"
        debug_print(f"[ERROR] {error_text}")
        return tool_result_to_content(
            build_tool_error_result(
                code="provider_unavailable",
                message=error_text,
                details={
                    "provider": actual_provider,
                    "available_providers": available_providers
                }
            )
        )

    # Validate style
    if actual_style and not provider_instance.validate_style(actual_style):
        available_styles = provider_instance.get_available_styles()
        error_text = f"Invalid style '{actual_style}' for provider '{actual_provider}'. Available styles: {list(available_styles.keys())}"
        debug_print(f"[ERROR] {error_text}")
        return tool_result_to_content(
            build_tool_error_result(
                code="invalid_style",
                message=error_text,
                details={
                    "provider": actual_provider,
                    "style": actual_style,
                    "available_styles": list(available_styles.keys())
                }
            )
        )

    # Validate resolution
    if actual_resolution and not provider_instance.validate_resolution(actual_resolution):
        available_resolutions = provider_instance.get_available_resolutions()
        error_text = f"Invalid resolution '{actual_resolution}' for provider '{actual_provider}'. Available resolutions: {list(available_resolutions.keys())}"
        debug_print(f"[ERROR] {error_text}")
        return tool_result_to_content(
            build_tool_error_result(
                code="invalid_resolution",
                message=error_text,
                details={
                    "provider": actual_provider,
                    "resolution": actual_resolution,
                    "available_resolutions": list(available_resolutions.keys())
                }
            )
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
        async def print_progress():
            count = 0
            while True:
                count += 1
                debug_print(f"[Progress] Generating image with {actual_provider}... waited {count*5} seconds")
                await asyncio.sleep(5)

        progress_task = asyncio.create_task(print_progress())

        try:
            debug_print(f"Calling {actual_provider} provider...")
            result = await provider_manager.generate_images(
                query=prompt,
                provider_name=actual_provider,
                style=actual_style,
                resolution=actual_resolution,
                negative_prompt=negative_prompt
            )

            progress_task.cancel()
            try:
                await progress_task
            except asyncio.CancelledError:
                pass

            debug_print(f"Image generation completed, result type: {type(result)}")

            if not result or len(result) == 0:
                return tool_result_to_content(
                    build_tool_error_result(
                        code="generation_failed",
                        message="Image generation failed: No result"
                    )
                )

            if "error" in result[0]:
                error_msg = result[0]["error"]
                debug_print(f"[ERROR] {error_msg}")
                return tool_result_to_content(
                    build_tool_error_result(
                        code="provider_error",
                        message=f"Image generation error: {error_msg}",
                        details={"provider": actual_provider}
                    )
                )

            if "content" not in result[0]:
                return tool_result_to_content(
                    build_tool_error_result(
                        code="missing_content",
                        message="No image content in the generation result",
                        details={"provider": actual_provider}
                    )
                )

            image_data = result[0]["content"]
            image_mime_type = result[0].get("content_type", "image/jpeg")

            try:
                image_data_bytes = base64.b64decode(image_data)
            except Exception as e:
                error_msg = f"Failed to decode image content: {str(e)}"
                debug_print(f"[ERROR] {error_msg}")
                return tool_result_to_content(
                    build_tool_error_result(
                        code="decode_failed",
                        message=error_msg,
                        details={"provider": actual_provider}
                    )
                )

            timestamp = int(time.time())
            extension = image_extension_from_mime(image_mime_type)
            if file_prefix:
                safe_prefix = "".join(c if c.isalnum() or c == "_" else "_" for c in file_prefix)
                filename = f"{safe_prefix}_{actual_provider}_{timestamp}.{extension}"
            else:
                filename = f"img_{actual_provider}_{timestamp}.{extension}"

            save_dir = Path(DEFAULT_SAVE_DIR)
            file_path = save_dir / filename
            local_path: Optional[str] = None
            save_error: Optional[str] = None

            try:
                save_dir.mkdir(parents=True, exist_ok=True)
                with open(file_path, "wb") as f:
                    f.write(image_data_bytes)
                local_path = str(file_path.resolve())
                debug_print(f"[DEBUG] Image successfully saved to {local_path}")
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
                # Internal field used to build ImageContent, stripped from text payload.
                "base64_data": image_data,
                "revised_prompt": result[0].get("revised_prompt"),
                "save_error": save_error
            }

            return tool_result_to_content(
                build_tool_success_result(images=[image_info])
            )
        finally:
            if not progress_task.done():
                progress_task.cancel()

    except Exception as e:
        import traceback
        traceback.print_exc(file=sys.stderr)
        error_msg = f"Exception occurred during image generation: {str(e)}"
        return tool_result_to_content(
            build_tool_error_result(
                code="internal_error",
                message=error_msg
            )
        )

@mcp.tool()
async def reload_config(
    dotenv_override: Annotated[bool, Field(description="Whether to force-refresh environment values from .env before reload")] = True
):
    """
    Reload runtime configuration without process restart.

    Only a safe subset of fields is hot-reloadable (mainly provider credentials/models).
    """
    global runtime_config, provider_manager

    if not isinstance(dotenv_override, bool):
        return reload_result_to_content(
            build_reload_result(
                ok=False,
                code="invalid_arguments",
                message="dotenv_override must be a boolean",
                details={"dotenv_override": dotenv_override}
            )
        )

    if dotenv_override:
        load_dotenv(override=True)

    try:
        new_config = ServerConfig()
        new_config.validate_transport_config()
    except Exception as e:
        return reload_result_to_content(
            build_reload_result(
                ok=False,
                code="invalid_config",
                message=f"Failed to parse configuration: {e}",
            )
        )

    changed_fields = collect_changed_config_fields(runtime_config, new_config)
    changed_names = sorted(changed_fields.keys())
    restart_required_fields = sorted(
        name for name in changed_names if name not in RELOADABLE_CONFIG_FIELDS
    )
    if restart_required_fields:
        return reload_result_to_content(
            build_reload_result(
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
                }
            )
        )

    try:
        new_provider_manager = ProviderManager(config=new_config)
    except Exception as e:
        return reload_result_to_content(
            build_reload_result(
                ok=False,
                code="invalid_config",
                message=f"Failed to initialize providers from configuration: {e}",
            )
        )

    runtime_config = new_config
    provider_manager = new_provider_manager
    debug_print(
        "[INFO] Runtime config reloaded. "
        f"changed_fields={changed_names}, providers={provider_manager.get_available_providers()}"
    )
    return reload_result_to_content(
        build_reload_result(
            ok=True,
            result={
                "changed_fields": changed_names,
                "providers": provider_manager.get_available_providers(),
                "default_provider": provider_manager.default_provider,
                "provider_models": summarize_provider_models(),
                "restart_required_fields": [],
            }
        )
    )

@mcp.prompt()
def image_generation_prompt(
    description: str, 
    provider: str = "",
    style: str = "", 
    resolution: str = "", 
    file_prefix: str = ""
) -> str:
    """
    Create image generation prompt template
    
    Args:
        description: Image description
        provider: API provider to use
        style: Image style
        resolution: Image resolution
        file_prefix: Optional prefix for the output filename
    """
    available_providers = provider_manager.get_available_providers()
    all_styles = provider_manager.get_all_styles()
    all_resolutions = provider_manager.get_all_resolutions()
    
    provider_text = f"Provider: {provider}" if provider else f"Provider: Auto-select from {available_providers}"
    style_text = f"Style: {style}" if style else "Style: Default for selected provider"
    resolution_text = f"Resolution: {resolution}" if resolution else "Resolution: Default for selected provider"
    prefix_text = f"Filename Prefix: {file_prefix}" if file_prefix else "Filename Prefix: [AI will generate a suitable prefix if not provided]"
    
    return f"""
Please use the following prompt to generate an image using multiple API providers:

Description: {description}
{provider_text}
{style_text}
{resolution_text}
Save Path: {DEFAULT_SAVE_DIR} (configured on server)
{prefix_text}

Available Providers: {available_providers}

Available Styles by Provider:
{json.dumps(all_styles, ensure_ascii=False, indent=2)}

Available Resolutions by Provider:
{json.dumps(all_resolutions, ensure_ascii=False, indent=2)}

You can use the generate_image tool to generate this image and save it.
You can specify provider:style or provider:resolution format, or let the system auto-select.
"""

def main():
    """Main function entry point, start MCP server"""
    # Print startup information and environment check
    debug_print("=" * 50)
    debug_print("Multi-API Image Generation MCP Server Starting...")
    debug_print("Checking available providers...")
    
    available_providers = provider_manager.get_available_providers()
    if available_providers:
        debug_print(f"Available providers: {available_providers}")
        debug_print(f"Default provider: {provider_manager.default_provider}")
    else:
        debug_print("[WARNING] No providers available! Please check your environment variables.")
        debug_print("Expected environment variables:")
        debug_print("- TENCENT_SECRET_ID and TENCENT_SECRET_KEY for Hunyuan")
        debug_print("- OPENAI_API_KEY (and optionally OPENAI_BASE_URL) for OpenAI")
        debug_print("- DOUBAO_API_KEY (and optionally DOUBAO_ENDPOINT) for Doubao (using Ark API)")
    
    # Print available tools and resources
    debug_print("\nAvailable Tools:")
    try:
        async def get_tools():
            tools = await mcp.list_tools()
            return tools
            
        tools = asyncio.run(get_tools())
        for tool in tools:
            debug_print(f" - {tool.name}")
    except Exception as e:
        debug_print(f"Error listing tools: {e}")
        
    debug_print("=" * 50)
    debug_print("Starting Multi-API MCP Server...")
    mcp.run()

if __name__ == "__main__":
    main()
