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

from mcp_image_server.providers.openai_provider import OpenAIProvider


class OpenAIProviderModelPolicyTests(unittest.TestCase):
    def test_rejects_non_gpt_image_models(self):
        with patch("mcp_image_server.providers.openai_provider.openai.AsyncOpenAI") as mock_async_openai:
            mock_async_openai.return_value = MagicMock()
            with self.assertRaises(ValueError):
                OpenAIProvider(api_key="test-key", model="dall-e-3")

    def test_gpt_image_request_uses_supported_parameters(self):
        mock_client = MagicMock()
        mock_client.images.generate = AsyncMock(
            return_value=SimpleNamespace(
                data=[SimpleNamespace(b64_json="ZmFrZV9pbWFnZQ==", revised_prompt=None)]
            )
        )

        with patch("mcp_image_server.providers.openai_provider.openai.AsyncOpenAI", return_value=mock_client):
            provider = OpenAIProvider(api_key="test-key", model="gpt-image-1.5")
            result = asyncio.run(
                provider.generate_images(
                    query="a cat",
                    style="natural",
                    resolution="1024x1024",
                    negative_prompt=""
                )
            )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["provider"], "openai")
        self.assertEqual(result[0]["content"], "ZmFrZV9pbWFnZQ==")

        kwargs = mock_client.images.generate.await_args.kwargs
        self.assertEqual(kwargs["model"], "gpt-image-1.5")
        self.assertEqual(kwargs["size"], "1024x1024")
        self.assertEqual(kwargs["quality"], "auto")
        self.assertNotIn("style", kwargs)
        self.assertNotIn("response_format", kwargs)


if __name__ == "__main__":
    unittest.main()
