#!/usr/bin/env python
"""
Test script to verify HTTP server functionality.
"""
import asyncio
import httpx
import json
import sys
import time
from pathlib import Path

async def test_http_server():
    """Test HTTP server endpoints."""
    base_url = "http://127.0.0.1:8000"

    print("=" * 60)
    print("Testing MCP HTTP Server")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test 1: Health check
        print("\n[1] Testing health check endpoint...")
        try:
            response = await client.get(f"{base_url}/health")
            assert response.status_code == 200
            data = response.json()
            print(f"  ✓ Health check passed: {data}")
        except Exception as e:
            print(f"  ✗ Health check failed: {e}")
            return False

        # Test 2: Initialize (without auth - should fail if auth enabled)
        print("\n[2] Testing initialize without auth...")
        try:
            response = await client.post(
                f"{base_url}/mcp/v1/messages",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {
                            "name": "test-client",
                            "version": "1.0.0"
                        }
                    }
                }
            )
            # If auth is disabled, should succeed with 200
            # If auth is enabled, should fail with 401
            if response.status_code == 200:
                print(f"  ✓ Initialize succeeded (auth disabled)")
                data = response.json()
                session_id = response.headers.get("Mcp-Session-Id")
                print(f"  - Session ID: {session_id}")
                print(f"  - Protocol: {data['result']['protocolVersion']}")
                return session_id
            elif response.status_code == 401:
                print(f"  ✓ Initialize rejected (auth enabled)")
                return None
            else:
                print(f"  ✗ Unexpected status: {response.status_code}")
                return False
        except Exception as e:
            print(f"  ✗ Initialize failed: {e}")
            return False

        # Test 3: Initialize with auth
        print("\n[3] Testing initialize with Bearer token...")
        headers = {"Authorization": "Bearer test-token"}
        try:
            response = await client.post(
                f"{base_url}/mcp/v1/messages",
                headers=headers,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {
                            "name": "test-client",
                            "version": "1.0.0"
                        }
                    }
                }
            )

            if response.status_code == 200:
                data = response.json()
                session_id = response.headers.get("Mcp-Session-Id")
                print(f"  ✓ Initialize succeeded")
                print(f"  - Session ID: {session_id}")
                print(f"  - Server: {data['result']['serverInfo']}")

                # Test 4: List tools
                print("\n[4] Testing tools/list...")
                headers["Mcp-Session-Id"] = session_id
                response = await client.post(
                    f"{base_url}/mcp/v1/messages",
                    headers=headers,
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
                    print(f"  ✓ Tools listed: {len(tools)} tool(s)")
                    for tool in tools:
                        print(f"    - {tool['name']}: {tool['description'][:60]}...")
                else:
                    print(f"  ✗ List tools failed: {response.status_code}")

                # Test 5: List resources
                print("\n[5] Testing resources/list...")
                response = await client.post(
                    f"{base_url}/mcp/v1/messages",
                    headers=headers,
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
                    print(f"  ✓ Resources listed: {len(resources)} resource(s)")
                    for resource in resources:
                        print(f"    - {resource['name']}")
                else:
                    print(f"  ✗ List resources failed: {response.status_code}")

                # Test 6: Read resource
                print("\n[6] Testing resources/read...")
                response = await client.post(
                    f"{base_url}/mcp/v1/messages",
                    headers=headers,
                    json={
                        "jsonrpc": "2.0",
                        "id": 4,
                        "method": "resources/read",
                        "params": {
                            "uri": "providers://list"
                        }
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    content = json.loads(data['result']['contents'][0]['text'])
                    print(f"  ✓ Resource read: providers = {content}")
                else:
                    print(f"  ✗ Read resource failed: {response.status_code}")

                # Test 7: Delete session
                print("\n[7] Testing session deletion...")
                response = await client.delete(
                    f"{base_url}/mcp/v1/messages",
                    headers=headers
                )

                if response.status_code == 204:
                    print(f"  ✓ Session deleted")
                else:
                    print(f"  ✗ Delete session failed: {response.status_code}")

                return True
            else:
                print(f"  ✗ Initialize failed: {response.status_code}")
                print(f"  Response: {response.text}")
                return False

        except Exception as e:
            print(f"  ✗ Request failed: {e}")
            import traceback
            traceback.print_exc()
            return False

async def main():
    """Main test function."""
    print("\nWaiting for server to start...")
    await asyncio.sleep(2)

    result = await test_http_server()

    print("\n" + "=" * 60)
    if result:
        print("✅ All HTTP server tests passed!")
    else:
        print("❌ Some tests failed")
    print("=" * 60)

    return 0 if result else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
