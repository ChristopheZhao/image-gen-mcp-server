#!/usr/bin/env python3
"""
MCP HTTP客户端示例

演示如何通过HTTP传输连接MCP图像生成服务器，并调用图像生成功能。
"""

import asyncio
import httpx
import json
import sys
from typing import Optional


class MCPHTTPClient:
    """MCP HTTP客户端"""

    def __init__(self, base_url: str = "http://127.0.0.1:8000", auth_token: Optional[str] = None):
        """
        初始化客户端

        Args:
            base_url: MCP服务器地址
            auth_token: 认证token（如果服务器启用了认证）
        """
        self.base_url = base_url
        self.auth_token = auth_token
        self.session_id: Optional[str] = None
        self.request_id = 0

    def _get_headers(self) -> dict:
        """获取请求头"""
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        return headers

    def _next_request_id(self) -> int:
        """获取下一个请求ID"""
        self.request_id += 1
        return self.request_id

    async def initialize(self, client: httpx.AsyncClient) -> bool:
        """
        初始化MCP连接

        Returns:
            bool: 是否成功
        """
        print("🔌 初始化MCP连接...")

        response = await client.post(
            f"{self.base_url}/mcp/v1/messages",
            headers=self._get_headers(),
            json={
                "jsonrpc": "2.0",
                "id": self._next_request_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "mcp-http-example-client",
                        "version": "1.0.0"
                    }
                }
            }
        )

        if response.status_code == 200:
            data = response.json()
            self.session_id = response.headers.get("Mcp-Session-Id")

            print(f"✅ 连接成功")
            print(f"   会话ID: {self.session_id}")
            print(f"   协议版本: {data['result']['protocolVersion']}")
            print(f"   服务器: {data['result']['serverInfo']['name']} v{data['result']['serverInfo']['version']}")
            return True
        else:
            print(f"❌ 初始化失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return False

    async def list_tools(self, client: httpx.AsyncClient) -> list:
        """
        获取可用工具列表

        Returns:
            list: 工具列表
        """
        print("\n🔧 获取工具列表...")

        response = await client.post(
            f"{self.base_url}/mcp/v1/messages",
            headers=self._get_headers(),
            json={
                "jsonrpc": "2.0",
                "id": self._next_request_id(),
                "method": "tools/list",
                "params": {}
            }
        )

        if response.status_code == 200:
            data = response.json()
            tools = data['result']['tools']

            print(f"✅ 发现 {len(tools)} 个工具:")
            for tool in tools:
                print(f"\n   📦 {tool['name']}")
                print(f"      {tool['description']}")
                required = tool['inputSchema'].get('required', [])
                print(f"      必需参数: {', '.join(required) if required else '无'}")

            return tools
        else:
            print(f"❌ 获取工具失败: {response.status_code}")
            return []

    async def list_resources(self, client: httpx.AsyncClient) -> list:
        """
        获取可用资源列表

        Returns:
            list: 资源列表
        """
        print("\n📚 获取资源列表...")

        response = await client.post(
            f"{self.base_url}/mcp/v1/messages",
            headers=self._get_headers(),
            json={
                "jsonrpc": "2.0",
                "id": self._next_request_id(),
                "method": "resources/list",
                "params": {}
            }
        )

        if response.status_code == 200:
            data = response.json()
            resources = data['result']['resources']

            print(f"✅ 发现 {len(resources)} 个资源:")
            for resource in resources:
                print(f"   📄 {resource['name']}: {resource['uri']}")

            return resources
        else:
            print(f"❌ 获取资源失败: {response.status_code}")
            return []

    async def read_resource(self, client: httpx.AsyncClient, uri: str) -> Optional[dict]:
        """
        读取资源内容

        Args:
            uri: 资源URI

        Returns:
            Optional[dict]: 资源内容
        """
        print(f"\n📖 读取资源: {uri}")

        response = await client.post(
            f"{self.base_url}/mcp/v1/messages",
            headers=self._get_headers(),
            json={
                "jsonrpc": "2.0",
                "id": self._next_request_id(),
                "method": "resources/read",
                "params": {"uri": uri}
            }
        )

        if response.status_code == 200:
            data = response.json()
            content_text = data['result']['contents'][0]['text']
            content = json.loads(content_text)

            print(f"✅ 读取成功:")
            print(f"   {json.dumps(content, indent=2, ensure_ascii=False)}")

            return content
        else:
            print(f"❌ 读取失败: {response.status_code}")
            return None

    async def generate_image(
        self,
        client: httpx.AsyncClient,
        prompt: str,
        provider: Optional[str] = None,
        style: Optional[str] = None,
        resolution: Optional[str] = None,
        file_prefix: Optional[str] = None
    ) -> bool:
        """
        生成图像

        Args:
            prompt: 图像描述
            provider: API提供商（hunyuan/openai/doubao）
            style: 图像风格
            resolution: 图像分辨率
            file_prefix: 文件名前缀

        Returns:
            bool: 是否成功
        """
        print(f"\n🎨 生成图像...")
        print(f"   提示词: {prompt}")
        if provider:
            print(f"   提供商: {provider}")
        if style:
            print(f"   风格: {style}")
        if resolution:
            print(f"   分辨率: {resolution}")

        arguments = {"prompt": prompt}
        if provider:
            arguments["provider"] = provider
        if style:
            arguments["style"] = style
        if resolution:
            arguments["resolution"] = resolution
        if file_prefix:
            arguments["file_prefix"] = file_prefix

        response = await client.post(
            f"{self.base_url}/mcp/v1/messages",
            headers=self._get_headers(),
            json={
                "jsonrpc": "2.0",
                "id": self._next_request_id(),
                "method": "tools/call",
                "params": {
                    "name": "generate_image",
                    "arguments": arguments
                }
            },
            timeout=120.0  # 图像生成可能需要较长时间
        )

        if response.status_code == 200:
            data = response.json()
            result = data['result']['content'][0]

            if result['type'] == 'text':
                text = result['text']

                try:
                    payload = json.loads(text)
                except Exception:
                    print(f"❌ 非结构化返回:")
                    print(f"   {text}")
                    return False

                if payload.get("ok"):
                    images = payload.get("images", [])
                    image = images[0] if images else {}
                    print(f"✅ 图像生成成功！")
                    print(f"   provider: {image.get('provider')}")
                    print(f"   local_path: {image.get('local_path')}")
                    print(f"   url: {image.get('url')}")
                    print(f"   mime_type: {image.get('mime_type')}")
                    if image.get("save_error"):
                        print(f"   ⚠️ save_error: {image.get('save_error')}")
                    return True

                error = payload.get("error") or {}
                print(f"❌ 图像生成失败:")
                print(f"   code: {error.get('code')}")
                print(f"   message: {error.get('message')}")
                return False
            else:
                print(f"❌ 未知的返回类型: {result['type']}")
                return False
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"   响应: {response.text[:200]}")
            return False

    async def close(self, client: httpx.AsyncClient):
        """关闭连接（删除会话）"""
        if not self.session_id:
            return

        print(f"\n🔒 关闭连接...")

        response = await client.delete(
            f"{self.base_url}/mcp/v1/messages",
            headers=self._get_headers()
        )

        if response.status_code == 204:
            print(f"✅ 会话已关闭")
        else:
            print(f"⚠️  会话关闭失败: {response.status_code}")


async def example_basic_usage():
    """示例: 基础使用"""
    print("="*70)
    print("示例1: 基础使用 - 探索服务器功能")
    print("="*70)

    client = MCPHTTPClient(base_url="http://127.0.0.1:8000")

    async with httpx.AsyncClient(timeout=30.0) as http_client:
        # 初始化连接
        if not await client.initialize(http_client):
            return

        # 列出工具
        await client.list_tools(http_client)

        # 列出资源
        await client.list_resources(http_client)

        # 读取提供商列表
        await client.read_resource(http_client, "providers://list")

        # 关闭连接
        await client.close(http_client)


async def example_generate_image():
    """示例: 生成图像"""
    print("\n" + "="*70)
    print("示例2: 生成图像（需要API key）")
    print("="*70)

    # 检查是否有API key
    import os
    has_key = any([
        os.getenv("OPENAI_API_KEY"),
        os.getenv("TENCENT_SECRET_ID"),
        os.getenv("DOUBAO_ACCESS_KEY")
    ])

    if not has_key:
        print("\n⚠️  未检测到API key，跳过图像生成示例")
        print("   请设置以下环境变量之一：")
        print("   - OPENAI_API_KEY")
        print("   - TENCENT_SECRET_ID + TENCENT_SECRET_KEY")
        print("   - DOUBAO_ACCESS_KEY + DOUBAO_SECRET_KEY")
        return

    client = MCPHTTPClient(base_url="http://127.0.0.1:8000")

    async with httpx.AsyncClient(timeout=150.0) as http_client:
        # 初始化连接
        if not await client.initialize(http_client):
            return

        # 生成图像
        await client.generate_image(
            http_client,
            prompt="一只可爱的小猫坐在阳光下",
            provider="openai",  # 或 "hunyuan", "doubao"
            style="natural",
            file_prefix="example_cat"
        )

        # 关闭连接
        await client.close(http_client)


async def example_with_authentication():
    """示例: 使用认证"""
    print("\n" + "="*70)
    print("示例3: 使用认证连接")
    print("="*70)

    # 如果服务器启用了认证，需要提供token
    client = MCPHTTPClient(
        base_url="http://127.0.0.1:8000",
        auth_token="your-auth-token-here"  # 替换为实际的token
    )

    async with httpx.AsyncClient(timeout=30.0) as http_client:
        if not await client.initialize(http_client):
            print("\n💡 提示: 如果服务器未启用认证，请移除 auth_token 参数")
            return

        await client.list_tools(http_client)
        await client.close(http_client)


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="MCP HTTP客户端示例",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法：

  1. 基础探索（无需API key）:
     python example_http_client.py basic

  2. 生成图像（需要API key）:
     export OPENAI_API_KEY=sk-...
     python example_http_client.py generate

  3. 使用认证:
     python example_http_client.py auth

  4. 运行所有示例:
     python example_http_client.py all
        """
    )
    parser.add_argument(
        "mode",
        choices=["basic", "generate", "auth", "all"],
        default="basic",
        nargs="?",
        help="运行模式"
    )

    args = parser.parse_args()

    try:
        if args.mode == "basic":
            await example_basic_usage()
        elif args.mode == "generate":
            await example_generate_image()
        elif args.mode == "auth":
            await example_with_authentication()
        elif args.mode == "all":
            await example_basic_usage()
            await example_generate_image()
    except httpx.ConnectError:
        print("\n❌ 无法连接到服务器")
        print("   请确保MCP服务器正在运行:")
        print("   python mcp_image_server_unified.py")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n👋 已中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
