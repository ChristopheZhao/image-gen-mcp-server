import base64
import json
from typing import Dict, List, Optional
import asyncio
import aiohttp
import sys
from .base import BaseImageProvider, debug_print

class DoubaoProvider(BaseImageProvider):
    """ByteDance Doubao (豆包) image generation provider using Ark API"""

    def __init__(self, api_key: str, endpoint: Optional[str] = None, model: str = "doubao-seedream-4.0", **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key
        self.endpoint = endpoint or "https://ark.cn-beijing.volces.com"
        self.model = model  # doubao-seedream-4.0, doubao-seedream-4.5, etc.

    def get_provider_name(self) -> str:
        return "doubao"

    def get_available_styles(self) -> Dict[str, str]:
        """
        Doubao Seedream models use prompt engineering for styles.
        These style keywords will be appended to the prompt.
        """
        return {
            "general": "通用风格",
            "anime": "动漫风格 anime style",
            "realistic": "写实风格 realistic photographic",
            "oil_painting": "油画风格 oil painting",
            "watercolor": "水彩风格 watercolor painting",
            "sketch": "素描风格 pencil sketch",
            "cartoon": "卡通风格 cartoon illustration",
            "chinese_painting": "国画风格 traditional Chinese painting",
            "pixel_art": "像素艺术 pixel art",
            "cyberpunk": "赛博朋克 cyberpunk style",
            "fantasy": "奇幻风格 fantasy art",
            "sci_fi": "科幻风格 sci-fi concept art"
        }

    def get_available_resolutions(self) -> Dict[str, str]:
        """
        Doubao Seedream 4.0/4.5 supported resolutions.
        Format: WIDTHxHEIGHT
        """
        return {
            "512x512": "512x512 (1:1 小正方形)",
            "768x768": "768x768 (1:1 正方形)",
            "1024x1024": "1024x1024 (1:1 大正方形)",
            "512x768": "512x768 (2:3 竖向)",
            "768x512": "768x512 (3:2 横向)",
            "576x1024": "576x1024 (9:16 竖向)",
            "1024x576": "1024x576 (16:9 横向)",
            "768x1024": "768x1024 (3:4 竖向)",
            "1024x768": "1024x768 (4:3 横向)"
        }

    async def generate_images(
        self,
        query: str,
        style: str = "general",
        resolution: str = "1024x1024",
        negative_prompt: str = "",
        **kwargs
    ) -> List[Dict]:
        """Generate images using Doubao Ark API"""
        try:
            debug_print(f"[DEBUG] Doubao generate_images call started: query={query}, style={style}, resolution={resolution}, model={self.model}")

            # Parse resolution
            width, height = map(int, resolution.split('x'))

            # Build prompt with style
            full_prompt = query
            if style and style != "general":
                style_desc = self.get_available_styles().get(style, "")
                if style_desc:
                    # Extract English style description
                    english_part = style_desc.split()[-1] if " " in style_desc else style_desc
                    full_prompt = f"{query}, {english_part}"

            # Prepare request data (Ark API format, similar to OpenAI)
            request_data = {
                "model": self.model,
                "prompt": full_prompt,
                "n": 1,  # Number of images to generate
                "size": f"{width}x{height}",
                "response_format": "b64_json"  # Return base64 encoded image
            }

            # Add negative prompt if provided
            if negative_prompt:
                request_data["negative_prompt"] = negative_prompt

            # Prepare headers
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            debug_print(f"[DEBUG] Calling Doubao Ark API with prompt: {full_prompt}")

            # Make API request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.endpoint}/api/v3/images/generations",
                    headers=headers,
                    json=request_data,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:

                    if response.status != 200:
                        error_text = await response.text()
                        debug_print(f"[ERROR] Doubao API request failed with status {response.status}: {error_text}")
                        return [{
                            "error": f"Doubao API request failed: HTTP {response.status}",
                            "content_type": "text/plain"
                        }]

                    response_data = await response.json()
                    debug_print(f"[DEBUG] Doubao API response received")

                    # Check for API errors
                    if "error" in response_data:
                        error_msg = response_data["error"].get("message", "Unknown error from Doubao API")
                        debug_print(f"[ERROR] Doubao API error: {error_msg}")
                        return [{
                            "error": f"Doubao API error: {error_msg}",
                            "content_type": "text/plain"
                        }]

                    # Extract image data (Ark API returns OpenAI-compatible format)
                    if "data" not in response_data or not response_data["data"]:
                        debug_print("[ERROR] No data in Doubao response")
                        return [{
                            "error": "No image data returned from Doubao API",
                            "content_type": "text/plain"
                        }]

                    # Get first image (we requested n=1)
                    image_item = response_data["data"][0]

                    # Handle response format
                    if "b64_json" in image_item:
                        # Base64 encoded image
                        encoded_image = image_item["b64_json"]
                        debug_print(f"[DEBUG] Received base64 image, length: {len(encoded_image)}")
                    elif "url" in image_item:
                        # Image URL - need to download
                        image_url = image_item["url"]
                        debug_print(f"[DEBUG] Downloading image from URL: {image_url}")
                        image_data = await self._download_image(image_url)
                        if not image_data:
                            return [{
                                "error": "Failed to download image from Doubao",
                                "content_type": "text/plain"
                            }]
                        encoded_image = base64.b64encode(image_data).decode('utf-8')
                    else:
                        debug_print("[ERROR] No image data or URL in response")
                        return [{
                            "error": "Invalid response format from Doubao API",
                            "content_type": "text/plain"
                        }]

                    # Return result
                    result = [{
                        "content": encoded_image,
                        "content_type": "image/png",  # Ark API typically returns PNG
                        "description": query,
                        "style": style,
                        "provider": self.get_provider_name()
                    }]

                    debug_print(f"[DEBUG] Returning Doubao result successfully")
                    return result

        except asyncio.TimeoutError:
            error_msg = "Doubao API request timeout"
            debug_print(f"[ERROR] {error_msg}")
            return [{
                "error": error_msg,
                "content_type": "text/plain"
            }]
        except Exception as e:
            error_msg = str(e)
            debug_print(f"[ERROR] Unexpected error in Doubao provider: {error_msg}")
            import traceback
            traceback.print_exc(file=sys.stderr)
            return [{
                "error": f"Error occurred during Doubao image generation: {error_msg}",
                "content_type": "text/plain"
            }]

    async def _download_image(self, url: str) -> Optional[bytes]:
        """Download image from URL"""
        debug_print(f"[DEBUG] Downloading image from URL: {url}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        debug_print(f"[DEBUG] Image downloaded successfully, size: {len(image_data)} bytes")
                        return image_data
                    else:
                        debug_print(f"[ERROR] Failed to download image, status code: {response.status}")
                        return None
        except Exception as e:
            error_msg = str(e)
            debug_print(f"[ERROR] Error downloading image: {error_msg}")
            import traceback
            traceback.print_exc(file=sys.stderr)
            return None
