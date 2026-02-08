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
from api_providers import ProviderManager

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

# Initialize provider manager
provider_manager = ProviderManager()

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
            return [TextContent(type="text", text=error_text)]
    
    # Get the provider instance
    provider_instance = provider_manager.get_provider(actual_provider)
    if not provider_instance:
        available_providers = provider_manager.get_available_providers()
        error_text = f"Provider '{actual_provider}' not available. Available providers: {available_providers}"
        debug_print(f"[ERROR] {error_text}")
        return [TextContent(type="text", text=error_text)]
    
    # Validate style
    if actual_style and not provider_instance.validate_style(actual_style):
        available_styles = provider_instance.get_available_styles()
        error_text = f"Invalid style '{actual_style}' for provider '{actual_provider}'. Available styles: {list(available_styles.keys())}"
        debug_print(f"[ERROR] {error_text}")
        return [TextContent(type="text", text=error_text)]
    
    # Validate resolution
    if actual_resolution and not provider_instance.validate_resolution(actual_resolution):
        available_resolutions = provider_instance.get_available_resolutions()
        error_text = f"Invalid resolution '{actual_resolution}' for provider '{actual_provider}'. Available resolutions: {list(available_resolutions.keys())}"
        debug_print(f"[ERROR] {error_text}")
        return [TextContent(type="text", text=error_text)]
    
    # Set defaults if not provided
    if not actual_style:
        default_styles = provider_instance.get_available_styles()
        actual_style = list(default_styles.keys())[0] if default_styles else "default"
    
    if not actual_resolution:
        default_resolutions = provider_instance.get_available_resolutions()
        actual_resolution = list(default_resolutions.keys())[0] if default_resolutions else "1024x1024"
    
    debug_print(f"Using provider: {actual_provider}, style: {actual_style}, resolution: {actual_resolution}")
    
    try:
        # Add a timed print task, print progress reminder every 5 seconds
        async def print_progress():
            count = 0
            while True:
                count += 1
                debug_print(f"[Progress] Generating image with {actual_provider}... waited {count*5} seconds")
                await asyncio.sleep(5)
        
        # Start progress print task
        progress_task = asyncio.create_task(print_progress())
        
        try:
            # Call image generation through provider manager
            debug_print(f"Calling {actual_provider} provider...")
            result = await provider_manager.generate_images(
                query=prompt,
                provider_name=actual_provider,
                style=actual_style,
                resolution=actual_resolution,
                negative_prompt=negative_prompt
            )
            
            # Cancel progress print task
            progress_task.cancel()
            try:
                await progress_task
            except asyncio.CancelledError:
                pass
            
            debug_print(f"Image generation completed, result type: {type(result)}")
            
            # Check result
            if not result or len(result) == 0:
                error_msg = "Image generation failed: No result"
                return [TextContent(type="text", text=error_msg)]
                
            # Check for errors
            if "error" in result[0]:
                error_msg = result[0]["error"]
                debug_print(f"[DEBUG] Processed error message: {error_msg}")
                return [TextContent(type="text", text=f"Image generation error: {error_msg}")]
                
            # Check image content
            if "content" in result[0]:
                # This is Base64 encoded image
                image_data = result[0]["content"]
                
                # Save the image
                save_dir = Path(DEFAULT_SAVE_DIR)
                save_dir.mkdir(parents=True, exist_ok=True)
                
                # Create filename
                timestamp = int(time.time())
                if file_prefix:
                    safe_prefix = "".join(c if c.isalnum() or c == '_' else '_' for c in file_prefix)
                    filename = f"{safe_prefix}_{actual_provider}_{timestamp}.jpg"
                else:
                    filename = f"img_{actual_provider}_{timestamp}.jpg"
                
                file_path = save_dir / filename
                
                try:
                    # Decode base64 data and save to file
                    image_data_bytes = base64.b64decode(image_data)
                    with open(file_path, "wb") as f:
                        f.write(image_data_bytes)
                    
                    debug_print(f"[DEBUG] Image successfully saved to {file_path}")
                    
                    # Return the path to the saved image
                    provider_info = f" (Provider: {actual_provider})"
                    return [TextContent(
                        type="text",
                        text=f"Image successfully generated and saved to: {file_path}{provider_info}"
                    )]
                except Exception as e:
                    debug_print(f"[ERROR] Error saving image: {e}")
                    import traceback
                    traceback.print_exc(file=sys.stderr)
                    
                    # Still return the image data if saving fails
                    response = [ImageContent(
                        type="image", 
                        mimeType=result[0].get("content_type", "image/jpeg"), 
                        data=image_data
                    )]
                    
                    response.append(TextContent(
                        type="text",
                        text=f"Warning: Failed to save image to disk. Error: {str(e)} (Provider: {actual_provider})"
                    ))
                    
                    return response
            else:
                error_msg = "No image content in the image generation result"
                return [TextContent(type="text", text=error_msg)]
        finally:
            # Ensure progress task is cancelled
            if not progress_task.done():
                progress_task.cancel()
                
    except Exception as e:
        import traceback
        traceback.print_exc(file=sys.stderr)
        error_msg = f"Exception occurred during image generation: {str(e)}"
        return [TextContent(type="text", text=error_msg)]

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