import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcp_image_server.providers.hunyuan_provider import HunyuanProvider


class HunyuanResultImageParsingTests(unittest.TestCase):
    def test_extract_result_image_url_from_list(self):
        url = HunyuanProvider._extract_result_image_url(
            ["https://example.com/image-1.jpg", "https://example.com/image-2.jpg"]
        )
        self.assertEqual(url, "https://example.com/image-1.jpg")

    def test_extract_result_image_url_from_string(self):
        url = HunyuanProvider._extract_result_image_url("https://example.com/image-1.jpg")
        self.assertEqual(url, "https://example.com/image-1.jpg")

    def test_extract_result_image_url_handles_invalid_payload(self):
        self.assertIsNone(HunyuanProvider._extract_result_image_url([]))
        self.assertIsNone(HunyuanProvider._extract_result_image_url(["", None]))
        self.assertIsNone(HunyuanProvider._extract_result_image_url(None))
        self.assertIsNone(HunyuanProvider._extract_result_image_url({"url": "x"}))


if __name__ == "__main__":
    unittest.main()
