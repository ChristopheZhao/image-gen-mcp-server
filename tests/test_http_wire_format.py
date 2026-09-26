"""Wire-format checks for the HTTP JSON-RPC handler.

Strict MCP clients (e.g. the TypeScript SDK used by Claude) validate results with
schemas where optional fields may be omitted but must not be ``null``. These tests
make sure the HTTP transport never emits ``null`` for optional protocol fields and
that JSON-RPC notifications are accepted without a response body.
"""
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from starlette.testclient import TestClient

from mcp_image_server.config import ServerConfig
from mcp_image_server.transports.http_server import MCPImageServerHTTP

TEST_ENV = {
    "MCP_TRANSPORT": "http",
    "MCP_HOST": "127.0.0.1",
    "MCP_PORT": "8000",
    "OPENAI_API_KEY": "openai-test-key",
    "OPENAI_MODEL": "gpt-image-test-a",
}


def _null_paths(obj, path="$"):
    """Return JSON paths whose value is None."""
    found = []
    if obj is None:
        found.append(path)
    elif isinstance(obj, dict):
        for key, value in obj.items():
            found.extend(_null_paths(value, f"{path}.{key}"))
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            found.extend(_null_paths(value, f"{path}[{i}]"))
    return found


class HTTPWireFormatTests(unittest.IsolatedAsyncioTestCase):
    def _server(self):
        return MCPImageServerHTTP(ServerConfig())

    async def test_tools_call_content_has_no_null_fields(self):
        with patch.dict(os.environ, TEST_ENV, clear=True):
            server = self._server()
            response = await server._handle_json_rpc(
                {"jsonrpc": "2.0", "id": 7, "method": "tools/call",
                 "params": {"name": "get_image_data", "arguments": {"image_id": "img_missing_0"}}},
                session=None,
            )
        self.assertIn("result", response, msg=response)
        content = response["result"]["content"]
        self.assertTrue(content)
        for item in content:
            self.assertNotIn("annotations", item, msg=item)
            self.assertEqual(_null_paths(item), [], msg=item)

    async def test_tools_list_has_no_null_fields(self):
        with patch.dict(os.environ, TEST_ENV, clear=True):
            server = self._server()
            response = await server._handle_json_rpc(
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}, session=None
            )
        tools = response["result"]["tools"]
        self.assertTrue(tools)
        for tool in tools:
            self.assertEqual(_null_paths(tool), [], msg=json.dumps(tool, ensure_ascii=False)[:300])

    async def test_initialized_notification_gets_no_response(self):
        with patch.dict(os.environ, TEST_ENV, clear=True):
            server = self._server()
            response = await server._handle_json_rpc(
                {"jsonrpc": "2.0", "method": "notifications/initialized"}, session=None
            )
        self.assertIsNone(response)

    def test_http_notification_returns_202_without_body(self):
        with patch.dict(os.environ, TEST_ENV, clear=True):
            server = self._server()
            with TestClient(server.create_app()) as client:
                r = client.post("/mcp/v1/messages",
                                json={"jsonrpc": "2.0", "method": "notifications/initialized"})
        self.assertEqual(r.status_code, 202, msg=r.text)
        self.assertEqual(r.content, b"")


if __name__ == "__main__":
    unittest.main()
