import asyncio
import httpx
import threading
import time
from config import ServerConfig
from mcp_image_server_http import MCPImageServerHTTP
import uvicorn

# Create config with different port
config = ServerConfig(
    transport="http",
    host="127.0.0.1",
    port=8002,
    auth_token=None,  # Disable auth for testing
    image_save_dir="./test_images"
)

print(f"Config: {config}")

# Create server
server = MCPImageServerHTTP(config)
app = server.create_app()

print(f"App created with routes: {[r.path for r in app.routes]}")

# Run in thread
def run():
    print("Starting uvicorn...")
    uvicorn.run(app, host=config.host, port=config.port, log_level="info")

thread = threading.Thread(target=run, daemon=True)
thread.start()

time.sleep(3)

# Test endpoints
async def test():
    base = f"http://{config.host}:{config.port}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        print(f"\n[1] Testing {base}/health")
        try:
            r = await client.get(f"{base}/health")
            print(f"  Status: {r.status_code}")
            print(f" Response: {r.json()}")
        except Exception as e:
            print(f"  Error: {e}")
        
        print(f"\n[2] Testing {base}/mcp/v1/messages (initialize)")
        try:
            r = await client.post(f"{base}/mcp/v1/messages", json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1.0"}
                }
            })
            print(f"  Status: {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                print(f"  Session: {r.headers.get('Mcp-Session-Id')}")
                print(f"  Server: {data.get('result', {}).get('serverInfo')}")
        except Exception as e:
            print(f"  Error: {e}")

asyncio.run(test())
print("\n✅ Test completed")
