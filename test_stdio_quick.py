#!/usr/bin/env python3
"""Quick stdio transport test"""
import json
import subprocess
import os
import sys

# Change to script directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Set environment
env = os.environ.copy()
env['MCP_TRANSPORT'] = 'stdio'

# Prepare initialize request
init_request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1.0"}
    }
}

list_tools = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
}

# Combine requests
requests = json.dumps(init_request) + "\n" + json.dumps(list_tools) + "\n"

print("🧪 测试 stdio transport")
print("="*70)

try:
    # Run server with input
    proc = subprocess.Popen(
        [sys.executable, "mcp_image_server_unified.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True
    )

    # Send requests and get responses
    stdout, stderr = proc.communicate(input=requests, timeout=10)

    # Parse responses
    lines = [line for line in stdout.strip().split('\n') if line.strip()]

    print(f"\n收到 {len(lines)} 个响应\n")

    passed = 0
    failed = 0

    for i, line in enumerate(lines[:2]):  # Only check first 2 responses
        try:
            data = json.loads(line)
            if "result" in data:
                if i == 0:  # Initialize response
                    server_info = data['result'].get('serverInfo', {})
                    print(f"✅ 测试 1: Initialize 成功")
                    print(f"   服务器: {server_info.get('name')}")
                    print(f"   版本: {server_info.get('version')}")
                    passed += 1
                elif i == 1:  # Tools list response
                    tools = data['result'].get('tools', [])
                    print(f"\n✅ 测试 2: List Tools 成功")
                    print(f"   工具数量: {len(tools)}")
                    if tools:
                        print(f"   工具名称: {tools[0]['name']}")
                    passed += 1
            else:
                print(f"❌ 测试 {i+1} 失败: {data.get('error')}")
                failed += 1
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败: {e}")
            print(f"   内容: {line[:100]}")
            failed += 1

    if stderr:
        print(f"\n服务器日志:\n{stderr}")

    print("\n" + "="*70)
    if passed == 2 and failed == 0:
        print("✅ stdio transport 回归测试通过！")
        sys.exit(0)
    else:
        print(f"⚠️  测试结果: {passed} 通过, {failed} 失败")
        sys.exit(1)

except subprocess.TimeoutExpired:
    print("❌ 超时")
    proc.kill()
    sys.exit(1)
except Exception as e:
    print(f"❌ 异常: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
