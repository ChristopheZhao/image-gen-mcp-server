import base64
import sys
import tempfile
import unittest
from pathlib import Path

from starlette.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcp_image_server.config import ServerConfig
from mcp_image_server.transports.http_server import MCPImageServerHTTP


class _FakeProvider:
    def validate_style(self, style: str) -> bool:
        return True

    def validate_resolution(self, resolution: str) -> bool:
        return True

    def get_available_styles(self) -> dict:
        return {"default": "default"}

    def get_available_resolutions(self) -> dict:
        return {"1024x1024": "1024x1024"}


class _FakeProviderManager:
    def __init__(self):
        self.default_provider = "fake"
        self._provider = _FakeProvider()

    def get_provider(self, provider_name: str):
        if provider_name == "fake":
            return self._provider
        return None

    def get_available_providers(self):
        return ["fake"]

    async def generate_images(self, query: str, provider_name: str, **kwargs):
        image_data = base64.b64encode(b"fake-image-bytes").decode("ascii")
        return [
            {
                "content": image_data,
                "content_type": "image/png",
                "revised_prompt": None,
            }
        ]


class HTTPImageURLTests(unittest.IsolatedAsyncioTestCase):
    async def test_generate_image_populates_public_url(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ServerConfig(
                transport="http",
                host="127.0.0.1",
                port=8123,
                image_save_dir=tmpdir,
                public_base_url="https://mcp.example.com",
            )
            server = MCPImageServerHTTP(config)
            server.provider_manager = _FakeProviderManager()

            result = await server._generate_image(prompt="test prompt")

            self.assertTrue(result.get("ok"))
            self.assertEqual(len(result.get("images", [])), 1)

            image = result["images"][0]
            self.assertIsNotNone(image.get("local_path"))
            self.assertTrue(Path(image["local_path"]).exists())
            self.assertEqual(
                image.get("url"),
                f"https://mcp.example.com/images/{image.get('file_name')}",
            )

    async def test_generate_image_url_is_none_for_wildcard_host_without_public_base(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ServerConfig(
                transport="http",
                host="0.0.0.0",
                port=8123,
                image_save_dir=tmpdir,
            )
            server = MCPImageServerHTTP(config)
            server.provider_manager = _FakeProviderManager()

            result = await server._generate_image(prompt="test prompt")

            self.assertTrue(result.get("ok"))
            image = result["images"][0]
            self.assertIsNone(image.get("url"))


class HTTPStaticRouteTests(unittest.TestCase):
    def test_images_static_route_is_mounted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ServerConfig(
                transport="http",
                host="127.0.0.1",
                port=8123,
                image_save_dir=tmpdir,
            )
            server = MCPImageServerHTTP(config)
            app = server.create_app()

            image_route_paths = [route.path for route in app.routes]
            self.assertIn("/images", image_route_paths)

    def test_url_builder_uses_host_port_when_public_base_missing(self):
        config = ServerConfig(
            transport="http",
            host="127.0.0.1",
            port=8123,
            image_save_dir="./generated_images",
        )
        server = MCPImageServerHTTP(config)
        url = server._build_public_image_url("demo.png")
        self.assertEqual(url, "http://127.0.0.1:8123/images/demo.png")

    def test_images_route_is_public_even_when_auth_enabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            image_path = Path(tmpdir) / "demo.png"
            image_bytes = b"png-bytes"
            image_path.write_bytes(image_bytes)

            config = ServerConfig(
                transport="http",
                host="127.0.0.1",
                port=8123,
                image_save_dir=tmpdir,
                auth_token="test-token",
            )
            server = MCPImageServerHTTP(config)
            app = server.create_app()

            with TestClient(app) as client:
                image_response = client.get("/images/demo.png")
                self.assertEqual(image_response.status_code, 200)
                self.assertEqual(image_response.content, image_bytes)

                mcp_response = client.get("/mcp/v1/messages")
                self.assertEqual(mcp_response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
