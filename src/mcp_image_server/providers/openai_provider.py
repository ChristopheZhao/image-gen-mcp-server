import openai
import base64
import json
from typing import Dict, List, Optional
import asyncio
import aiohttp
import sys
from .base import BaseImageProvider, debug_print

class OpenAIProvider(BaseImageProvider):
    """OpenAI image generation provider (GPT Image series)"""

    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model = model.strip()
        if not self.model:
            raise ValueError("OpenAI model must be provided via OPENAI_MODEL")
        if not self.model.startswith("gpt-image"):
            raise ValueError(
                "Unsupported OpenAI image model. "
                "Only GPT Image models are supported (for example: gpt-image-1.5). "
                f"Got: {self.model}"
            )

    def get_provider_name(self) -> str:
        return "openai"

    def get_available_styles(self) -> Dict[str, str]:
        return {
            "natural": "自然风格",
            "vivid": "生动风格",
            "realistic": "写实风格",
            "artistic": "艺术风格",
            "cartoon": "卡通风格",
            "anime": "动漫风格",
            "oil_painting": "油画风格",
            "watercolor": "水彩风格",
            "sketch": "素描风格",
            "digital_art": "数字艺术",
            "photographic": "摄影风格",
            "minimalist": "极简风格"
        }

    def get_available_resolutions(self) -> Dict[str, str]:
        return {
            "1024x1024": "1024x1024 (1:1 正方形)",
            "1536x1024": "1536x1024 (3:2 横向)",
            "1024x1536": "1024x1536 (2:3 竖向)"
        }

    async def generate_images(
        self,
        query: str,
        style: str = "natural",
        resolution: str = "1024x1024",
        negative_prompt: str = "",
        **kwargs
    ) -> List[Dict]:
        """Generate images using OpenAI image generation API"""
        try:
            debug_print(f"[DEBUG] OpenAI generate_images call started: model={self.model}, query={query}, style={style}, resolution={resolution}")

            # Prepare the prompt with style
            styled_prompt = query
            if style and style != "natural":
                style_desc = self.get_available_styles().get(style, style)
                styled_prompt = f"{query}, {style_desc}"

            if negative_prompt:
                styled_prompt = f"{styled_prompt}. Avoid: {negative_prompt}"

            debug_print(f"[DEBUG] Calling OpenAI API with model={self.model}, prompt: {styled_prompt}")

            # GPT Image models: no legacy DALL-E style/response_format parameters.
            response = await self.client.images.generate(
                model=self.model,
                prompt=styled_prompt,
                size=resolution,
                quality="auto",
                n=1
            )

            debug_print(f"[DEBUG] OpenAI API call successful")

            if not response.data:
                debug_print("[ERROR] No image data returned from OpenAI")
                return [{
                    "error": "No image data returned from OpenAI API",
                    "content_type": "text/plain"
                }]

            image_data = response.data[0]

            if not image_data.b64_json:
                debug_print("[ERROR] No base64 image data in response")
                return [{
                    "error": "No base64 image data in OpenAI response",
                    "content_type": "text/plain"
                }]

            debug_print(f"[DEBUG] Image successfully generated, base64 length: {len(image_data.b64_json)}")

            result = [{
                "content": image_data.b64_json,
                "content_type": "image/png",
                "description": query,
                "style": style,
                "provider": self.get_provider_name(),
                "revised_prompt": getattr(image_data, 'revised_prompt', None)
            }]

            debug_print(f"[DEBUG] Returning OpenAI result: {result[0].keys()}")
            return result

        except openai.RateLimitError as e:
            error_msg = f"OpenAI API rate limit exceeded: {str(e)}"
            debug_print(f"[ERROR] {error_msg}")
            return [{
                "error": error_msg,
                "content_type": "text/plain"
            }]
        except openai.APIError as e:
            error_msg = f"OpenAI API error: {str(e)}"
            debug_print(f"[ERROR] {error_msg}")
            return [{
                "error": error_msg,
                "content_type": "text/plain"
            }]
        except Exception as e:
            error_msg = str(e)
            debug_print(f"[ERROR] Unexpected error in OpenAI provider: {error_msg}")
            import traceback
            traceback.print_exc(file=sys.stderr)
            return [{
                "error": f"Error occurred during OpenAI image generation: {error_msg}",
                "content_type": "text/plain"
            }]
