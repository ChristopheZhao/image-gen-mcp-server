import openai
from typing import Dict, List, Optional
import sys
from .base import BaseImageProvider, debug_print

class OpenAIProvider(BaseImageProvider):
    """OpenAI image generation provider (GPT Image series)"""
    _ALLOWED_BACKGROUNDS = {"transparent", "opaque", "auto"}
    _ALLOWED_OUTPUT_FORMATS = {"png", "jpeg", "webp"}
    _ALLOWED_MODERATION = {"low", "auto"}
    _OUTPUT_MIME_BY_FORMAT = {
        "png": "image/png",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
    }

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
            "1024x1536": "1024x1536 (2:3 竖向)",
            "auto": "auto (由模型自动选择最佳尺寸)",
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

            background = kwargs.get("background")
            output_format = kwargs.get("output_format")
            output_compression = kwargs.get("output_compression")
            moderation = kwargs.get("moderation")

            if isinstance(background, str):
                background = background.strip().lower()
            if isinstance(output_format, str):
                output_format = output_format.strip().lower()
            if isinstance(moderation, str):
                moderation = moderation.strip().lower()

            if background and background not in self._ALLOWED_BACKGROUNDS:
                return [{
                    "error": (
                        f"Invalid OpenAI background '{background}'. "
                        f"Allowed values: {sorted(self._ALLOWED_BACKGROUNDS)}"
                    ),
                    "content_type": "text/plain",
                }]

            if output_format and output_format not in self._ALLOWED_OUTPUT_FORMATS:
                return [{
                    "error": (
                        f"Invalid OpenAI output_format '{output_format}'. "
                        f"Allowed values: {sorted(self._ALLOWED_OUTPUT_FORMATS)}"
                    ),
                    "content_type": "text/plain",
                }]

            if moderation and moderation not in self._ALLOWED_MODERATION:
                return [{
                    "error": (
                        f"Invalid OpenAI moderation '{moderation}'. "
                        f"Allowed values: {sorted(self._ALLOWED_MODERATION)}"
                    ),
                    "content_type": "text/plain",
                }]

            if output_compression is not None and output_compression != "":
                try:
                    output_compression = int(output_compression)
                except (TypeError, ValueError):
                    return [{
                        "error": "Invalid OpenAI output_compression. Expected integer between 0 and 100.",
                        "content_type": "text/plain",
                    }]
                if output_compression < 0 or output_compression > 100:
                    return [{
                        "error": "Invalid OpenAI output_compression. Expected integer between 0 and 100.",
                        "content_type": "text/plain",
                    }]
                if output_format not in {"jpeg", "webp"}:
                    return [{
                        "error": "OpenAI output_compression requires output_format to be 'jpeg' or 'webp'.",
                        "content_type": "text/plain",
                    }]

            debug_print(f"[DEBUG] Calling OpenAI API with model={self.model}, prompt: {styled_prompt}")

            # GPT Image models: no legacy DALL-E style/response_format parameters.
            request_kwargs = {
                "model": self.model,
                "prompt": styled_prompt,
                "size": resolution,
                "quality": "auto",
                "n": 1,
            }
            if background:
                request_kwargs["background"] = background
            if output_format:
                request_kwargs["output_format"] = output_format
            if output_compression is not None and output_compression != "":
                request_kwargs["output_compression"] = output_compression
            if moderation:
                request_kwargs["moderation"] = moderation

            response = await self.client.images.generate(
                **request_kwargs
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
            image_mime_type = self._OUTPUT_MIME_BY_FORMAT.get(output_format, "image/png")

            result = [{
                "content": image_data.b64_json,
                "content_type": image_mime_type,
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
