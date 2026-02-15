# MCP 图像生成服务器 - HTTP 传输指南

本指南介绍如何使用 HTTP 传输连接和使用 MCP 图像生成服务器，支持远程访问和企业部署。

## 目录

- [概述](#概述)
- [快速开始](#快速开始)
- [配置详解](#配置详解)
- [HTTP API 文档](#http-api-文档)
- [认证和安全](#认证和安全)
- [客户端开发](#客户端开发)
- [部署指南](#部署指南)
- [故障排查](#故障排查)

---

## 概述

### MCP 传输协议对比

| 特性 | stdio 传输 | HTTP 传输 |
|------|-----------|----------|
| 使用场景 | 本地 IDE 集成 | 远程访问、企业部署 |
| 连接方式 | 子进程通信 | HTTP/HTTPS 网络 |
| 多客户端 | ❌ 单客户端 | ✅ 多客户端并发 |
| 远程访问 | ❌ 不支持 | ✅ 支持 |
| 会话管理 | 无需 | UUID 会话 |
| 认证 | 无需 | Bearer Token |
| 部署复杂度 | 简单 | 中等 |

### HTTP 传输优势

- ✅ **远程访问**: 支持跨网络访问，不限于本地
- ✅ **多客户端**: 支持多个客户端同时连接
- ✅ **企业部署**: 适合集中式服务部署
- ✅ **云原生**: 兼容容器、Kubernetes等云平台
- ✅ **标准协议**: 使用标准HTTP/HTTPS协议
- ✅ **负载均衡**: 可配合负载均衡器使用
- ✅ **可监控**: 便于监控和日志记录

---

## 快速开始

### 1. 安装依赖

使用 uv 安装项目依赖：

```bash
# 安装项目
uv pip install -e .
```

### 2. 配置环境

创建 `.env` 文件：

```bash
# 传输配置
MCP_TRANSPORT=http
MCP_HOST=127.0.0.1
MCP_PORT=8000

# 图像生成API配置（至少选择一个）
# OpenAI
OPENAI_API_KEY=sk-your-openai-key

# 或 腾讯混元
TENCENT_SECRET_ID=your-tencent-id
TENCENT_SECRET_KEY=your-tencent-key

# 或 豆包
DOUBAO_ACCESS_KEY=your-doubao-key
DOUBAO_SECRET_KEY=your-doubao-secret
```

### 3. 启动服务器

```bash
# 使用统一入口启动
python mcp_image_server_unified.py

# 或直接启动HTTP服务器
python -c "
from config import ServerConfig
from mcp_image_server_http import run_http_server
config = ServerConfig()
run_http_server(config)
"
```

服务器启动后会显示：

```
Starting MCP Image Generation Server...
Transport mode: http
Using HTTP transport: 127.0.0.1:8000
==================================================
Multi-API Image Generation MCP HTTP Server Starting...
Available providers: ['openai']
HTTP server: 127.0.0.1:8000
Authentication: Disabled
==================================================
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### 4. 测试连接

```bash
# 健康检查
curl http://127.0.0.1:8000/health

# 运行完整测试
python test_mcp_server.py

# 测试图像生成（需要API key）
python test_mcp_server.py --with-api
```

### 5. 使用客户端示例

```bash
# 基础探索
python example_http_client.py basic

# 生成图像
python example_http_client.py generate
```

---

## 配置详解

### 环境变量配置

所有配置项均可通过环境变量设置：

#### 传输配置

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `MCP_TRANSPORT` | `http` | 传输协议（`http` 或 `stdio`） |
| `MCP_HOST` | `127.0.0.1` | HTTP 服务器绑定地址 |
| `MCP_PORT` | `8000` | HTTP 服务器端口 |

#### 安全配置

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `MCP_AUTH_TOKEN` | `None` | Bearer Token（留空则禁用认证） |
| `MCP_ALLOWED_ORIGINS` | `["*"]` | 允许的来源列表（CORS） |

#### 会话管理

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `MCP_ENABLE_SESSIONS` | `true` | 是否启用会话管理 |
| `MCP_SESSION_TIMEOUT` | `3600` | 会话超时时间（秒） |
| `MCP_SESSION_CLEANUP_INTERVAL` | `300` | 会话清理间隔（秒） |

#### SSE 配置

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `MCP_ENABLE_SSE` | `true` | 是否启用 SSE 流 |
| `MCP_SSE_KEEPALIVE` | `30` | SSE 保活间隔（秒） |

#### 日志配置

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `MCP_LOG_LEVEL` | `INFO` | 日志级别（DEBUG/INFO/WARNING/ERROR） |
| `MCP_DEBUG` | `false` | 是否启用调试模式 |

#### 图像生成配置

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `MCP_IMAGE_SAVE_DIR` | `./generated_images` | 图像保存目录 |
| `MCP_PUBLIC_BASE_URL` | `None` | 生成图片外链的基础地址（建议公网部署时设置） |

#### API 提供商配置

**OpenAI DALL-E 3:**
- `OPENAI_API_KEY`: OpenAI API密钥（必需）
- `OPENAI_BASE_URL`: 自定义API端点（可选）

**腾讯混元:**
- `TENCENT_SECRET_ID`: 腾讯云Secret ID（必需）
- `TENCENT_SECRET_KEY`: 腾讯云Secret Key（必需）

**豆包:**
- `DOUBAO_ACCESS_KEY`: 豆包Access Key（必需）
- `DOUBAO_SECRET_KEY`: 豆包Secret Key（必需）
- `DOUBAO_ENDPOINT`: 自定义端点（可选）

### 配置示例

#### 开发环境配置

```bash
# .env.development
MCP_TRANSPORT=http
MCP_HOST=127.0.0.1
MCP_PORT=8000
MCP_DEBUG=true
MCP_LOG_LEVEL=DEBUG
# 本地直接访问可不设置，默认按 host:port 生成 URL
# MCP_PUBLIC_BASE_URL=http://127.0.0.1:8000

# 禁用认证（本地开发）
# MCP_AUTH_TOKEN=

OPENAI_API_KEY=sk-dev-key
```

#### 生产环境配置

```bash
# .env.production
MCP_TRANSPORT=http
MCP_HOST=0.0.0.0  # 监听所有接口
MCP_PORT=8000
MCP_DEBUG=false
MCP_LOG_LEVEL=INFO
# 通过公网域名/反向代理访问时必须设置，确保 images[].url 可外部访问
MCP_PUBLIC_BASE_URL=https://mcp.your-domain.com

# 启用认证（必需）
MCP_AUTH_TOKEN=your-secure-random-token-here

# 限制来源
MCP_ALLOWED_ORIGINS=["https://your-app.com"]

# 会话配置
MCP_SESSION_TIMEOUT=7200
MCP_SESSION_CLEANUP_INTERVAL=300

OPENAI_API_KEY=${OPENAI_API_KEY}  # 从密钥管理器读取
```

---

## HTTP API 文档

### 端点列表

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/health` | 健康检查 |
| `POST` | `/mcp/v1/messages` | 发送 JSON-RPC 消息 |
| `GET` | `/mcp/v1/messages` | 订阅 SSE 事件流 |
| `DELETE` | `/mcp/v1/messages` | 删除会话 |
| `GET` | `/images/{filename}` | 访问已生成图片文件 |

说明：`/images/*` 默认不要求 Bearer Token，便于前端直接渲染图片 URL。

### 1. 健康检查

```bash
GET /health
```

**响应:**

```json
{
  "status": "healthy",
  "service": "mcp-image-generation-http"
}
```

### 2. MCP 消息端点

#### POST /mcp/v1/messages

发送 JSON-RPC 消息到服务器。

**请求头:**

```
Content-Type: application/json
Authorization: Bearer <token>  # 如果启用了认证
Mcp-Session-Id: <session-id>  # 初始化后的请求需要
```

**请求体:**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "method_name",
  "params": {
    // 方法参数
  }
}
```

**响应头:**

```
Mcp-Session-Id: <new-session-id>  # 初始化时返回
```

**响应体:**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    // 结果数据
  }
}
```

### 3. 支持的 JSON-RPC 方法

#### initialize

初始化 MCP 连接，建立会话。

**请求:**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {
      "name": "my-client",
      "version": "1.0.0"
    }
  }
}
```

**响应:**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": {},
      "resources": {},
      "prompts": {}
    },
    "serverInfo": {
      "name": "multi-api-image-mcp-http",
      "version": "0.2.0"
    }
  }
}
```

**响应头会包含新的会话ID:**

```
Mcp-Session-Id: 550e8400-e29b-41d4-a716-446655440000
```

#### tools/list

获取可用工具列表。

**请求:**

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list",
  "params": {}
}
```

**响应:**

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "tools": [
      {
        "name": "generate_image",
        "description": "Generate image based on prompt using multiple API providers",
        "inputSchema": {
          "type": "object",
          "properties": {
            "prompt": {
              "type": "string",
              "description": "Image description text"
            },
            "provider": {
              "type": "string",
              "description": "API provider to use (hunyuan/openai/doubao)",
              "default": ""
            },
            "style": {
              "type": "string",
              "description": "Image style",
              "default": ""
            },
            "resolution": {
              "type": "string",
              "description": "Image resolution",
              "default": ""
            },
            "negative_prompt": {
              "type": "string",
              "description": "Negative prompt",
              "default": ""
            },
            "file_prefix": {
              "type": "string",
              "description": "Filename prefix",
              "default": ""
            }
          },
          "required": ["prompt"]
        }
      }
    ]
  }
}
```

#### tools/call

调用工具执行操作。

**请求:**

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "generate_image",
    "arguments": {
      "prompt": "a cute cat sitting in the sun",
      "provider": "openai",
      "style": "natural",
      "resolution": "1024x1024",
      "file_prefix": "cat"
    }
  }
}
```

**响应（成功）:**

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "isError": false,
    "structuredContent": {
      "version": "1.0",
      "ok": true,
      "images": [
        {
          "id": "img_openai_1707304800",
          "provider": "openai",
          "mime_type": "image/png",
          "file_name": "cat_openai_1707304800.png",
          "local_path": "/abs/path/generated_images/cat_openai_1707304800.png",
          "url": "https://mcp.your-domain.com/images/cat_openai_1707304800.png",
          "size_bytes": 1543210,
          "revised_prompt": null,
          "save_error": null
        }
      ],
      "error": null
    },
    "content": [
      {
        "type": "text",
        "text": "{\"version\":\"1.0\",\"ok\":true,\"images\":[{\"id\":\"img_openai_1707304800\",\"provider\":\"openai\",\"mime_type\":\"image/png\",\"file_name\":\"cat_openai_1707304800.png\",\"local_path\":\"/abs/path/generated_images/cat_openai_1707304800.png\",\"url\":\"https://mcp.your-domain.com/images/cat_openai_1707304800.png\",\"size_bytes\":1543210,\"revised_prompt\":null,\"save_error\":null}],\"error\":null}"
      },
      {
        "type": "image",
        "mimeType": "image/png",
        "data": "<base64 image data>"
      }
    ]
  }
}
```

说明：
- 当 `MCP_PUBLIC_BASE_URL` 已配置时，`images[].url` 会使用该地址生成外部可访问链接。
- 未配置时会尝试使用 `http://<MCP_HOST>:<MCP_PORT>`；若 `MCP_HOST=0.0.0.0` 或 `::`，则 `images[].url` 可能为 `null`。

**响应（失败）:**

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "isError": true,
    "structuredContent": {
      "version": "1.0",
      "ok": false,
      "images": [],
      "error": {
        "code": "provider_unavailable",
        "message": "Provider 'xxx' not available.",
        "details": {}
      }
    },
    "content": [
      {
        "type": "text",
        "text": "{\"version\":\"1.0\",\"ok\":false,\"images\":[],\"error\":{\"code\":\"provider_unavailable\",\"message\":\"Provider 'xxx' not available.\",\"details\":{}}}"
      }
    ]
  }
}
```

#### resources/list

获取可用资源列表。

**请求:**

```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "resources/list",
  "params": {}
}
```

**响应:**

```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "result": {
    "resources": [
      {
        "uri": "providers://list",
        "name": "Available Providers",
        "description": "List of available image generation API providers",
        "mimeType": "application/json"
      },
      {
        "uri": "styles://list",
        "name": "All Styles",
        "description": "All available image styles from all providers",
        "mimeType": "application/json"
      },
      {
        "uri": "resolutions://list",
        "name": "All Resolutions",
        "description": "All available image resolutions from all providers",
        "mimeType": "application/json"
      }
    ]
  }
}
```

#### resources/read

读取资源内容。

**请求:**

```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "method": "resources/read",
  "params": {
    "uri": "providers://list"
  }
}
```

**响应:**

```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "result": {
    "contents": [
      {
        "uri": "providers://list",
        "mimeType": "application/json",
        "text": "[\"openai\", \"hunyuan\", \"doubao\"]"
      }
    ]
  }
}
```

#### prompts/list

获取提示模板列表。

**请求:**

```json
{
  "jsonrpc": "2.0",
  "id": 6,
  "method": "prompts/list",
  "params": {}
}
```

**响应:**

```json
{
  "jsonrpc": "2.0",
  "id": 6,
  "result": {
    "prompts": [
      {
        "name": "image_generation_prompt",
        "description": "Create image generation prompt template",
        "arguments": [
          {
            "name": "description",
            "description": "Image description",
            "required": true
          },
          {
            "name": "provider",
            "description": "API provider",
            "required": false
          }
        ]
      }
    ]
  }
}
```

### 4. SSE 事件流

#### GET /mcp/v1/messages

订阅服务器推送的事件流（Server-Sent Events）。

**请求头:**

```
Authorization: Bearer <token>
Mcp-Session-Id: <session-id>  # 必需
```

**响应:**

```
Content-Type: text/event-stream
Cache-Control: no-cache
X-Accel-Buffering: no
```

**事件格式:**

```
event: connected
id: 0
data: {"status":"connected"}

event: message
id: 1
data: {"jsonrpc":"2.0","method":"notifications/progress","params":{...}}

event: ping
id: 2
data: {"type":"keepalive"}
```

### 5. 会话删除

#### DELETE /mcp/v1/messages

删除当前会话。

**请求头:**

```
Mcp-Session-Id: <session-id>
```

**响应:**

```
HTTP/1.1 204 No Content
```

---

## 认证和安全

### 启用认证

设置 `MCP_AUTH_TOKEN` 环境变量：

```bash
export MCP_AUTH_TOKEN="your-secure-random-token-here"
```

### 生成安全 Token

```python
import secrets
token = secrets.token_urlsafe(32)
print(f"MCP_AUTH_TOKEN={token}")
```

### 客户端使用认证

在所有请求中添加 `Authorization` 头：

```bash
curl -X POST http://127.0.0.1:8000/mcp/v1/messages \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{...}}'
```

注意：`/images/*` 静态图片路由默认不要求 `Authorization`，用于支持浏览器直接加载 `images[].url`。

### 安全最佳实践

1. **生产环境必须启用认证**
   ```bash
   MCP_AUTH_TOKEN=<strong-random-token>
   ```

2. **使用 HTTPS（通过反向代理）**
   ```nginx
   server {
       listen 443 ssl;
       server_name api.example.com;

       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

3. **限制允许的来源**
   ```bash
   MCP_ALLOWED_ORIGINS=["https://your-app.com"]
   ```

4. **配置会话超时**
   ```bash
   MCP_SESSION_TIMEOUT=3600  # 1小时
   ```

5. **使用强密码管理工具**
   - 使用 AWS Secrets Manager
   - 使用 HashiCorp Vault
   - 使用 Kubernetes Secrets

---

## 客户端开发

### Python 客户端示例

完整示例见 [`example_http_client.py`](./example_http_client.py)

基础使用：

```python
import asyncio
import httpx

async def main():
    base_url = "http://127.0.0.1:8000"
    session_id = None

    async with httpx.AsyncClient() as client:
        # 1. 初始化
        response = await client.post(
            f"{base_url}/mcp/v1/messages",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "my-client", "version": "1.0"}
                }
            }
        )
        session_id = response.headers.get("Mcp-Session-Id")

        # 2. 调用工具
        response = await client.post(
            f"{base_url}/mcp/v1/messages",
            headers={"Mcp-Session-Id": session_id},
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "generate_image",
                    "arguments": {"prompt": "a cute cat"}
                }
            }
        )
        result = response.json()
        print(result)

asyncio.run(main())
```

### JavaScript/TypeScript 客户端

```typescript
class MCPClient {
  private baseUrl: string;
  private sessionId?: string;
  private requestId = 0;

  constructor(baseUrl: string = "http://127.0.0.1:8000") {
    this.baseUrl = baseUrl;
  }

  async initialize() {
    const response = await fetch(`${this.baseUrl}/mcp/v1/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: ++this.requestId,
        method: "initialize",
        params: {
          protocolVersion: "2024-11-05",
          capabilities: {},
          clientInfo: { name: "js-client", version: "1.0.0" }
        }
      })
    });

    this.sessionId = response.headers.get("Mcp-Session-Id");
    return await response.json();
  }

  async generateImage(prompt: string, options = {}) {
    const response = await fetch(`${this.baseUrl}/mcp/v1/messages`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Mcp-Session-Id": this.sessionId
      },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: ++this.requestId,
        method: "tools/call",
        params: {
          name: "generate_image",
          arguments: { prompt, ...options }
        }
      })
    });

    return await response.json();
  }
}

// 使用示例
const client = new MCPClient();
await client.initialize();
const result = await client.generateImage("a cute cat");
console.log(result);
```

### curl 测试命令

```bash
# 1. 初始化
SESSION_ID=$(curl -s -X POST http://127.0.0.1:8000/mcp/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {"name": "curl-client", "version": "1.0"}
    }
  }' -D - | grep "Mcp-Session-Id" | cut -d: -f2 | tr -d ' \r')

echo "Session ID: $SESSION_ID"

# 2. 生成图像
curl -X POST http://127.0.0.1:8000/mcp/v1/messages \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: $SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "generate_image",
      "arguments": {
        "prompt": "a cute cat",
        "provider": "openai"
      }
    }
  }' | jq .
```

---

## 部署指南

### 本地开发部署

```bash
# 1. 创建虚拟环境
uv venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows

# 2. 安装依赖
uv pip install -e .

# 3. 配置环境
cp .env.example .env
# 编辑 .env 设置API keys

# 4. 启动服务器
python mcp_image_server_unified.py
```

### systemd 服务（Linux）

创建 `/etc/systemd/system/mcp-image-server.service`:

```ini
[Unit]
Description=MCP Image Generation Server
After=network.target

[Service]
Type=simple
User=mcp
WorkingDirectory=/opt/mcp-image-server
Environment="PATH=/opt/mcp-image-server/.venv/bin"
EnvironmentFile=/opt/mcp-image-server/.env
ExecStart=/opt/mcp-image-server/.venv/bin/python mcp_image_server_unified.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl enable mcp-image-server
sudo systemctl start mcp-image-server
sudo systemctl status mcp-image-server
```

### Nginx 反向代理

```nginx
upstream mcp_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name api.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;

    location / {
        proxy_pass http://mcp_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE支持
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
        proxy_buffering off;
        proxy_cache off;
    }

    location /health {
        proxy_pass http://mcp_backend/health;
        access_log off;
    }
}
```

### 监控和日志

使用 journalctl 查看日志：

```bash
# 查看服务日志
sudo journalctl -u mcp-image-server -f

# 查看最近100行
sudo journalctl -u mcp-image-server -n 100

# 查看错误日志
sudo journalctl -u mcp-image-server -p err
```

---

## 故障排查

### 常见问题

#### 1. 无法连接到服务器

```bash
❌ httpx.ConnectError: Connection refused
```

**解决方案:**
- 检查服务器是否运行：`curl http://127.0.0.1:8000/health`
- 检查端口是否正确：`MCP_PORT=8000`
- 检查防火墙设置

#### 2. 认证失败

```bash
❌ 401 Unauthorized
```

**解决方案:**
- 检查是否设置了 `Authorization` 头
- 验证 token 是否正确
- 确认服务器 `MCP_AUTH_TOKEN` 配置

#### 3. 会话不存在

```bash
❌ 404 Session not found
```

**解决方案:**
- 确保先调用 `initialize` 获取会话ID
- 检查 `Mcp-Session-Id` 头是否正确
- 会话可能已过期，重新初始化

#### 4. 无可用提供商

```bash
No provider specified and no default provider available
```

**解决方案:**
- 检查是否设置了 API keys：
  ```bash
  echo $OPENAI_API_KEY
  echo $TENCENT_SECRET_ID
  ```
- 验证 API keys 格式正确
- 查看服务器启动日志

#### 5. 图像生成失败

```bash
Image generation error: API rate limit exceeded
```

**解决方案:**
- 检查 API 配额和限制
- 等待一段时间后重试
- 切换到其他提供商

### 调试模式

启用调试日志：

```bash
export MCP_DEBUG=true
export MCP_LOG_LEVEL=DEBUG
python mcp_image_server_unified.py
```

### 测试工具

```bash
# 1. 运行协议测试
python test_mcp_server.py

# 2. 运行功能测试（需要API key）
python test_mcp_server.py --with-api

# 3. 使用示例客户端
python example_http_client.py basic
```

---

## 相关文档

- [README.md](./README.md) - 项目概述
- [example_http_client.py](./example_http_client.py) - HTTP 客户端示例
- [test_mcp_server.py](./test_mcp_server.py) - 测试脚本
- [MCP 协议规范](https://spec.modelcontextprotocol.io/) - 官方协议文档

---

## 支持

如有问题或建议，请提交 Issue 到项目仓库。
