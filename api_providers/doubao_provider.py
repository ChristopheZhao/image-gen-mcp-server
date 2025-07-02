import base64
import json
from typing import Dict, List, Optional
import asyncio
import aiohttp
import hashlib
import hmac
import time
import sys
from urllib.parse import urlencode
from .base import BaseImageProvider, debug_print

class DoubaoProvider(BaseImageProvider):
    """ByteDance Doubao (豆包) image generation provider"""
    
    def __init__(self, access_key: str, secret_key: str, endpoint: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.access_key = access_key
        self.secret_key = secret_key
        self.endpoint = endpoint or "https://visual.volcengineapi.com"
        
    def get_provider_name(self) -> str:
        return "doubao"
    
    def get_available_styles(self) -> Dict[str, str]:
        return {
            "general": "通用风格",
            "anime": "动漫风格",
            "realistic": "写实风格", 
            "oil_painting": "油画风格",
            "watercolor": "水彩风格",
            "sketch": "素描风格",
            "cartoon": "卡通风格",
            "chinese_painting": "国画风格",
            "pixel_art": "像素艺术",
            "cyberpunk": "赛博朋克",
            "fantasy": "奇幻风格",
            "sci_fi": "科幻风格"
        }
    
    def get_available_resolutions(self) -> Dict[str, str]:
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
    
    def _sign_request(self, method: str, uri: str, query: Dict, headers: Dict, body: str = "") -> str:
        """Generate signature for Volcengine API request"""
        # Create canonical request
        canonical_headers = ""
        signed_headers = ""
        
        # Sort headers
        sorted_headers = sorted(headers.items())
        for key, value in sorted_headers:
            canonical_headers += f"{key.lower()}:{value}\n"
            if signed_headers:
                signed_headers += ";"
            signed_headers += key.lower()
        
        # Create canonical query string
        canonical_query = ""
        if query:
            sorted_query = sorted(query.items())
            canonical_query = urlencode(sorted_query)
        
        # Create canonical request
        canonical_request = f"{method}\n{uri}\n{canonical_query}\n{canonical_headers}\n{signed_headers}\n{hashlib.sha256(body.encode()).hexdigest()}"
        
        # Create string to sign
        algorithm = "HMAC-SHA256"
        credential_scope = f"{time.strftime('%Y%m%d', time.gmtime())}/visual/request"
        string_to_sign = f"{algorithm}\n{headers['X-Date']}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode()).hexdigest()}"
        
        # Calculate signature
        kDate = hmac.new(f"volc{self.secret_key}".encode(), time.strftime('%Y%m%d', time.gmtime()).encode(), hashlib.sha256).digest()
        kService = hmac.new(kDate, "visual".encode(), hashlib.sha256).digest()
        kSigning = hmac.new(kService, "request".encode(), hashlib.sha256).digest()
        signature = hmac.new(kSigning, string_to_sign.encode(), hashlib.sha256).hexdigest()
        
        return signature
    
    async def generate_images(
        self, 
        query: str, 
        style: str = "general",
        resolution: str = "1024x1024",
        negative_prompt: str = "",
        **kwargs
    ) -> List[Dict]:
        """Generate images using Doubao API"""
        try:
            debug_print(f"[DEBUG] Doubao generate_images call started: query={query}, style={style}, resolution={resolution}")
            
            # Parse resolution
            width, height = map(int, resolution.split('x'))
            
            # Prepare request data
            request_data = {
                "req_key": f"doubao_img_{int(time.time())}",
                "prompt": query,
                "model_version": "general_v1.4",  # Use latest model
                "width": width,
                "height": height,
                "scale": 7.5,  # Guidance scale
                "ddim_steps": 25,  # Number of inference steps
                "seed": -1,  # Random seed
                "use_sr": True,  # Super resolution
                "logo_info": {
                    "add_logo": False,
                    "position": 0,
                    "language": 0,
                    "opacity": 0.3
                }
            }
            
            # Add style information to prompt if specified
            if style and style != "general":
                style_desc = self.get_available_styles().get(style, style)
                request_data["prompt"] = f"{query}, {style_desc}"
            
            # Add negative prompt if provided
            if negative_prompt:
                request_data["negative_prompt"] = negative_prompt
            
            # Prepare headers
            timestamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
            headers = {
                "Content-Type": "application/json",
                "X-Date": timestamp,
                "Host": "visual.volcengineapi.com"
            }
            
            # Convert data to JSON
            body = json.dumps(request_data)
            
            # Sign the request
            signature = self._sign_request("POST", "/", {}, headers, body)
            
            # Add authorization header
            headers["Authorization"] = f"HMAC-SHA256 Credential={self.access_key}/{time.strftime('%Y%m%d', time.gmtime())}/visual/request, SignedHeaders=content-type;host;x-date, Signature={signature}"
            
            debug_print(f"[DEBUG] Calling Doubao API with prompt: {request_data['prompt']}")
            
            # Make API request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.endpoint}/",
                    headers=headers,
                    data=body,
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
                    if "data" not in response_data or not response_data["data"]:
                        error_msg = response_data.get("message", "Unknown error from Doubao API")
                        debug_print(f"[ERROR] Doubao API error: {error_msg}")
                        return [{
                            "error": f"Doubao API error: {error_msg}",
                            "content_type": "text/plain"
                        }]
                    
                    # Extract image data
                    data = response_data["data"]
                    if "image_urls" not in data or not data["image_urls"]:
                        debug_print("[ERROR] No image URLs in Doubao response")
                        return [{
                            "error": "No image URLs returned from Doubao API",
                            "content_type": "text/plain"
                        }]
                    
                    # Download the first image
                    image_url = data["image_urls"][0]
                    debug_print(f"[DEBUG] Downloading image from Doubao: {image_url}")
                    
                    image_data = await self._download_image(image_url)
                    if not image_data:
                        return [{
                            "error": "Failed to download image from Doubao",
                            "content_type": "text/plain"
                        }]
                    
                    # Encode to base64
                    encoded_image = base64.b64encode(image_data).decode('utf-8')
                    debug_print(f"[DEBUG] Image successfully encoded to base64, length: {len(encoded_image)}")
                    
                    # Return result
                    result = [{
                        "content": encoded_image,
                        "content_type": "image/jpeg",
                        "description": query,
                        "style": style,
                        "provider": self.get_provider_name()
                    }]
                    
                    debug_print(f"[DEBUG] Returning Doubao result: {result[0].keys()}")
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