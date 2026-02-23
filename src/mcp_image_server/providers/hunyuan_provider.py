from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.aiart.v20221229 import aiart_client, models as aiart_models
import json
import base64
from typing import Dict, List, Optional
import asyncio
import aiohttp
import sys
from .base import BaseImageProvider, debug_print

class HunyuanProvider(BaseImageProvider):
    """Tencent HunyuanImage 3.0 image generation provider"""

    def __init__(self, secret_id: str, secret_key: str, **kwargs):
        super().__init__(**kwargs)
        self.cred = credential.Credential(secret_id, secret_key)
        self.client = aiart_client.AiartClient(self.cred, "ap-guangzhou")

    def get_provider_name(self) -> str:
        return "hunyuan"

    @staticmethod
    def _extract_result_image_url(result_image: object) -> Optional[str]:
        """Extract a usable image URL from Tencent ResultImage payload."""
        if isinstance(result_image, str):
            return result_image if result_image else None

        if isinstance(result_image, list):
            for item in result_image:
                if isinstance(item, str) and item:
                    return item

        return None

    def get_available_styles(self) -> Dict[str, str]:
        # HunyuanImage 3.0 has no Style parameter; styles are injected into the prompt
        return {
            "riman": "日漫动画风格, Japanese anime style",
            "xieshi": "写实风格, photorealistic style",
            "monai": "莫奈印象派画风, Monet impressionist painting style",
            "shuimo": "水墨画风格, Chinese ink wash painting style",
            "bianping": "扁平插画风格, flat illustration style",
            "xiangsu": "像素插画风格, pixel art style",
            "ertonghuiben": "儿童绘本风格, children's picture book style",
            "3dxuanran": "3D渲染风格, 3D rendering style",
            "manhua": "漫画风格, comic style",
            "heibaimanhua": "黑白漫画风格, black and white comic style",
            "dongman": "动漫风格, animation style",
            "bijiasuo": "毕加索立体主义风格, Picasso cubism style",
            "saibopengke": "赛博朋克风格, cyberpunk style",
            "youhua": "油画风格, oil painting style",
            "masaike": "马赛克风格, mosaic style",
            "qinghuaci": "青花瓷风格, blue and white porcelain style",
            "xinnianjianzhi": "新年剪纸画风格, New Year paper-cut art style",
            "xinnianhuayi": "新年花艺风格, New Year floral art style"
        }

    def get_available_resolutions(self) -> Dict[str, str]:
        # HunyuanImage 3.0: width and height each in [512, 2048], width*height <= 1024*1024
        return {
            "768:768": "768:768 (1:1 正方形)",
            "768:1024": "768:1024 (3:4 竖向)",
            "1024:768": "1024:768 (4:3 横向)",
            "1024:1024": "1024:1024 (1:1 正方形大图)",
            "720:1280": "720:1280 (9:16 竖向)",  # 720*1280=921600 <= 1024*1024=1048576
            "1280:720": "1280:720 (16:9 横向)",
            "512:1024": "512:1024 (1:2 竖向)",
            "1024:512": "1024:512 (2:1 横向)"
        }

    async def generate_images(
        self,
        query: str,
        style: str = "riman",
        resolution: str = "1024:1024",
        negative_prompt: str = "",
        **kwargs
    ) -> List[Dict]:
        """Generate images using HunyuanImage 3.0 text-to-image model"""
        try:
            debug_print(f"[DEBUG] Hunyuan generate_images call started: query={query}, style={style}, resolution={resolution}")

            # Build prompt: inject style description and negative prompt
            styled_prompt = query
            if style:
                style_desc = self.get_available_styles().get(style, "")
                if style_desc:
                    styled_prompt = f"{query}, {style_desc}"

            if negative_prompt:
                styled_prompt = f"{styled_prompt}. Avoid: {negative_prompt}"

            # Create request object
            req = aiart_models.SubmitTextToImageJobRequest()
            req.Prompt = styled_prompt
            req.Resolution = resolution
            req.Revise = 1  # Enable prompt expansion
            req.LogoAdd = 0  # No watermark

            debug_print(f"[DEBUG] Calling Tencent API SubmitTextToImageJob: Prompt={styled_prompt}, Resolution={resolution}")

            loop = asyncio.get_event_loop()

            # Try to submit job, retry on failure
            job_id = None
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    resp = await loop.run_in_executor(None, self.client.SubmitTextToImageJob, req)
                    job_id = resp.JobId
                    debug_print(f"[DEBUG] Successfully submitted task, JobId={job_id}")
                    break
                except TencentCloudSDKException as e:
                    error_msg = str(e)
                    debug_print(f"[ERROR] Task submission failed (attempt {attempt+1}/{max_retries}): {error_msg}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)
                    else:
                        raise

            if not job_id:
                debug_print("[ERROR] Unable to get task ID")
                return [{
                    "error": "Failed to create image generation task",
                    "content_type": "text/plain"
                }]

            # Wait for task completion and get results
            image_result = await self._wait_for_job_completion(job_id)

            if image_result is None:
                debug_print("[ERROR] Image generation failed, returning empty result")
                return [{
                    "error": "Image generation failed, unable to get image result",
                    "content_type": "text/plain"
                }]

            debug_print(f"[DEBUG] Image generation successful: image_url={image_result.get('url', 'No URL')}")

            if not image_result.get("image_data"):
                debug_print("[ERROR] Image data is empty")
                return [{
                    "error": "Image data is empty",
                    "content_type": "text/plain"
                }]

            try:
                encoded_image = base64.b64encode(image_result["image_data"]).decode('utf-8')
                debug_print(f"[DEBUG] Image successfully encoded to base64, length: {len(encoded_image)}")
            except Exception as e:
                error_msg = str(e)
                debug_print(f"[ERROR] Image encoding failed: {error_msg}")
                return [{
                    "error": f"Image encoding failed: {error_msg}",
                    "content_type": "text/plain"
                }]

            result = [{
                "content": encoded_image,
                "content_type": "image/jpeg",
                "description": query,
                "style": style,
                "provider": self.get_provider_name()
            }]
            debug_print(f"[DEBUG] Returning result: {result[0].keys()}")

            return result

        except TencentCloudSDKException as err:
            error_msg = str(err)
            debug_print(f"[ERROR] Failed to generate image: {error_msg}, Error type: {type(err)}")
            return [{
                "error": f"Hunyuan API call failed: {error_msg}",
                "content_type": "text/plain"
            }]
        except Exception as e:
            error_msg = str(e)
            debug_print(f"[ERROR] Unexpected error: {error_msg}, Error type: {type(e)}")
            import traceback
            traceback.print_exc(file=sys.stderr)
            return [{
                "error": f"Error occurred during Hunyuan image generation: {error_msg}",
                "content_type": "text/plain"
            }]

    async def _wait_for_job_completion(self, job_id: str, max_retries: int = 60) -> Optional[Dict]:
        """Wait for task completion and get results"""
        try:
            debug_print(f"[DEBUG] Start waiting for task completion, JobId={job_id}, max_retries={max_retries}")
            loop = asyncio.get_event_loop()

            for attempt in range(max_retries):
                req = aiart_models.QueryTextToImageJobRequest()
                req.JobId = job_id

                debug_print(f"[DEBUG] Query task status, attempt #{attempt+1}, JobId={job_id}")
                try:
                    resp = await loop.run_in_executor(None, self.client.QueryTextToImageJob, req)
                    debug_print(f"[DEBUG] Task status response: {resp.to_json_string()}")

                    status_code = resp.JobStatusCode
                    debug_print(f"[DEBUG] Task status code: {status_code}")

                    if status_code == "5":   # 1: Waiting, 2: Running, 4: Failed, 5: Completed
                        image_url = self._extract_result_image_url(resp.ResultImage)
                        if image_url:
                            debug_print(f"[DEBUG] Image generation completed, ResultImage: {image_url}")
                            debug_print(f"[DEBUG] Start downloading image: {image_url}")

                            for download_attempt in range(3):
                                image_data = await self._download_image(image_url)
                                if image_data:
                                    debug_print(f"[DEBUG] Image download successful, size: {len(image_data)} bytes")
                                    return {
                                        "image_data": image_data,
                                        "url": image_url
                                    }
                                else:
                                    debug_print(f"[WARNING] Image download failed, attempt #{download_attempt+1}/3")
                                    await asyncio.sleep(1)

                            debug_print("[ERROR] Image download failed, maximum retry count reached")
                            return None
                        else:
                            debug_print(
                                f"[ERROR] Task completed but no usable image result, "
                                f"ResultImage={resp.ResultImage!r}"
                            )
                            return None
                    elif status_code == "4":  # Processing failed
                        debug_print("[ERROR] Task processing failed")
                        return None
                    else:
                        debug_print(f"[DEBUG] Task still in progress, status code: {status_code}, waiting...")
                        await asyncio.sleep(2)
                except TencentCloudSDKException as e:
                    error_msg = str(e)
                    debug_print(f"[ERROR] Error querying task status: {error_msg}")
                    await asyncio.sleep(2)

            debug_print(f"[ERROR] Task not completed after {max_retries} retries")
            return None
        except Exception as e:
            error_msg = str(e)
            debug_print(f"[ERROR] Error waiting for task completion: {error_msg}")
            import traceback
            traceback.print_exc(file=sys.stderr)
            return None

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
