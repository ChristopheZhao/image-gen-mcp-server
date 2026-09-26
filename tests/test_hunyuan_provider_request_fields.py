import asyncio
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcp_image_server.providers.hunyuan_provider import HunyuanProvider


class _StrictSubmitHunyuanImageJobRequest:
    __slots__ = ("Prompt", "Resolution", "Revise", "LogoAdd", "Style", "NegativePrompt")

    def __init__(self):
        self.Prompt = None
        self.Resolution = None
        self.Revise = None
        self.LogoAdd = None
        self.Style = None
        self.NegativePrompt = None


class HunyuanProviderRequestFieldTests(unittest.TestCase):
    def test_submit_request_only_uses_supported_fields(self):
        fake_client = MagicMock()
        fake_client.SubmitHunyuanImageJob.return_value = SimpleNamespace(JobId="job-123")

        with patch("mcp_image_server.providers.hunyuan_provider.credential.Credential"), patch(
            "mcp_image_server.providers.hunyuan_provider.hunyuan_client.HunyuanClient",
            return_value=fake_client,
        ), patch(
            "mcp_image_server.providers.hunyuan_provider.hunyuan_models.SubmitHunyuanImageJobRequest",
            _StrictSubmitHunyuanImageJobRequest,
        ):
            provider = HunyuanProvider(secret_id="sid", secret_key="skey")
            with patch.object(
                provider,
                "_wait_for_job_completion",
                AsyncMock(return_value={"image_data": b"fake-bytes", "url": "https://example.com/image.jpg"}),
            ):
                result = asyncio.run(
                    provider.generate_images(
                        query="a mountain",
                        style="riman",
                        resolution="1024:1024",
                        negative_prompt="blur, low quality",
                    )
                )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["provider"], "hunyuan")
        self.assertEqual(result[0]["content_type"], "image/jpeg")

        submit_request = fake_client.SubmitHunyuanImageJob.call_args.args[0]
        self.assertEqual(submit_request.Prompt, "a mountain")
        self.assertEqual(submit_request.Resolution, "1024:1024")
        self.assertEqual(submit_request.Revise, 1)
        self.assertEqual(submit_request.LogoAdd, 0)
        self.assertEqual(submit_request.Style, "riman")
        self.assertEqual(submit_request.NegativePrompt, "blur, low quality")

    def test_unknown_style_is_not_sent(self):
        fake_client = MagicMock()
        fake_client.SubmitHunyuanImageJob.return_value = SimpleNamespace(JobId="job-123")

        with patch("mcp_image_server.providers.hunyuan_provider.credential.Credential"), patch(
            "mcp_image_server.providers.hunyuan_provider.hunyuan_client.HunyuanClient",
            return_value=fake_client,
        ), patch(
            "mcp_image_server.providers.hunyuan_provider.hunyuan_models.SubmitHunyuanImageJobRequest",
            _StrictSubmitHunyuanImageJobRequest,
        ):
            provider = HunyuanProvider(secret_id="sid", secret_key="skey")
            with patch.object(
                provider,
                "_wait_for_job_completion",
                AsyncMock(return_value={"image_data": b"fake-bytes", "url": "https://example.com/image.jpg"}),
            ):
                asyncio.run(
                    provider.generate_images(
                        query="a mountain",
                        style="not_a_style",
                        resolution="1024:1024",
                    )
                )

        submit_request = fake_client.SubmitHunyuanImageJob.call_args.args[0]
        self.assertIsNone(submit_request.Style)
        self.assertIsNone(submit_request.NegativePrompt)


if __name__ == "__main__":
    unittest.main()
