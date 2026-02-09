#!/usr/bin/env python3
"""
Simple stdio transport test - sends initialize request
"""
import json
import subprocess
import sys
import os

def test_stdio():
    """Test stdio transport"""
    print("🧪 测试 stdio transport")
    print("="*70)

    # Set environment for stdio mode
    env = os.environ.copy()
    env['MCP_TRANSPORT'] = 'stdio'

    # Start server
    python_path = os.path.join(os.path.dirname(sys.executable), 'python3')
    if not os.path.exists(python_path):
        python_path = sys.executable

    proc = subprocess.Popen(
        [python_path, "mcp_image_server_unified.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
        bufsize=1
    )

    try:
        # Test 1: Initialize
        print("\n📋 测试 1: Initialize")
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }

        request_json = json.dumps(init_request)
        print(f"   发送: {request_json[:80]}...")

        proc.stdin.write(request_json + "\n")
        proc.stdin.flush()

        # Wait for response with timeout
        import select
        import time
        start = time.time()
        timeout = 10

        while time.time() - start < timeout:
            if proc.poll() is not None:
                print(f"❌ 服务器异常退出，退出码: {proc.returncode}")
                stderr = proc.stderr.read()
                if stderr:
                    print(f"   错误信息:\n{stderr}")
                return False

            # Try to read line with short timeout
            ready, _, _ = select.select([proc.stdout], [], [], 0.5)
            if ready:
                response = proc.stdout.readline()
                if response:
                    try:
                        data = json.loads(response)
                        if "result" in data:
                            server_info = data['result'].get('serverInfo', {})
                            print(f"✅ Initialize 成功")
                            print(f"   服务器: {server_info.get('name', 'unknown')}")
                            print(f"   版本: {server_info.get('version', 'unknown')}")

                            # Test 2: List tools
                            print("\n📋 测试 2: List Tools")
                            list_tools = {
                                "jsonrpc": "2.0",
                                "id": 2,
                                "method": "tools/list",
                                "params": {}
                            }

                            proc.stdin.write(json.dumps(list_tools) + "\n")
                            proc.stdin.flush()

                            # Read tools response
                            time.sleep(0.5)
                            ready, _, _ = select.select([proc.stdout], [], [], 5)
                            if ready:
                                response2 = proc.stdout.readline()
                                if response2:
                                    data2 = json.loads(response2)
                                    if "result" in data2:
                                        tools = data2['result'].get('tools', [])
                                        print(f"✅ List Tools 成功: {len(tools)} 个工具")
                                        for tool in tools:
                                            print(f"   - {tool['name']}")
                                    else:
                                        print(f"⚠️  List Tools 响应异常: {data2.get('error')}")

                            print("\n✅ stdio transport 回归测试通过！")
                            return True
                        elif "error" in data:
                            print(f"❌ Initialize 失败: {data['error']}")
                            return False
                        else:
                            print(f"⚠️  未预期的响应格式: {data}")
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON 解析失败: {e}")
                        print(f"   响应内容: {response}")
                        return False

        print(f"❌ 超时：{timeout}秒内没有收到响应")
        stderr = proc.stderr.read()
        if stderr:
            print(f"   错误信息:\n{stderr}")
        return False

    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        stderr = proc.stderr.read()
        if stderr:
            print(f"   错误信息:\n{stderr}")
        return False
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except:
            proc.kill()

if __name__ == "__main__":
    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    success = test_stdio()
    sys.exit(0 if success else 1)
