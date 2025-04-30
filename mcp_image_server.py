import os
import base64
from typing import Dict, Any, List, Optional
import asyncio
import json
import sys
import time
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent, ImageContent
from image_generation_tool import ImageGenerationTool

from dotenv import load_dotenv

load_dotenv()

# Function to print debug messages to stderr instead of stdout
def debug_print(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

# Initialize the MCP server
mcp = FastMCP("Image Generation MCP Service")

# Get configuration from MCP if available
try:
    # Try to get imageSaveDir from MCP config
    mcp_config = mcp.get_config()
    image_save_dir = mcp_config.get("imageSaveDir") if mcp_config else None
    debug_print(f"MCP config: {mcp_config}")
except Exception as e:
    debug_print(f"Error getting MCP config: {e}")
    image_save_dir = None

# Initialize image generation tool
secret_id = os.getenv("TENCENT_SECRET_ID")
secret_key = os.getenv("TENCENT_SECRET_KEY")

# Configure the default image save directory - priority: MCP config > env var > default
DEFAULT_SAVE_DIR = image_save_dir or os.getenv("MCP_IMAGE_SAVE_DIR", "./generated_images")
debug_print(f"Images will be saved to: {DEFAULT_SAVE_DIR}")

if not secret_id or not secret_key:
    raise ValueError("TENCENT_SECRET_ID and TENCENT_SECRET_KEY environment variables must be set")

image_tool = ImageGenerationTool(secret_id=secret_id, secret_key=secret_key)

# Define available styles for image generation
AVAILABLE_STYLES = {
    "riman": "日漫动画",
    "xieshi": "写实",
    "monai": "莫奈画风",
    "shuimo": "水墨画",
    "bianping": "扁平插画",
    "xiangsu": "像素插画",
    "ertonghuiben": "儿童绘本",
    "3dxuanran": "3D渲染",
    "manhua": "漫画",
    "heibaimanhua": "黑白漫画",
    "dongman": "动漫",
    "bijiasuo": "毕加索",
    "saibopengke": "赛博朋克",
    "youhua": "油画",
    "masaike": "马赛克",
    "qinghuaci": "青花瓷",
    "xinnianjianzhi": "新年剪纸画",
    "xinnianhuayi": "新年花艺"
}

# Define available resolutions
AVAILABLE_RESOLUTIONS = {
    "768:768": "768:768(1:1 正方形)",
    "768:1024": "768:1024(3:4 竖向)",
    "1024:768": "1024:768(4:3 横向)",
    "1024:1024": "1024:1024(1:1 正方形大图)",
    "720:1280": "720:1280(16:9 竖向)    ",
    "1280:720": "1280:720(9:16 横向)",
    "768:1280": "768:1280(3:5 竖向)",
    "1280:768": "1280:768(5:3 横向)"
}



# Register styles and resolutions as MCP resources
@mcp.resource("styles://list")
def get_available_styles() -> Dict[str, str]:
    """Get available image styles"""
    return AVAILABLE_STYLES

@mcp.resource("resolutions://list")
def get_available_resolutions() -> Dict[str, str]:
    """Get available image resolutions"""
    return AVAILABLE_RESOLUTIONS

def format_options(options_dict: Dict[str, str]) -> str:
    """
    Format dictionary of options into a string for parameter description.
    
    Args:
        options_dict: Dictionary of options where key is the option value and value is the description
        
    Returns:
        String in the format "key (description), key (description), ..."
    """
    return ', '.join(f'"{k}" ({v})' for k, v in options_dict.items())

available_styles_list = format_options(AVAILABLE_STYLES)
available_resolutions_list = format_options(AVAILABLE_RESOLUTIONS)  

@mcp.tool()
async def generate_image(
    prompt: str,
    style: str = "riman",
    resolution: str = "1024:1024",
    negative_prompt: str = "",
    file_prefix: str = ""
):
    f"""
    Generate image based on prompt

    Args:
        prompt: Image description text
        style: Image style. Must be one of: {available_styles_list}
        resolution: Image resolution. Must be one of: {available_resolutions_list}
        negative_prompt: Negative prompt, describes content you don't want in the image
        file_prefix: Optional prefix for the output filename (English only)
    """
    debug_print(f"generate_image called: prompt={prompt}, style={style}, resolution={resolution}, negative_prompt={negative_prompt}, file_prefix={file_prefix}")
    
    # Check if input parameters contain non-ASCII characters
    try:
        # Try to convert parameters to JSON to validate format
        params = {"prompt": prompt, "style": style, "resolution": resolution, "negative_prompt": negative_prompt, "file_prefix": file_prefix}
        json_str = json.dumps(params, ensure_ascii=False)
        debug_print(f"[DEBUG] Input parameters as JSON: {json_str}")
    except Exception as e:
        debug_print(f"[ERROR] Failed to convert input parameters to JSON: {e}")
    
    if style not in AVAILABLE_STYLES:
        debug_print(f"Error: Invalid style {style}")
        error_text = f"Error: Invalid style: {style}, please use styles://list to see available styles"
        return [TextContent(type="text", text=error_text)]
        
    if resolution not in AVAILABLE_RESOLUTIONS:
        debug_print(f"Error: Invalid resolution {resolution}")
        error_text = f"Error: Invalid resolution: {resolution}, please use resolutions://list to see available resolutions"
        return [TextContent(type="text", text=error_text)]
    
    debug_print("Starting image generation...")
    try:
        # Set a longer timeout
        debug_print("Initiating image generation, this may take some time...")
        
        # Add a timed print task, print progress reminder every 5 seconds
        async def print_progress():
            count = 0
            while True:
                count += 1
                debug_print(f"[Progress] Generating image... waited {count*5} seconds")
                await asyncio.sleep(5)
        
        # Start progress print task
        progress_task = asyncio.create_task(print_progress())
        
        try:
            # Call image generation tool
            debug_print("Calling image_tool.generate_images...")
            result = await image_tool.generate_images(
                query=prompt,
                style=style,
                resolution=resolution,
                negative_prompt=negative_prompt
            )
            
            # Cancel progress print task
            progress_task.cancel()
            try:
                await progress_task
            except asyncio.CancelledError:
                pass
            
            # Check if result can be serialized to JSON
            try:
                result_json = json.dumps(result, ensure_ascii=False)
                debug_print(f"[DEBUG] Generation result can be properly converted to JSON")
            except Exception as e:
                debug_print(f"[ERROR] Generation result cannot be converted to JSON: {e}")
                # Print detailed error information
                import traceback
                traceback.print_exc(file=sys.stderr)
                
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
                # Use the configured default save directory
                save_dir = Path(DEFAULT_SAVE_DIR)
                
                # Create the directory if it doesn't exist
                save_dir.mkdir(parents=True, exist_ok=True)
                
                # Create a safer and shorter filename
                # Option 1: Use fewer characters from the prompt
                safe_prompt = "".join(c if c.isalnum() else "_" for c in prompt[:10])
                timestamp = int(time.time())
                
                # Use custom name if provided, otherwise create one based on prompt
                if file_prefix:
                    safe_prefix = "".join(c if c.isalnum() or c == '_' else '_' for c in file_prefix)
                    filename = f"{safe_prefix}_{timestamp}.jpg"
                else:
                    filename = f"img_{timestamp}.jpg"
                
                # Full path to save the image
                file_path = save_dir / filename
                
                try:
                    # Decode base64 data and save to file
                    image_data_bytes = base64.b64decode(image_data)
                    with open(file_path, "wb") as f:
                        f.write(image_data_bytes)
                    
                    debug_print(f"[DEBUG] Image successfully saved to {file_path}")
                    
                    # Return the path to the saved image
                    return [TextContent(
                        type="text",
                        text=f"Image successfully generated and saved to: {file_path}"
                    )]
                except Exception as e:
                    debug_print(f"[ERROR] Error saving image: {e}")
                    import traceback
                    traceback.print_exc(file=sys.stderr)
                    
                    # Still return the image data if saving fails
                    response = [ImageContent(
                        type="image", 
                        mimeType="image/jpeg", 
                        data=image_data
                    )]
                    
                    response.append(TextContent(
                        type="text",
                        text=f"Warning: Failed to save image to disk. Error: {str(e)}"
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
def image_generation_prompt(description: str, style: str = "riman", resolution: str = "1024:1024", file_prefix: str = "") -> str:
    """
    Create image generation prompt template
    
    Args:
        description: Image description
        style: Image style
        resolution: Image resolution
        file_prefix: Optional prefix for the output filename
    """
    prefix_text = f"Filename Prefix: {file_prefix}" if file_prefix else "Filename Prefix: [AI will generate a suitable prefix if not provided]"
    
    return f"""
Please use the following prompt to generate an image:

Description: {description}
Style: {style}
Style可选值: {available_styles_list}
Resolution: {resolution}
Resolution可选值: {available_resolutions_list}
Save Path: {DEFAULT_SAVE_DIR} (configured on server)
{prefix_text}

You can use the generate_image tool to generate this image and save it.
If no filename prefix is provided, please create a short, descriptive English prefix based on the image description.
"""

def main():
    """Main function entry point, start MCP server"""
    # Print startup information and environment check
    debug_print("=" * 50)
    debug_print("MCP Image Generation Server Starting...")
    debug_print("Checking environment variables...")
    
    if not secret_id:
        debug_print("Error: TENCENT_SECRET_ID environment variable not set")
    else:
        debug_print(f"TENCENT_SECRET_ID environment variable set (length: {len(secret_id)})")
        
    if not secret_key:
        debug_print("Error: TENCENT_SECRET_KEY environment variable not set")
    else:
        debug_print(f"TENCENT_SECRET_KEY environment variable set (length: {len(secret_key)})")
    
    # Print available tools and resources
    debug_print("\nAvailable Tools:")
    try:
        # Get registered tools
        # Because list_tools() is an asynchronous method, we need a small helper function to get the tool list
        async def get_tools():
            tools = await mcp.list_tools()
            return tools
            
        # Run asynchronous function in synchronous environment
        tools = asyncio.run(get_tools())
        for tool in tools:
            debug_print(f" - {tool.name}")
    except Exception as e:
        debug_print(f"Error listing tools: {e}")
    
    # Load environment variables (if needed when running script directly)
    try:
        debug_print("Loading environment variables from .env file")
    except Exception as e:
        debug_print(f"Error loading environment variables: {e}")
        
    # Run MCP server
    debug_print("=" * 50)
    debug_print("Starting MCP Server...")
    mcp.run()

if __name__ == "__main__":
    # Run the MCP server
    main() 