#!/usr/bin/env python3
"""
Simple test for stdio transport
"""
import json
import subprocess
import sys

def test_stdio():
    """Test stdio transport by sending JSON-RPC messages"""
    print("🧪 测试 stdio transport")
    print("="*70)
    
    # Start server in stdio mode
    env = {"MCP_TRANSPORT": "stdio"}
    
    proc = subprocess.Popen(
        [sys.executable, "mcp_image_server_unified.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**dict(os.environ), **env},
        text=True
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
        
        proc.stdin.write(json.dumps(init_request) + "\n")
        proc.stdin.flush()
        
        response = proc.stdout.readline()
        if response:
            data = json.loads(response)
            if "result" in data:
                print(f"✅ Initialize 成功")
                print(f"   服务器: {data['result']['serverInfo']['name']}")
            else:
                print(f"❌ Initialize 失败: {data.get('error')}")
                return False
        else:
            print("❌ 没有收到响应")
            return False
        
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
        
        response = proc.stdout.readline()
        if response:
            data = json.loads(response)
            if "result" in data:
                tools = data['result']['tools']
                print(f"✅ List Tools 成功: {len(tools)} 个工具")
                for tool in tools:
                    print(f"   - {tool['name']}")
            else:
                print(f"❌ List Tools 失败: {data.get('error')}")
                return False
        
        print("\n✅ stdio transport 测试通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        proc.terminate()
        proc.wait(timeout=5)

if __name__ == "__main__":
    import os
    success = test_stdio()
    sys.exit(0 if success else 1)
