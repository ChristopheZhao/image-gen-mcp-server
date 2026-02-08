# VS Code MCP Integration Guide

本指南介绍如何在 VS Code 中通过 **GitHub Copilot** 集成 MCP Image Generation Server（stdio transport）。

## 方法 1：GitHub Copilot（推荐）

### 前置条件

- ✅ VS Code 已安装
- ✅ 已安装 **GitHub Copilot** 和 **GitHub Copilot Chat** 扩展
- ✅ 项目依赖已安装（`pip install -r requirements.txt`）

### 配置步骤

根据 [GitHub 官方文档](https://docs.github.com/en/copilot/how-tos/provide-context/use-mcp/extend-copilot-chat-with-mcp)，有两种配置方式：

#### 方式 A：项目级配置（推荐用于开发测试）

在项目根目录创建 `.vscode/mcp.json`：

```bash
cd /mnt/d/code/OpenSource/tools/image-gen-mcp-server
mkdir -p .vscode
```

创建 `.vscode/mcp.json` 文件：

```json
{
  "servers": {
    "image-gen-stdio": {
      "command": "/mnt/d/code/OpenSource/tools/image-gen-mcp-server/.venv/bin/python",
      "args": [
        "/mnt/d/code/OpenSource/tools/image-gen-mcp-server/mcp_image_server_unified.py"
      ],
      "env": {
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

**✅ 优点：**
- 配置跟随项目
- 团队成员可共享配置（可选提交到 Git）
- 切换项目时自动切换配置

**Windows 路径示例：**
```json
{
  "servers": {
    "image-gen-stdio": {
      "command": "D:\\code\\OpenSource\\tools\\image-gen-mcp-server\\.venv\\Scripts\\python.exe",
      "args": [
        "D:\\code\\OpenSource\\tools\\image-gen-mcp-server\\mcp_image_server_unified.py"
      ],
      "env": {
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

#### 方式 B：全局配置（推荐用于个人常用）

在 VS Code 的 `settings.json` 中添加 MCP 配置：

1. 打开命令面板（`Ctrl+Shift+P`）
2. 输入 "Preferences: Open User Settings (JSON)"
3. 添加以下配置：

```json
{
  // ... 其他配置 ...
  "chat.mcp.servers": {
    "image-gen-stdio": {
      "command": "/mnt/d/code/OpenSource/tools/image-gen-mcp-server/.venv/bin/python",
      "args": [
        "/mnt/d/code/OpenSource/tools/image-gen-mcp-server/mcp_image_server_unified.py"
      ],
      "env": {
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

**✅ 优点：**
- 全局可用，任何项目都能使用
- 适合个人常用的 MCP 服务器

**⚠️ 注意：** 不要在两个地方同时配置同一个服务器，可能会导致冲突。

#### 方式 C：自动发现（实验性）

在 `settings.json` 中启用：

```json
{
  "chat.mcp.discovery.enabled": true
}
```

VS Code 会自动发现项目中的 `.vscode/mcp.json` 文件。

### 重启 VS Code

配置完成后，完全关闭 VS Code 再重新打开。

### 验证连接

1. 打开 GitHub Copilot Chat（侧边栏或 `Ctrl+Alt+I`）
2. 输入 `@workspace`，查看可用工具
3. 应该能看到 `generate_image` 工具

### 测试图像生成

在 Copilot Chat 中输入：

```
请使用 MCP 工具生成一张可爱的小猫图片
```

或者更具体：

```
@workspace 请调用 generate_image 工具生成图片：
- prompt: 夕阳下的富士山
- provider: hunyuan
- style: xieshi
```

### 查看服务器状态

**方法 1：查看输出面板**
1. 按 `Ctrl+Shift+U` 打开输出面板
2. 在下拉菜单选择 "GitHub Copilot Chat"
3. 查看 MCP 服务器日志

**方法 2：开发者工具**
1. 按 `Ctrl+Shift+P` 打开命令面板
2. 输入 "Developer: Toggle Developer Tools"
3. 在 Console 中查看 MCP 相关日志

### 故障排查

**问题：找不到 .vscode/mcp.json**

在项目根目录创建：
```bash
mkdir -p .vscode
touch .vscode/mcp.json
code .vscode/mcp.json
```

**问题：服务器无法启动**

手动测试服务器：
```bash
cd /mnt/d/code/OpenSource/tools/image-gen-mcp-server
MCP_TRANSPORT=stdio .venv/bin/python mcp_image_server_unified.py
```

应该看到：
```
Starting MCP Image Generation Server...
Transport mode: stdio
Using stdio transport (FastMCP)
[INFO] Hunyuan provider initialized successfully
Available providers: ['hunyuan']
```

**问题：相对路径 vs 绝对路径**

如果使用相对路径，确保从项目根目录启动：
```json
{
  "servers": {
    "image-gen-stdio": {
      "command": ".venv/bin/python",
      "args": ["mcp_image_server_unified.py"],
      "env": {
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

**推荐使用绝对路径避免路径问题。**

---

## 方法 2：Cline/Claude Dev 扩展（备选）

如果你使用 Cline 扩展（第三方 AI 助手）。

### 配置文件位置

**Linux/WSL:**
```bash
~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json
```

**Windows:**
```
%APPDATA%\Code\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json
```

### 配置内容

Cline 使用不同的配置格式：

```json
{
  "mcpServers": {
    "image-gen-stdio": {
      "command": "/path/to/.venv/bin/python",
      "args": ["/path/to/mcp_image_server_unified.py"],
      "env": {
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

### 使用 Cline

1. 打开 Cline 面板（侧边栏）
2. 在 MCP 服务器列表中应该能看到 `image-gen-stdio`
3. 在对话中请求生成图片

---

## 方法 3：Continue 扩展（备选）

另一个支持 MCP 的 AI 编码助手。

### 配置文件位置

```bash
~/.continue/config.json
```

### 配置内容

```json
{
  "models": [...],
  "mcpServers": {
    "image-gen-stdio": {
      "command": "/path/to/.venv/bin/python",
      "args": ["/path/to/mcp_image_server_unified.py"],
      "env": {
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

---

## 快速配置生成器

运行以下命令生成适合你系统的配置：

### 生成项目级配置（推荐）

```bash
cd /mnt/d/code/OpenSource/tools/image-gen-mcp-server

mkdir -p .vscode
cat > .vscode/mcp.json << EOF
{
  "servers": {
    "image-gen-stdio": {
      "command": "$(pwd)/.venv/bin/python",
      "args": [
        "$(pwd)/mcp_image_server_unified.py"
      ],
      "env": {
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
EOF

echo "✅ 配置已生成：.vscode/mcp.json"
cat .vscode/mcp.json
```

### 生成全局配置

```bash
cat > vscode_settings_snippet.json << EOF
{
  "chat.mcp.servers": {
    "image-gen-stdio": {
      "command": "$(pwd)/.venv/bin/python",
      "args": [
        "$(pwd)/mcp_image_server_unified.py"
      ],
      "env": {
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
EOF

echo "✅ 配置已生成，请复制到 VS Code settings.json"
cat vscode_settings_snippet.json
```

---

## 环境变量配置

### 方式 1：使用项目 .env 文件（推荐）

服务器会自动从项目根目录的 `.env` 文件加载 API keys：

```bash
# .env
TENCENT_SECRET_ID=your_secret_id
TENCENT_SECRET_KEY=your_secret_key
```

### 方式 2：在 MCP 配置中直接指定

仅用于测试：

```json
{
  "servers": {
    "image-gen-stdio": {
      "command": "...",
      "args": ["..."],
      "env": {
        "MCP_TRANSPORT": "stdio",
        "TENCENT_SECRET_ID": "your_secret_id",
        "TENCENT_SECRET_KEY": "your_secret_key"
      }
    }
  }
}
```

---

## 预期效果

配置成功后：

1. ✅ GitHub Copilot Chat 可以看到 `generate_image` 工具
2. ✅ 可以通过自然语言或 `@workspace` 调用工具
3. ✅ 生成的图片保存在 `generated_images/` 目录
4. ✅ 工具返回文件路径

### 示例对话

**你：** @workspace 请生成一张图片：夕阳下的富士山

**Copilot：** 我会使用 generate_image 工具...

[调用工具]

**结果：** ✅ Image successfully generated and saved to: generated_images/img_hunyuan_xxx.jpg

---

## 配置对比

| 配置方式 | 位置 | 适用场景 | 优先级 |
|---------|------|----------|--------|
| 项目配置 | `.vscode/mcp.json` | 开发测试、团队共享 | 高 |
| 全局配置 | `settings.json` | 个人常用工具 | 中 |
| Cline | globalStorage | 使用 Cline 扩展 | - |
| Continue | `~/.continue/config.json` | 使用 Continue 扩展 | - |

## 推荐方案

1. **开发测试**：使用项目级 `.vscode/mcp.json`（可提交到 Git）
2. **个人使用**：使用全局 `settings.json` 配置
3. **第三方扩展**：根据具体扩展文档配置

---

## 参考文档

- [GitHub Copilot MCP 官方文档](https://docs.github.com/en/copilot/how-tos/provide-context/use-mcp/extend-copilot-chat-with-mcp)
- [MCP 协议规范](https://modelcontextprotocol.io/)
