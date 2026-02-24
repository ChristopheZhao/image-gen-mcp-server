import base64
import json
from typing import Dict, List, Optional
import asyncio
import aiohttp
import sys
from .base import BaseImageProvider, debug_print

class DoubaoProvider(BaseImageProvider):
    """ByteDance Doubao (豆包) image generation provider using Ark API"""

    _BASE_RESOLUTIONS: Dict[str, str] = {
        # High-res options first so default routing does not fall back to legacy low resolutions.
        "2048x2048": "2048x2048 (2K 正方形，推荐)",
        "2560x1440": "2560x1440 (2K 16:9 横向)",
        "1440x2560": "1440x2560 (2K 9:16 竖向)",
        "2304x1728": "2304x1728 (2K 4:3 横向)",
        "1728x2304": "1728x2304 (2K 3:4 竖向)",
        "2496x1664": "2496x1664 (2K 3:2 横向)",
        "1664x2496": "1664x2496 (2K 2:3 竖向)",
        "3024x1296": "3024x1296 (2K 21:9 横向)",
        "1296x3024": "1296x3024 (2K 9:21 竖向)",
        # Legacy lower-res options (kept for older models, filtered for 4.x as needed).
        "1024x1024": "1024x1024 (1:1 大正方形)",
        "768x1024": "768x1024 (3:4 竖向)",
        "1024x768": "1024x768 (4:3 横向)",
        "576x1024": "576x1024 (9:16 竖向)",
        "1024x576": "1024x576 (16:9 横向)",
        "768x768": "768x768 (1:1 正方形)",
        "512x768": "512x768 (2:3 竖向)",
        "768x512": "768x512 (3:2 横向)",
        "512x512": "512x512 (1:1 小正方形)",
    }

    def __init__(
        self,
        api_key: str,
        model: str,
        endpoint: Optional[str] = None,
        fallback_model: Optional[str] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.api_key = api_key
        self.endpoint = endpoint or "https://ark.cn-beijing.volces.com"
        self.model = model.strip()
        if not self.model:
            raise ValueError("Doubao model must be provided via DOUBAO_MODEL")
        self.fallback_model = (fallback_model or "").strip() or None
        if self.fallback_model == self.model:
            self.fallback_model = None

    def get_provider_name(self) -> str:
        return "doubao"

    @staticmethod
    def _pixels_for_resolution(resolution: str) -> int:
        try:
            width_text, height_text = resolution.lower().split("x", 1)
            return int(width_text) * int(height_text)
        except Exception:
            return 0

    @staticmethod
    def _minimum_pixels_for_model(model_name: str) -> int:
        model = (model_name or "").strip().lower()
        if not model:
            return 0
        if "seedream-4.5" in model or "seedream-4-5" in model:
            return 2560 * 1440
        if "seedream-4.0" in model or "seedream-4-0" in model or "seedream-4" in model:
            return 1280 * 720
        return 0

    def _minimum_pixels_required(self) -> int:
        required = self._minimum_pixels_for_model(self.model)
        if self.fallback_model:
            required = max(required, self._minimum_pixels_for_model(self.fallback_model))
        return required

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
        Doubao Seedream models supported resolutions.
        Format: WIDTHxHEIGHT
        """
        minimum_pixels = self._minimum_pixels_required()
        if minimum_pixels <= 0:
            return dict(self._BASE_RESOLUTIONS)

        filtered = {
            resolution: desc
            for resolution, desc in self._BASE_RESOLUTIONS.items()
            if self._pixels_for_resolution(resolution) >= minimum_pixels
        }

        # Defensive fallback: keep at least one valid high-resolution option.
        return filtered or {"2048x2048": self._BASE_RESOLUTIONS["2048x2048"]}

    @staticmethod
    def _is_model_unavailable_error(error_text: str) -> bool:
        text = (error_text or "").lower()
        if not text:
            return False

        model_tokens = ("model", "模型")
        unavailable_tokens = (
            "unsupported",
            "not found",
            "does not exist",
            "invalid",
            "unavailable",
            "not available",
            "not enabled",
            "unknown model",
            "未开通",
            "不存在",
            "不支持",
            "不可用",
            "非法",
            "无权限",
        )
        return any(token in text for token in model_tokens) and any(
            token in text for token in unavailable_tokens
        )

    async def _request_generation(
        self,
        session: aiohttp.ClientSession,
        model: str,
        prompt: str,
        size: str,
        negative_prompt: str,
        headers: Dict[str, str],
    ) -> tuple[Optional[Dict], int, str]:
        request_data = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": size,
            "response_format": "b64_json",
        }
        if negative_prompt:
            request_data["negative_prompt"] = negative_prompt

        async with session.post(
            f"{self.endpoint}/api/v3/images/generations",
            headers=headers,
            json=request_data,
            timeout=aiohttp.ClientTimeout(total=60),
        ) as response:
            status_code = response.status

            if status_code != 200:
                return None, status_code, await response.text()

            response_data = await response.json()
            if "error" in response_data:
                error_payload = response_data["error"]
                if isinstance(error_payload, dict):
                    error_text = error_payload.get("message") or json.dumps(error_payload, ensure_ascii=False)
                else:
                    error_text = str(error_payload)
                return None, status_code, error_text

            return response_data, status_code, ""

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
            debug_print(
                f"[DEBUG] Doubao generate_images call started: query={query}, style={style}, "
                f"resolution={resolution}, model={self.model}, fallback_model={self.fallback_model}"
            )

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

            # Prepare headers
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            models_to_try = [self.model]
            if self.fallback_model:
                models_to_try.append(self.fallback_model)

            debug_print(f"[DEBUG] Calling Doubao Ark API with prompt: {full_prompt}")
            async with aiohttp.ClientSession() as session:
                for index, model_name in enumerate(models_to_try):
                    response_data, status_code, error_text = await self._request_generation(
                        session=session,
                        model=model_name,
                        prompt=full_prompt,
                        size=f"{width}x{height}",
                        negative_prompt=negative_prompt,
                        headers=headers,
                    )

                    if response_data is None:
                        debug_print(
                            f"[ERROR] Doubao API request failed: model={model_name}, "
                            f"status={status_code}, error={error_text}"
                        )

                        has_fallback = index == 0 and len(models_to_try) > 1
                        if has_fallback and self._is_model_unavailable_error(error_text):
                            debug_print(
                                f"[WARNING] Doubao model '{model_name}' unavailable, "
                                f"retrying with fallback '{models_to_try[1]}'"
                            )
                            continue

                        return [{
                            "error": f"Doubao API request failed: HTTP {status_code}, {error_text}",
                            "content_type": "text/plain"
                        }]

                    # Extract image data (Ark API returns OpenAI-compatible format)
                    if "data" not in response_data or not response_data["data"]:
                        debug_print("[ERROR] No data in Doubao response")
                        return [{
                            "error": "No image data returned from Doubao API",
                            "content_type": "text/plain"
                        }]

                    debug_print(f"[DEBUG] Doubao API response received with model={model_name}")

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
                        "content_type": "image/png",
                        "description": query,
                        "style": style,
                        "provider": self.get_provider_name()
                    }]

                    debug_print(f"[DEBUG] Returning Doubao result successfully with model={model_name}")
                    return result

                return [{
                    "error": "Doubao API request failed after trying all configured models",
                    "content_type": "text/plain"
                }]

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
