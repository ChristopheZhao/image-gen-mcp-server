import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcp_image_server.config import ServerConfig
from mcp_image_server.transports.http_server import MCPImageServerHTTP


class HTTPReloadConfigTests(unittest.IsolatedAsyncioTestCase):
    def test_list_tools_includes_reload_config(self):
        with patch.dict(
            os.environ,
            {
                "MCP_TRANSPORT": "http",
                "MCP_HOST": "127.0.0.1",
                "MCP_PORT": "8000",
                "OPENAI_API_KEY": "openai-test-key",
                "OPENAI_MODEL": "gpt-image-test-a",
                "DOUBAO_API_KEY": "doubao-test-key",
                "DOUBAO_MODEL": "doubao-seedream-test-a",
                "DOUBAO_FALLBACK_MODEL": "doubao-seedream-fallback-a",
            },
            clear=True,
        ):
            server = MCPImageServerHTTP(ServerConfig())
            tools = self._run(server._list_tools())
            tool_names = [tool.name for tool in tools]
            self.assertIn("reload_config", tool_names)

    async def test_reload_config_updates_provider_models(self):
        with patch.dict(
            os.environ,
            {
                "MCP_TRANSPORT": "http",
                "MCP_HOST": "127.0.0.1",
                "MCP_PORT": "8000",
                "OPENAI_API_KEY": "openai-test-key",
                "OPENAI_MODEL": "gpt-image-test-a",
                "DOUBAO_API_KEY": "doubao-test-key",
                "DOUBAO_MODEL": "doubao-seedream-test-a",
                "DOUBAO_FALLBACK_MODEL": "doubao-seedream-fallback-a",
                "MCP_DEFAULT_PROVIDER": "openai",
            },
            clear=True,
        ):
            server = MCPImageServerHTTP(ServerConfig())
            self.assertEqual(server.provider_manager.get_provider("openai").model, "gpt-image-test-a")
            self.assertEqual(server.provider_manager.get_provider("doubao").model, "doubao-seedream-test-a")
            self.assertEqual(server.provider_manager.default_provider, "openai")

            os.environ["OPENAI_MODEL"] = "gpt-image-test-b"
            os.environ["DOUBAO_MODEL"] = "doubao-seedream-test-b"
            os.environ["DOUBAO_FALLBACK_MODEL"] = "doubao-seedream-fallback-b"
            os.environ["MCP_DEFAULT_PROVIDER"] = "doubao"

            result = await server._reload_config(dotenv_override=False)

            self.assertTrue(result.get("ok"), msg=result)
            changed_fields = result["result"]["changed_fields"]
            self.assertIn("openai_model", changed_fields)
            self.assertIn("doubao_model", changed_fields)
            self.assertIn("doubao_fallback_model", changed_fields)
            self.assertIn("default_provider", changed_fields)
            self.assertEqual(server.provider_manager.get_provider("openai").model, "gpt-image-test-b")
            self.assertEqual(server.provider_manager.get_provider("doubao").model, "doubao-seedream-test-b")
            self.assertEqual(
                server.provider_manager.get_provider("doubao").fallback_model,
                "doubao-seedream-fallback-b",
            )
            self.assertEqual(server.provider_manager.default_provider, "doubao")

    async def test_reload_config_rejects_restart_required_changes(self):
        with patch.dict(
            os.environ,
            {
                "MCP_TRANSPORT": "http",
                "MCP_HOST": "127.0.0.1",
                "MCP_PORT": "8000",
                "OPENAI_API_KEY": "openai-test-key",
                "OPENAI_MODEL": "gpt-image-test-a",
            },
            clear=True,
        ):
            server = MCPImageServerHTTP(ServerConfig())
            os.environ["MCP_PORT"] = "9000"

            result = await server._reload_config(dotenv_override=False)

            self.assertFalse(result.get("ok"), msg=result)
            self.assertEqual(result["error"]["code"], "restart_required")
            self.assertIn("port", result["error"]["details"]["restart_required_fields"])

    async def test_reload_config_rejects_unavailable_default_provider(self):
        with patch.dict(
            os.environ,
            {
                "MCP_TRANSPORT": "http",
                "MCP_HOST": "127.0.0.1",
                "MCP_PORT": "8000",
                "OPENAI_API_KEY": "openai-test-key",
                "OPENAI_MODEL": "gpt-image-test-a",
                "MCP_DEFAULT_PROVIDER": "openai",
            },
            clear=True,
        ):
            server = MCPImageServerHTTP(ServerConfig())
            os.environ["MCP_DEFAULT_PROVIDER"] = "doubao"

            result = await server._reload_config(dotenv_override=False)

            self.assertFalse(result.get("ok"), msg=result)
            self.assertEqual(result["error"]["code"], "invalid_config")

    def _run(self, coro):
        import asyncio

        return asyncio.run(coro)


if __name__ == "__main__":
    unittest.main()
