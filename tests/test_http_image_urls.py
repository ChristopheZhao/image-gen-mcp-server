import asyncio
import base64
import json
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
    def __init__(self, provider_name: str = "fake"):
        self.default_provider = provider_name
        self.provider_name = provider_name
        self._provider = _FakeProvider()
        self.last_generate_kwargs = None

    def get_provider(self, provider_name: str):
        if provider_name == self.provider_name:
            return self._provider
        return None

    def get_available_providers(self):
        return [self.provider_name]

    async def generate_images(self, query: str, provider_name: str, **kwargs):
        self.last_generate_kwargs = kwargs
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

    async def test_generate_image_forwards_openai_options(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ServerConfig(
                transport="http",
                host="127.0.0.1",
                port=8123,
                image_save_dir=tmpdir,
            )
            server = MCPImageServerHTTP(config)
            fake_manager = _FakeProviderManager(provider_name="openai")
            server.provider_manager = fake_manager

            result = await server._generate_image(
                prompt="test prompt",
                provider="openai",
                background="transparent",
                output_format="webp",
                output_compression=70,
                moderation="low",
            )

            self.assertTrue(result.get("ok"))
            self.assertIsNotNone(fake_manager.last_generate_kwargs)
            self.assertEqual(fake_manager.last_generate_kwargs.get("background"), "transparent")
            self.assertEqual(fake_manager.last_generate_kwargs.get("output_format"), "webp")
            self.assertEqual(fake_manager.last_generate_kwargs.get("output_compression"), 70)
            self.assertEqual(fake_manager.last_generate_kwargs.get("moderation"), "low")

    async def test_generate_image_rejects_openai_options_for_other_providers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ServerConfig(
                transport="http",
                host="127.0.0.1",
                port=8123,
                image_save_dir=tmpdir,
            )
            server = MCPImageServerHTTP(config)
            server.provider_manager = _FakeProviderManager(provider_name="doubao")

            result = await server._generate_image(
                prompt="test prompt",
                provider="doubao",
                background="auto",
            )

            self.assertFalse(result.get("ok"))
            self.assertEqual(result["error"]["code"], "invalid_parameters")

    async def test_get_image_data_returns_base64_for_generated_image(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ServerConfig(
                transport="http",
                host="127.0.0.1",
                port=8123,
                image_save_dir=tmpdir,
            )
            server = MCPImageServerHTTP(config)
            server.provider_manager = _FakeProviderManager()

            generate_result = await server._generate_image(prompt="test prompt")
            self.assertTrue(generate_result.get("ok"))
            image_id = generate_result["images"][0]["id"]

            data_result = await server._get_image_data(image_id=image_id)
            self.assertTrue(data_result.get("ok"))
            self.assertEqual(len(data_result.get("images", [])), 1)

            image = data_result["images"][0]
            self.assertIn("base64_data", image)
            decoded = base64.b64decode(image["base64_data"])
            self.assertEqual(decoded, b"fake-image-bytes")

    async def test_get_image_data_returns_error_when_image_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ServerConfig(
                transport="http",
                host="127.0.0.1",
                port=8123,
                image_save_dir=tmpdir,
            )
            server = MCPImageServerHTTP(config)
            server.provider_manager = _FakeProviderManager()

            data_result = await server._get_image_data(image_id="img_not_found")
            self.assertFalse(data_result.get("ok"))
            self.assertEqual(data_result["error"]["code"], "image_not_found")

    async def test_tools_call_get_image_data_keeps_base64_in_text_payload(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ServerConfig(
                transport="http",
                host="127.0.0.1",
                port=8123,
                image_save_dir=tmpdir,
            )
            server = MCPImageServerHTTP(config)
            server.provider_manager = _FakeProviderManager()

            generate_result = await server._generate_image(prompt="test prompt")
            image_id = generate_result["images"][0]["id"]

            rpc_response = await server._handle_json_rpc(
                {
                    "jsonrpc": "2.0",
                    "id": 11,
                    "method": "tools/call",
                    "params": {
                        "name": "get_image_data",
                        "arguments": {"image_id": image_id}
                    }
                },
                session=None
            )

            result = rpc_response["result"]
            self.assertFalse(result["isError"])
            structured = result["structuredContent"]
            self.assertTrue(structured["ok"])
            self.assertIn("base64_data", structured["images"][0])

            content_types = [item["type"] for item in result["content"]]
            self.assertEqual(content_types, ["text"])

            text_payload = json.loads(result["content"][0]["text"])
            self.assertIn("base64_data", text_payload["images"][0])

    async def test_get_image_data_rejects_large_payload(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ServerConfig(
                transport="http",
                host="127.0.0.1",
                port=8123,
                image_save_dir=tmpdir,
                get_image_data_max_bytes=1,
            )
            server = MCPImageServerHTTP(config)
            server.provider_manager = _FakeProviderManager()

            generate_result = await server._generate_image(prompt="test prompt")
            self.assertTrue(generate_result.get("ok"))
            image_id = generate_result["images"][0]["id"]

            data_result = await server._get_image_data(image_id=image_id)
            self.assertFalse(data_result.get("ok"))
            self.assertEqual(data_result["error"]["code"], "payload_too_large")


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

    def test_list_tools_includes_get_image_data(self):
        config = ServerConfig(
            transport="http",
            host="127.0.0.1",
            port=8123,
            image_save_dir="./generated_images",
        )
        server = MCPImageServerHTTP(config)
        tools = asyncio.run(server._list_tools())
        tool_names = [tool.name for tool in tools]
        self.assertIn("generate_image", tool_names)
        self.assertIn("get_image_data", tool_names)

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
