#!/usr/bin/env python3
"""
完整的MCP HTTP服务器测试脚本

分两部分：
1. 协议测试（无需API key）- 测试MCP协议流程
2. 功能测试（需要API key）- 测试真实图像生成
"""

import asyncio
import httpx
import json
import sys
import os
from typing import Optional

# 从配置文件加载配置
try:
    from mcp_image_server.config import ServerConfig
    _config = ServerConfig()
    DEFAULT_BASE_URL = f"http://{_config.host}:{_config.port}"
    DEFAULT_AUTH_TOKEN = _config.auth_token
except Exception as e:
    print(f"⚠️  警告: 无法加载配置文件，使用默认值: {e}")
    DEFAULT_BASE_URL = "http://127.0.0.1:8000"
    DEFAULT_AUTH_TOKEN = None


class MCPServerTester:
    """MCP服务器测试器"""

    def __init__(self, base_url: str = None, auth_token: Optional[str] = None):
        self.base_url = base_url or DEFAULT_BASE_URL
        self.auth_token = auth_token if auth_token is not None else DEFAULT_AUTH_TOKEN
        self.session_id: Optional[str] = None
        self.passed = 0
        self.failed = 0

    def _get_headers(self) -> dict:
        """获取请求头"""
        headers = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        return headers

    def _print_test(self, test_name: str):
        """打印测试名称"""
        print(f"\n{'='*70}")
        print(f"测试: {test_name}")
        print('='*70)

    def _print_result(self, success: bool, message: str):
        """打印测试结果"""
        if success:
            print(f"✅ {message}")
            self.passed += 1
        else:
            print(f"❌ {message}")
            self.failed += 1

    async def test_health_check(self, client: httpx.AsyncClient):
        """测试健康检查端点"""
        self._print_test("健康检查")
        try:
            response = await client.get(f"{self.base_url}/health")

            if response.status_code == 200:
                data = response.json()
                self._print_result(True, f"健康检查通过")
                print(f"  状态: {data.get('status')}")
                print(f"  服务: {data.get('service')}")
            else:
                self._print_result(False, f"健康检查失败: {response.status_code}")
        except Exception as e:
            self._print_result(False, f"健康检查异常: {e}")

    async def test_initialize(self, client: httpx.AsyncClient):
        """测试MCP初始化握手"""
        self._print_test("MCP初始化握手")
        try:
            response = await client.post(
                f"{self.base_url}/mcp/v1/messages",
                headers=self._get_headers(),
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {
                            "name": "mcp-test-client",
                            "version": "1.0.0"
                        }
                    }
                }
            )

            if response.status_code == 200:
                data = response.json()
                self.session_id = response.headers.get("Mcp-Session-Id")

                self._print_result(True, "初始化成功")
                print(f"  会话ID: {self.session_id}")
                print(f"  协议版本: {data['result']['protocolVersion']}")
                print(f"  服务器: {data['result']['serverInfo']['name']} v{data['result']['serverInfo']['version']}")
                print(f"  能力: {', '.join(data['result']['capabilities'].keys())}")
            else:
                self._print_result(False, f"初始化失败: {response.status_code}")
                print(f"  响应: {response.text}")
        except Exception as e:
            import traceback
            self._print_result(False, f"初始化异常: {type(e).__name__}: {e}")
            if str(e):  # 只在有详细信息时打印traceback
                print(f"  详细信息: {traceback.format_exc()}")

    async def test_list_tools(self, client: httpx.AsyncClient):
        """测试获取工具列表"""
        self._print_test("获取工具列表 (tools/list)")
        try:
            response = await client.post(
                f"{self.base_url}/mcp/v1/messages",
                headers=self._get_headers(),
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": {}
                }
            )

            if response.status_code == 200:
                data = response.json()
                tools = data['result']['tools']

                self._print_result(True, f"成功获取 {len(tools)} 个工具")
                for tool in tools:
                    print(f"\n  📦 工具: {tool['name']}")
                    print(f"     描述: {tool['description']}")
                    print(f"     必需参数: {tool['inputSchema'].get('required', [])}")
                    print(f"     可选参数: {[k for k in tool['inputSchema']['properties'].keys() if k not in tool['inputSchema'].get('required', [])]}")
            else:
                self._print_result(False, f"获取工具列表失败: {response.status_code}")
        except Exception as e:
            self._print_result(False, f"获取工具列表异常: {e}")

    async def test_list_resources(self, client: httpx.AsyncClient):
        """测试获取资源列表"""
        self._print_test("获取资源列表 (resources/list)")
        try:
            response = await client.post(
                f"{self.base_url}/mcp/v1/messages",
                headers=self._get_headers(),
                json={
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "resources/list",
                    "params": {}
                }
            )

            if response.status_code == 200:
                data = response.json()
                resources = data['result']['resources']

                self._print_result(True, f"成功获取 {len(resources)} 个资源")
                for resource in resources:
                    print(f"\n  📄 资源: {resource['name']}")
                    print(f"     URI: {resource['uri']}")
                    print(f"     类型: {resource['mimeType']}")
            else:
                self._print_result(False, f"获取资源列表失败: {response.status_code}")
        except Exception as e:
            self._print_result(False, f"获取资源列表异常: {e}")

    async def test_read_resources(self, client: httpx.AsyncClient):
        """测试读取资源内容"""
        self._print_test("读取资源内容 (resources/read)")

        resources_to_test = [
            ("providers://list", "可用提供商"),
            ("styles://list", "所有风格"),
            ("resolutions://list", "所有分辨率"),
        ]

        for uri, description in resources_to_test:
            try:
                response = await client.post(
                    f"{self.base_url}/mcp/v1/messages",
                    headers=self._get_headers(),
                    json={
                        "jsonrpc": "2.0",
                        "id": 4,
                        "method": "resources/read",
                        "params": {"uri": uri}
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    content_text = data['result']['contents'][0]['text']
                    content = json.loads(content_text)

                    self._print_result(True, f"读取 {description}")
                    print(f"  内容: {json.dumps(content, indent=2, ensure_ascii=False)}")
                else:
                    self._print_result(False, f"读取 {description} 失败: {response.status_code}")
            except Exception as e:
                self._print_result(False, f"读取 {description} 异常: {e}")

    async def test_list_prompts(self, client: httpx.AsyncClient):
        """测试获取提示模板"""
        self._print_test("获取提示模板 (prompts/list)")
        try:
            response = await client.post(
                f"{self.base_url}/mcp/v1/messages",
                headers=self._get_headers(),
                json={
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "prompts/list",
                    "params": {}
                }
            )

            if response.status_code == 200:
                data = response.json()
                prompts = data['result']['prompts']

                self._print_result(True, f"成功获取 {len(prompts)} 个提示模板")
                for prompt in prompts:
                    print(f"\n  📝 模板: {prompt['name']}")
                    print(f"     描述: {prompt['description']}")
                    args = [f"{arg['name']}{'*' if arg['required'] else ''}" for arg in prompt['arguments']]
                    print(f"     参数: {', '.join(args)} (* = 必需)")
            else:
                self._print_result(False, f"获取提示模板失败: {response.status_code}")
        except Exception as e:
            self._print_result(False, f"获取提示模板异常: {e}")

    async def test_call_tool_without_key(self, client: httpx.AsyncClient):
        """测试工具调用（无API key）"""
        self._print_test("工具调用测试（无API key - 预期失败）")
        try:
            response = await client.post(
                f"{self.base_url}/mcp/v1/messages",
                headers=self._get_headers(),
                json={
                    "jsonrpc": "2.0",
                    "id": 10,
                    "method": "tools/call",
                    "params": {
                        "name": "generate_image",
                        "arguments": {
                            "prompt": "a cute cat"
                        }
                    }
                },
                timeout=60.0
            )

            if response.status_code == 200:
                data = response.json()
                result = data['result']['content'][0]

                if result['type'] == 'text':
                    text = result['text']
                    try:
                        payload = json.loads(text)
                    except Exception:
                        self._print_result(False, f"非结构化返回内容: {text}")
                        return

                    if payload.get("ok") is False:
                        error = payload.get("error") or {}
                        self._print_result(True, "正确返回了结构化错误")
                        print(f"  错误码: {error.get('code')}")
                        print(f"  消息: {error.get('message')}")
                    else:
                        self._print_result(False, f"意外的返回内容: {payload}")
                else:
                    self._print_result(False, f"意外的返回类型: {result['type']}")
            else:
                self._print_result(False, f"工具调用失败: {response.status_code}")
        except Exception as e:
            self._print_result(False, f"工具调用异常: {e}")

    async def test_call_tool_with_key(self, client: httpx.AsyncClient, provider: str):
        """测试工具调用（有API key）"""
        self._print_test(f"真实图像生成测试 - {provider.upper()}")

        print(f"⏳ 正在调用 {provider} API 生成图像...")
        print(f"   提示词: 一只可爱的小猫")

        try:
            response = await client.post(
                f"{self.base_url}/mcp/v1/messages",
                headers=self._get_headers(),
                json={
                    "jsonrpc": "2.0",
                    "id": 20,
                    "method": "tools/call",
                    "params": {
                        "name": "generate_image",
                        "arguments": {
                            "prompt": "一只可爱的小猫，坐在阳光下",
                            "provider": provider,
                            "file_prefix": "test_cat"
                        }
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
                        self._print_result(False, f"{provider} 返回非结构化内容")
                        print(f"  文本: {text[:300]}")
                        return

                    if payload.get("ok"):
                        image = (payload.get("images") or [{}])[0]
                        self._print_result(True, f"{provider} 图像生成成功")
                        print(f"  provider: {image.get('provider')}")
                        print(f"  local_path: {image.get('local_path')}")
                        print(f"  mime_type: {image.get('mime_type')}")
                        if image.get("save_error"):
                            print(f"  save_error: {image.get('save_error')}")
                    else:
                        error = payload.get("error") or {}
                        self._print_result(False, f"{provider} 图像生成失败")
                        print(f"  code: {error.get('code')}")
                        print(f"  message: {error.get('message')}")
                else:
                    self._print_result(False, f"意外的返回类型: {result['type']}")
            else:
                self._print_result(False, f"{provider} 工具调用失败: {response.status_code}")
                print(f"  响应: {response.text[:200]}")
        except asyncio.TimeoutError:
            self._print_result(False, f"{provider} 请求超时（可能API响应慢）")
        except Exception as e:
            self._print_result(False, f"{provider} 调用异常: {e}")

    async def test_session_cleanup(self, client: httpx.AsyncClient):
        """测试会话清理"""
        self._print_test("会话清理")

        if not self.session_id:
            print("ℹ️  没有活动会话，跳过清理测试")
            return

        try:
            response = await client.delete(
                f"{self.base_url}/mcp/v1/messages",
                headers=self._get_headers()
            )

            if response.status_code == 204:
                self._print_result(True, "会话删除成功")
                print(f"  已删除会话: {self.session_id}")
                self.session_id = None
            else:
                self._print_result(False, f"会话删除失败: {response.status_code}")

        except Exception as e:
            self._print_result(False, f"会话清理异常: {e}")

    async def run_protocol_tests(self):
        """运行协议测试（不需要API key）"""
        print("\n" + "="*70)
        print("第一部分：MCP 协议流程测试（无需API key）")
        print("="*70)
        print("测试目标：验证MCP协议的各个端点是否正常工作")

        async with httpx.AsyncClient(timeout=30.0) as client:
            await self.test_health_check(client)
            await self.test_initialize(client)
            await self.test_list_tools(client)
            await self.test_list_resources(client)
            await self.test_read_resources(client)
            await self.test_list_prompts(client)

            # 只有在没有API key时才测试"无API key"的情况
            providers = check_api_keys()
            if not providers:
                await self.test_call_tool_without_key(client)
            else:
                print("\n" + "="*70)
                print("测试: 工具调用测试（无API key - 跳过）")
                print("="*70)
                print("ℹ️  检测到API keys，跳过此测试（有API key时应该成功生成）")

            await self.test_session_cleanup(client)

    async def run_functional_tests(self, providers: list):
        """运行功能测试（需要API key）"""
        print("\n" + "="*70)
        print("第二部分：图像生成功能测试（需要API key）")
        print("="*70)
        print("测试目标：验证真实的图像生成是否工作")
        print(f"测试提供商: {', '.join(providers)}")

        async with httpx.AsyncClient(timeout=150.0) as client:
            # 重新初始化会话
            await self.test_initialize(client)

            # 测试每个提供商
            for provider in providers:
                await self.test_call_tool_with_key(client, provider)

            # 清理会话
            await self.test_session_cleanup(client)

    def print_summary(self):
        """打印测试总结"""
        print("\n" + "="*70)
        print("📊 测试总结")
        print("="*70)
        print(f"✅ 通过: {self.passed}")
        print(f"❌ 失败: {self.failed}")
        print(f"📈 总计: {self.passed + self.failed}")

        if self.failed == 0:
            print("\n🎉 所有测试通过！MCP服务器工作完全正常。")
            return 0
        else:
            print(f"\n⚠️  有 {self.failed} 个测试失败，请检查服务器配置。")
            return 1


def check_api_keys():
    """检查可用的API keys"""
    # 使用 config 模块加载 .env 文件
    try:
        from mcp_image_server.config import ServerConfig
        config = ServerConfig()
        credentials = config.get_provider_credentials()
        return list(credentials.keys())
    except Exception as e:
        print(f"⚠️  警告: 无法从配置加载提供商: {e}")
        print("   回退到直接检查环境变量...")

        # 回退方案：直接检查环境变量（需要手动 load_dotenv）
        from dotenv import load_dotenv
        load_dotenv()

        available_providers = []
        if os.getenv("OPENAI_API_KEY"):
            available_providers.append("openai")
        if os.getenv("TENCENT_SECRET_ID") and os.getenv("TENCENT_SECRET_KEY"):
            available_providers.append("hunyuan")
        if os.getenv("DOUBAO_API_KEY"):  # 使用新的 API Key
            available_providers.append("doubao")

        return available_providers


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="测试MCP HTTP服务器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法：

  1. 仅测试协议（无需API key）:
     python test_mcp_server.py

  2. 测试协议 + 图像生成:
     python test_mcp_server.py --with-api

  3. 指定服务器地址和认证:
     python test_mcp_server.py --url http://localhost:8000 --token my-token
        """
    )
    parser.add_argument("--url", default=None, help=f"服务器URL（默认: 从.env读取，当前: {DEFAULT_BASE_URL}）")
    parser.add_argument("--token", default=None, help="认证token（默认: 从.env读取）")
    parser.add_argument("--with-api", action="store_true", help="运行图像生成测试（需要API key）")
    args = parser.parse_args()

    # 使用命令行参数或配置文件的值
    base_url = args.url or DEFAULT_BASE_URL
    auth_token = args.token if args.token is not None else DEFAULT_AUTH_TOKEN

    tester = MCPServerTester(base_url=base_url, auth_token=auth_token)

    print(f"📋 测试配置:")
    print(f"   服务器地址: {tester.base_url}")
    print(f"   认证: {'启用' if tester.auth_token else '未启用'}")
    print()

    # 第一部分：协议测试（始终运行）
    await tester.run_protocol_tests()

    # 第二部分：功能测试（如果指定了--with-api）
    if args.with_api:
        providers = check_api_keys()
        if providers:
            print(f"\n✅ 检测到API keys: {', '.join(providers)}")
            await tester.run_functional_tests(providers)
        else:
            print("\n⚠️  未检测到任何API key，跳过图像生成测试")
            print("   请设置以下环境变量之一：")
            print("   - OPENAI_API_KEY (OpenAI DALL-E 3)")
            print("   - TENCENT_SECRET_ID + TENCENT_SECRET_KEY (腾讯混元)")
            print("   - DOUBAO_ACCESS_KEY + DOUBAO_SECRET_KEY (豆包)")
    else:
        print("\n💡 提示：使用 --with-api 参数可测试真实图像生成")

    # 打印总结
    exit_code = tester.print_summary()
    return exit_code


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
