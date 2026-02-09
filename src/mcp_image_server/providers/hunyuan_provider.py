from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.hunyuan.v20230901 import hunyuan_client, models
import json
import base64
from typing import Dict, List, Optional
import asyncio
import aiohttp
import sys
from .base import BaseImageProvider, debug_print

class HunyuanProvider(BaseImageProvider):
    """Tencent Hunyuan image generation provider"""
    
    def __init__(self, secret_id: str, secret_key: str, **kwargs):
        super().__init__(**kwargs)
        self.cred = credential.Credential(secret_id, secret_key)
        self.client = hunyuan_client.HunyuanClient(self.cred, "ap-guangzhou")
    
    def get_provider_name(self) -> str:
        return "hunyuan"
    
    def get_available_styles(self) -> Dict[str, str]:
        return {
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
    
    def get_available_resolutions(self) -> Dict[str, str]:
        return {
            "768:768": "768:768(1:1 正方形)",
            "768:1024": "768:1024(3:4 竖向)",
            "1024:768": "1024:768(4:3 横向)",
            "1024:1024": "1024:1024(1:1 正方形大图)",
            "720:1280": "720:1280(16:9 竖向)",
            "1280:720": "1280:720(9:16 横向)",
            "768:1280": "768:1280(3:5 竖向)",
            "1280:768": "1280:768(5:3 横向)"
        }
    
    async def generate_images(
        self, 
        query: str, 
        style: str = "riman",
        resolution: str = "1024:1024",
        negative_prompt: str = "",
        **kwargs
    ) -> List[Dict]:
        """Generate images using Hunyuan text-to-image model"""
        try:
            debug_print(f"[DEBUG] Hunyuan generate_images call started: query={query}, style={style}, resolution={resolution}")
            
            # Create request object
            req = models.SubmitHunyuanImageJobRequest()
            
            # Set request parameters
            req.Prompt = query
            req.Style = style
            req.Resolution = resolution
            req.Num = 1  # Default generate 1 image
            req.Revise = 1  # Enable prompt expansion
            req.LogoAdd = 0  # No watermark
            
            if negative_prompt:
                req.NegativePrompt = negative_prompt
            
            debug_print(f"[DEBUG] Calling Tencent API SubmitHunyuanImageJob: Prompt={query}, Style={style}, Resolution={resolution}")
            
            # Try to call interface, retry on failure
            job_id = None
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    resp = self.client.SubmitHunyuanImageJob(req)
                    job_id = resp.JobId
                    debug_print(f"[DEBUG] Successfully submitted task, JobId={job_id}")
                    break
                except TencentCloudSDKException as e:
                    error_msg = str(e)
                    debug_print(f"[ERROR] Task submission failed (attempt {attempt+1}/{max_retries}): {error_msg}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)  # Wait 2 seconds before retrying
                    else:
                        raise  # Retry count exhausted, continue to throw exception
            
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
            
            # Check image data
            if not image_result.get("image_data"):
                debug_print("[ERROR] Image data is empty")
                return [{
                    "error": "Image data is empty",
                    "content_type": "text/plain"
                }]
            
            # Ensure image data is properly encoded
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
            
            # Return result containing all necessary fields
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
            for attempt in range(max_retries):
                req = models.QueryHunyuanImageJobRequest()
                req.JobId = job_id
                
                debug_print(f"[DEBUG] Query task status, attempt #{attempt+1}, JobId={job_id}")
                try:
                    resp = self.client.QueryHunyuanImageJob(req)
                    # Print response content for debugging
                    debug_print(f"[DEBUG] Task status response: {resp.to_json_string()}")
                    
                    # Check task status code
                    status_code = resp.JobStatusCode
                    debug_print(f"[DEBUG] Task status code: {status_code}")
                    
                    if status_code == "5":   # 1: Waiting, 2: Running, 4: Processing failed, 5: Processing completed.
                        if resp.ResultImage and len(resp.ResultImage) > 0:
                            image_url = resp.ResultImage[0]
                            debug_print(f"[DEBUG] Image generation completed, ResultImage: {resp.ResultImage}")
                            debug_print(f"[DEBUG] Start downloading image: {image_url}")
                            
                            # Add retry logic for downloading images
                            for download_attempt in range(3):  # Try downloading 3 times
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
                            debug_print("[ERROR] Task completed but no image result")
                            return None
                    elif status_code == "4":  # Processing failed
                        debug_print("[ERROR] Task processing failed")
                        return None
                    else:
                        debug_print(f"[DEBUG] Task still in progress, status code: {status_code}, waiting...")
                        await asyncio.sleep(2)  # Wait 2 seconds before checking again
                except TencentCloudSDKException as e:
                    error_msg = str(e)
                    debug_print(f"[ERROR] Error querying task status: {error_msg}")
                    await asyncio.sleep(2)  # Wait 2 seconds before retrying
            
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