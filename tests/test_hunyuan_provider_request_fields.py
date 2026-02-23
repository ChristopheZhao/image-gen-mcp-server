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


class _StrictSubmitTextToImageJobRequest:
    __slots__ = ("Prompt", "Resolution", "Revise", "LogoAdd")

    def __init__(self):
        self.Prompt = None
        self.Resolution = None
        self.Revise = None
        self.LogoAdd = None


class HunyuanProviderRequestFieldTests(unittest.TestCase):
    def test_submit_request_only_uses_supported_fields(self):
        fake_client = MagicMock()
        fake_client.SubmitTextToImageJob.return_value = SimpleNamespace(JobId="job-123")

        with patch("mcp_image_server.providers.hunyuan_provider.credential.Credential"), patch(
            "mcp_image_server.providers.hunyuan_provider.aiart_client.AiartClient",
            return_value=fake_client,
        ), patch(
            "mcp_image_server.providers.hunyuan_provider.aiart_models.SubmitTextToImageJobRequest",
            _StrictSubmitTextToImageJobRequest,
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
                    )
                )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["provider"], "hunyuan")
        self.assertEqual(result[0]["content_type"], "image/jpeg")

        submit_request = fake_client.SubmitTextToImageJob.call_args.args[0]
        self.assertEqual(submit_request.Resolution, "1024:1024")
        self.assertEqual(submit_request.Revise, 1)
        self.assertEqual(submit_request.LogoAdd, 0)


if __name__ == "__main__":
    unittest.main()
