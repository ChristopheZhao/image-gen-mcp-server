import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcp_image_server.providers.doubao_provider import DoubaoProvider


class DoubaoFallbackLogicTests(unittest.TestCase):
    def test_detects_model_unavailable_errors(self):
        self.assertTrue(
            DoubaoProvider._is_model_unavailable_error(
                "Model doubao-seedream-4.5 is not enabled for this account"
            )
        )
        self.assertTrue(
            DoubaoProvider._is_model_unavailable_error(
                "请求失败：模型暂未开通"
            )
        )

    def test_ignores_non_model_errors(self):
        self.assertFalse(DoubaoProvider._is_model_unavailable_error("rate limit exceeded"))
        self.assertFalse(DoubaoProvider._is_model_unavailable_error("network timeout"))

    def test_disables_fallback_when_same_as_primary(self):
        provider = DoubaoProvider(
            api_key="test-key",
            model="doubao-seedream-4.5",
            fallback_model="doubao-seedream-4.5",
        )
        self.assertIsNone(provider.fallback_model)

    def test_filters_low_resolutions_for_seedream_4_models(self):
        provider = DoubaoProvider(
            api_key="test-key",
            model="doubao-seedream-4-0-250828",
        )
        resolutions = provider.get_available_resolutions()

        self.assertNotIn("512x512", resolutions)
        self.assertNotIn("768x768", resolutions)
        self.assertIn("1024x1024", resolutions)

    def test_uses_stricter_resolution_limit_when_fallback_is_seedream_45(self):
        provider = DoubaoProvider(
            api_key="test-key",
            model="doubao-seedream-4-0-250828",
            fallback_model="doubao-seedream-4-5-251128",
        )
        resolutions = provider.get_available_resolutions()

        self.assertNotIn("1024x1024", resolutions)
        self.assertIn("2560x1440", resolutions)
        self.assertIn("2048x2048", resolutions)


if __name__ == "__main__":
    unittest.main()
