import asyncio
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"


class StdioTransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_stdio_initialize_and_list_capabilities(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env = os.environ.copy()
            env["PYTHONPATH"] = str(SRC_DIR)
            env["MCP_TRANSPORT"] = "stdio"
            env["MCP_IMAGE_SAVE_DIR"] = str(Path(tmpdir) / "generated_images")

            params = StdioServerParameters(
                command=sys.executable,
                args=["-m", "mcp_image_server.main"],
                cwd=tmpdir,
                env=env,
            )

            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    init = await asyncio.wait_for(session.initialize(), timeout=10)
                    self.assertEqual(init.serverInfo.name, "multi-api-image-mcp-stdio")

                    tools = await asyncio.wait_for(session.list_tools(), timeout=10)
                    tool_names = [tool.name for tool in tools.tools]
                    self.assertIn("generate_image", tool_names)
                    self.assertIn("get_image_data", tool_names)
                    self.assertIn("reload_config", tool_names)

                    resources = await asyncio.wait_for(session.list_resources(), timeout=10)
                    resource_uris = [str(resource.uri) for resource in resources.resources]
                    self.assertIn("providers://list", resource_uris)
                    self.assertIn("styles://list", resource_uris)
                    self.assertIn("resolutions://list", resource_uris)

                    prompts = await asyncio.wait_for(session.list_prompts(), timeout=10)
                    prompt_names = [prompt.name for prompt in prompts.prompts]
                    self.assertIn("image_generation_prompt", prompt_names)

    async def test_stdio_read_resource_with_lazy_provider_manager(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env = os.environ.copy()
            env["PYTHONPATH"] = str(SRC_DIR)
            env["MCP_TRANSPORT"] = "stdio"
            env["MCP_IMAGE_SAVE_DIR"] = str(Path(tmpdir) / "generated_images")

            params = StdioServerParameters(
                command=sys.executable,
                args=["-m", "mcp_image_server.main"],
                cwd=tmpdir,
                env=env,
            )

            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await asyncio.wait_for(session.initialize(), timeout=10)
                    resource_result = await asyncio.wait_for(
                        session.read_resource("styles://list"),
                        timeout=10,
                    )
                    self.assertTrue(resource_result.contents)
                    styles_payload = json.loads(resource_result.contents[0].text)
                    self.assertEqual(styles_payload, {})


if __name__ == "__main__":
    unittest.main()
