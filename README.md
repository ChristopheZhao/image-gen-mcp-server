# MCP Image Generation Server

A Model Context Protocol (MCP) server for image generation using multiple AI providers including Tencent Hunyuan, OpenAI DALL-E 3, and Doubao APIs.

**Version**: 0.2.0

## Features

### 🎯 Multi-API Provider Support
- **Tencent Hunyuan**: 18 artistic styles with Chinese optimization
- **OpenAI DALL-E 3**: High-quality image generation with English optimization
- **Doubao (ByteDance)**: Balanced quality and speed with 12 styles

### 🚀 Core Features
- Generate images from text descriptions
- Support for multiple image styles across different providers
- Support for different image resolutions
- Negative prompts for excluding unwanted elements
- Intelligent provider selection and management
- Unified parameter format with provider-specific options

### 🌐 Transport Modes (New in v0.2.0)
- **stdio Transport**: Local IDE integration (Cursor, Windsurf)
- **HTTP Transport**: Remote access and enterprise deployment
  - Multi-client concurrent connections
  - Bearer Token authentication
  - Session management
  - RESTful API endpoints
  - Suitable for cloud deployment and remote access

> **Why HTTP Transport?**
> Version 0.2.0 adds **Streamable HTTP** support (MCP's official standard as of 2024-11-05) to enable:
> - **Remote Access**: Claude remote MCP requires public HTTP endpoints (stdio only works locally)
> - **Enterprise Deployment**: Centralized service deployment with multiple concurrent clients
> - **Cloud Native**: Compatible with containers, Kubernetes, and load balancers
>
> Note: This uses **Streamable HTTP** (POST/GET/DELETE), not the deprecated SSE-only approach. SSE is retained for compatibility but Streamable HTTP is the recommended standard.

### 🔧 Smart Provider Management
- Automatic detection of available API providers
- Support for specifying particular providers or automatic selection
- Unified error handling and retry mechanisms
- Flexible parameter formats: `provider:style` and `provider:resolution`

## Installation

### Using UV (Recommended)

UV is a fast, modern Python package manager. Recommended usage:

```bash
# Install UV (Windows)
curl -sSf https://astral.sh/uv/install.ps1 | powershell

# Install UV (macOS/Linux)
curl -sSf https://astral.sh/uv/install.sh | bash

# Clone the project and enter the directory
cd path/to/image-gen-mcp-server

# Create a UV virtual environment
uv venv
# Or specify an environment name
# uv venv my-env-name

# Activate the virtual environment (Windows)
.venv\Scripts\activate
# Activate the virtual environment (macOS/Linux)
source .venv/bin/activate

# Install dependencies (recommended)
uv pip install -e .

# Or use the lock file for exact versions
uv pip install -r requirements.lock.txt
```

### Using Traditional pip

If you prefer traditional pip:

```bash
# Create a virtual environment
python -m venv venv
# Activate the virtual environment (Windows)
venv\Scripts\activate
# Activate the virtual environment (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -e .
# Or use the lock file
pip install -r requirements.lock.txt
```

### Environment Setup

Create a `.env` file in the project root. See `.env.example` for all available options.

#### Basic Configuration
```bash
# Image save directory
MCP_IMAGE_SAVE_DIR=./generated_images
# Public base URL for generated image links (HTTP mode, optional but recommended)
# MCP_PUBLIC_BASE_URL=https://mcp.your-domain.com
# Metadata TTL for get_image_data cache (seconds)
# MCP_IMAGE_RECORD_TTL=86400
# Max bytes allowed in get_image_data base64 response
# MCP_GET_IMAGE_DATA_MAX_BYTES=10485760

# API Provider Credentials (configure at least one)
TENCENT_SECRET_ID=your_tencent_secret_id
TENCENT_SECRET_KEY=your_tencent_secret_key
OPENAI_API_KEY=your_openai_api_key
DOUBAO_ACCESS_KEY=your_doubao_access_key
DOUBAO_SECRET_KEY=your_doubao_secret_key
```

#### Transport Configuration (Optional)
```bash
# Transport mode: stdio (default, for local IDE) or http (for remote access)
MCP_TRANSPORT=stdio

# HTTP transport settings (only needed for HTTP mode)
MCP_HOST=127.0.0.1
MCP_PORT=8000

# Authentication (recommended for HTTP mode)
MCP_AUTH_TOKEN=your-secure-random-token
```

## Usage

### 🔄 Transport Modes

This server supports two transport modes:

| Feature | stdio Transport | HTTP Transport |
|---------|----------------|----------------|
| **Use Case** | Local IDE integration | Remote access, enterprise deployment |
| **Connection** | Subprocess communication | HTTP/HTTPS network |
| **Multi-client** | ❌ Single client | ✅ Multiple concurrent clients |
| **Remote Access** | ❌ Not supported | ✅ Supported |
| **Authentication** | Not needed | Bearer Token |
| **Deployment** | Simple | Cloud-ready |

### 🚀 Quick Start

#### Unified Entry Point (Recommended)
```bash
# Method 1: Run as module (recommended)
python -m mcp_image_server

# Method 2: Use entry script
./mcp-server

# Method 3: After pip install
mcp-image-server
```

The unified server will automatically use the transport mode specified in your `.env` file:
- `MCP_TRANSPORT=stdio` → Local stdio mode for IDE integration
- `MCP_TRANSPORT=http` → HTTP server mode for remote access

#### Legacy Examples
```bash
# Legacy examples moved to examples/ directory
python examples/legacy_single_api_server.py
```

### 📡 HTTP Transport Mode

For remote access and enterprise deployment, use HTTP transport:

#### 1. Configure HTTP Mode
```bash
# Set in .env file
MCP_TRANSPORT=http
MCP_HOST=127.0.0.1
MCP_PORT=8000
MCP_AUTH_TOKEN=your-secure-token  # Optional but recommended
```

#### 2. Start HTTP Server
```bash
python -m mcp_image_server
```

Server will start on `http://127.0.0.1:8000` with endpoints:
- `GET /health` - Health check
- `POST /mcp/v1/messages` - Send JSON-RPC messages
- `GET /mcp/v1/messages` - Subscribe to SSE events
- `DELETE /mcp/v1/messages` - Close session
- `GET /images/{filename}` - Serve generated image files

`generate_image` tool returns `images[].url` for HTTP clients.  
If server is exposed through reverse proxy/public domain, set `MCP_PUBLIC_BASE_URL` to ensure URL is externally reachable.
`/images/*` is intentionally public so browser/front-end image rendering works even when MCP API auth is enabled.

Best-practice agent flow:
1. Call `generate_image` to get renderable image + stable `image_id`/`url`.
2. Call `get_image_data(image_id=...)` only when programmable base64 text is required.

#### 3. Test HTTP Server
```bash
# Check server health
curl http://127.0.0.1:8000/health

# Run comprehensive tests
python test_mcp_server.py

# Test with API key for actual image generation
python test_mcp_server.py --with-api
```

#### 4. Use HTTP Client
```bash
# Run example client
python example_http_client.py basic       # Explore server capabilities
python example_http_client.py generate    # Generate images (requires API key)
```

For detailed HTTP transport documentation, see **[HTTP_TRANSPORT_GUIDE.md](HTTP_TRANSPORT_GUIDE.md)**

Screenshot of MCP server running successfully:

![MCP Server Running](https://wechat-img-1317551199.cos.ap-shanghai.myqcloud.com/github/mcp_server_runsuc.png)

### Connecting to the Server

You can connect from MCP-compatible client(recommand cursor now). The server provides the following features:

#### Resources
- `styles://list` - List all available image styles
- `resolutions://list` - List all available image resolutions

#### Tools
- `generate_image` - Generate images based on prompt, style, and resolution
- `get_image_data` - Fetch base64 text for a previously generated image by `image_id`

#### Prompts
- `image_generation_prompt` - Create image generation prompt templates

### 🎨 Multi-API Usage Examples

#### Basic Usage
```python
# Auto-select best available provider
generate_image(prompt="A cute cat in a garden")

# Specify a particular provider
generate_image(prompt="A cute cat", provider="openai")
generate_image(prompt="一只可爱的小猫", provider="hunyuan")
generate_image(prompt="Cute kitten", provider="doubao")
```

#### Advanced Parameter Usage
```python
# Use provider-specific styles and resolutions
generate_image(
    prompt="Cyberpunk city skyline", 
    style="hunyuan:saibopengke", 
    resolution="hunyuan:1024:768"
)

# Mix provider selection with standard parameters
generate_image(
    prompt="Fantasy magical forest",
    provider="doubao",
    style="fantasy",
    resolution="1024x768",
    negative_prompt="low quality, blurry"
)

# OpenAI with high-resolution output
generate_image(
    prompt="Artistic portrait of a musician",
    provider="openai",
    style="artistic",
    resolution="1792x1024"
)
```

### 📊 Supported Providers and Parameters

#### Tencent Hunyuan
- **Styles**: 18 options including `riman`, `xieshi`, `shuimo`, `saibopengke`, `youhua`
- **Resolutions**: 8 options from `768:768` to `1280:720`
- **Specialty**: Chinese-optimized, rich artistic styles

#### OpenAI DALL-E 3
- **Styles**: 12 options including `natural`, `vivid`, `realistic`, `artistic`, `anime`
- **Resolutions**: 7 options including ultra-high resolution `1792x1024`
- **Specialty**: High-quality output, English optimization

#### Doubao (ByteDance)
- **Styles**: 12 options including `general`, `anime`, `chinese_painting`, `cyberpunk`
- **Resolutions**: 9 options from `512x512` to `1024x576`
- **Specialty**: Balanced quality and speed

### Cursor Integration

To add this MCP server in Cursor:

1. Open Cursor
2. Go to Settings > Features > MCP
3. Click "+ Add New MCP Server"
4. Fill in the configuration:
   - **Name**: `Multi-API Image Generator` (or any descriptive name)
   - **Type**: `stdio`
   - **Command**: Full command, must include the absolute path to Python and the script

#### Single API Configuration (Original)
```json
{
  "mcpServers": {
    "image-generation": {
      "name": "Multi-API Image Generation Service",
      "description": "Multi-provider image generation using Hunyuan, OpenAI, and Doubao APIs",
      "type": "stdio",
      "command": "D:\\your_path\\image-gen-mcp-server\\.venv\\Scripts\\python.exe",
      "args": ["-m", "mcp_image_server"],
      "environment": ["TENCENT_SECRET_ID", "TENCENT_SECRET_KEY", "OPENAI_API_KEY", "DOUBAO_API_KEY", "MCP_IMAGE_SAVE_DIR"],
      "autoRestart": true,
      "startupTimeoutMs": 30000
    }
  }
}
```

>  📝 **Note:** For detailed VS Code integration guide, see [docs/VSCODE_INTEGRATION.md](docs/VSCODE_INTEGRATION.md)

#### Environment Variables

When configuring the MCP server in Cursor, set the following environment variables:

**For Single API (Hunyuan only)**:
- `TENCENT_SECRET_ID`: Your Tencent Cloud API Secret ID
- `TENCENT_SECRET_KEY`: Your Tencent Cloud API Secret Key
- `MCP_IMAGE_SAVE_DIR`: Your save image dir, e.g.: D:\data\mcp_img

**For Multi-API (All providers)**:
- `TENCENT_SECRET_ID`: Your Tencent Cloud API Secret ID
- `TENCENT_SECRET_KEY`: Your Tencent Cloud API Secret Key
- `OPENAI_API_KEY`: Your OpenAI API Key
- `DOUBAO_ACCESS_KEY`: Your Doubao Access Key
- `DOUBAO_SECRET_KEY`: Your Doubao Secret Key
- `MCP_IMAGE_SAVE_DIR`: Your save image dir, e.g.: D:\data\mcp_img
- `OPENAI_BASE_URL`: (Optional) Custom OpenAI endpoint
- `DOUBAO_ENDPOINT`: (Optional) Custom Doubao endpoint

**Note**: You only need to configure the API keys for the providers you want to use. The system will automatically detect available providers.

### 🎯 Multi-API Usage in Cursor

With the multi-API server, you can use natural language in Cursor to specify different providers:

```
# Auto-select the best provider
"Generate a cyberpunk city image"

# Specify a particular provider
"Use OpenAI to generate a cartoon-style cat image"
"Please use Hunyuan to create a traditional Chinese painting"
"Generate with Doubao a fantasy-style forest scene"

# Use provider-specific styles
"Create an image with hunyuan:shuimo style showing mountains and rivers"
"Generate a doubao:chinese_painting style landscape"

# Mix parameters
"Use OpenAI to generate a 1792x1024 artistic portrait"
"Create a hunyuan:saibopengke style image at 1024:768 resolution"
```

#### Verification

1. Save the configuration
2. Restart Cursor
3. Start a new chat and enter: "Generate a mountain landscape image"
4. If everything is set up correctly, the AI will use your MCP server to generate the image

**Note:** The first time you use it, Cursor may ask for permission to use this MCP server.

Let's look at the steps in Cursor:

- step_1: types your generate command in cursor

  ![Mountain Landscape](https://wechat-img-1317551199.cos.ap-shanghai.myqcloud.com/github/mountain_cursor.png)

- step_2: after your approval it will call the mcp image-gen tool and save it

  ![Mountain Landscape](https://wechat-img-1317551199.cos.ap-shanghai.myqcloud.com/github/mountain_gtips.png)


- Step 3: View or use the image saved in the directory (MCP_IMAGE_SAVE_DIR) you have set in the .env file

  ![Generated Mountain Image](https://wechat-img-1317551199.cos.ap-shanghai.myqcloud.com/github/mountain_curg.jpg)


You can also ask Cursor to design images for your website ✨. Cursor can use the MCP tool to generate images that match your specific layout requirements 🎨. Perfect for creating beautiful web designs! 

Tip: You don't need to manually move the generated images from the save directory to your project directory. Cursor will handle this automatically after your approval. This is one of the main advantages of using Cursor.

- Planning the move 

  ![plan move](https://wechat-img-1317551199.cos.ap-shanghai.myqcloud.com/github/move_img_to_project.png)

- Executing the move

  ![act move](https://wechat-img-1317551199.cos.ap-shanghai.myqcloud.com/github/move_handle.png)

- Example Performance

  Original web design:
  ![Before Design](https://wechat-img-1317551199.cos.ap-shanghai.myqcloud.com/github/before_design.png)

  New design after generating and moving the image to the project using Cursor:
  ![After Design](https://wechat-img-1317551199.cos.ap-shanghai.myqcloud.com/github/after_design.png)


### 🧪 Testing

The project includes comprehensive testing tools:

#### Protocol Tests (No API Key Required)
```bash
# Test MCP protocol functionality without API keys
python test_mcp_server.py
```

This tests:
- ✅ Health check endpoint
- ✅ MCP initialization handshake
- ✅ Tools listing
- ✅ Resources listing and reading
- ✅ Prompts listing
- ✅ Session management

#### Functional Tests (API Key Required)
```bash
# Test actual image generation with configured providers
python test_mcp_server.py --with-api
```

This additionally tests:
- ✅ Real image generation with OpenAI
- ✅ Real image generation with Hunyuan
- ✅ Real image generation with Doubao

**Note**: At least one API key must be configured in `.env` to run functional tests.

### Troubleshooting

#### General Issues
- Ensure environment variables are set correctly
- Check for spaces in paths; use quotes if needed
- Ensure the virtual environment is activated (if using one)
- Try running the server script directly to check for errors
- Check UV environment with `uv --version`

#### HTTP Transport Issues
- **Connection refused**: Ensure server is running on correct host/port
- **401 Unauthorized**: Check `MCP_AUTH_TOKEN` configuration
- **404 Session not found**: Re-initialize connection to get new session ID
- **No provider available**: Configure at least one API provider in `.env`

For detailed troubleshooting, see **[HTTP_TRANSPORT_GUIDE.md](HTTP_TRANSPORT_GUIDE.md#故障排查)**

## Front-end Demo

For a front-end integration example, see [`web-design-demo/`](web-design-demo/).
This example demonstrates how to develop a real project using Cursor IDE, where you can generate and manage images directly within your development environment using our MCP tool 🛠️. No need to switch between different image generation tools or leave your IDE - everything can be done right in your development workflow ✨.

- screenshot of the demo web
![web demo screenshot](https://wechat-img-1317551199.cos.ap-shanghai.myqcloud.com/github/webdemo.png)


## API Reference

### Multi-API Architecture

The project now supports multiple image generation APIs through a unified interface:

#### Supported APIs
1. **Tencent Hunyuan Image Generation API** (Original)
2. **OpenAI DALL-E 3 API** (New)
3. **Doubao Image Generation API** (New)

#### Unified MCP Resources
- `providers://list` - List all available providers
- `styles://list` - List all styles from all providers
- `resolutions://list` - List all resolutions from all providers
- `styles://provider/{provider_name}` - Get styles for specific provider
- `resolutions://provider/{provider_name}` - Get resolutions for specific provider

#### Enhanced MCP Tools
- `generate_image` - Multi-provider image generation with intelligent routing

### Tencent Hunyuan Image Generation API

The project originally used and continues to support Tencent Hunyuan Image Generation API. Here are the key details:

#### API Endpoints
- Domain: `hunyuan.tencentcloudapi.com`
- Region: `ap-guangzhou` (Currently only supports Guangzhou region)
- Default API Rate Limit: 20 requests/second
- Concurrent Tasks: Default 1 task at a time

#### Task Flow
1. Submit Task: Submit an asynchronous image generation task with text description
2. Query Task: Get task status and results using task ID
3. Result URL: Generated image URLs are valid for 1 hour
  
For detailed API documentation and pricing, please refer to:
- [API Documentation](https://cloud.tencent.com/document/api/1729/105970)
- [Pricing Details](https://cloud.tencent.com/document/product/1729/105925) 

### OpenAI DALL-E 3 API

#### API Features
- High-quality image generation
- Automatic prompt optimization
- Multiple style options
- High-resolution output support

### Doubao API (ByteDance)

#### API Features
- ByteDance's proprietary image generation model
- Balanced quality and speed
- Chinese and English prompt support
- Multiple artistic styles

## RoadMap

- **Version 0.2.0** (Current)
  - ✅ Tencent Hunyuan image generation API
  - ✅ OpenAI DALL-E 3 API integration
  - ✅ Doubao API integration
  - ✅ Multi-provider management system
  - ✅ Intelligent provider selection
  - ✅ Unified parameter interface
  - ✅ HTTP transport with Streamable HTTP protocol
  - ✅ Remote access support
  - ✅ Multi-client concurrent connections
  - ✅ Bearer Token authentication
  - ✅ Session management
  - ✅ Comprehensive testing suite

- **Future Plans**
  - Support more mainstream text-to-image model APIs, including:
    - Alibaba Tongyi Wanxiang
    - Baidu ERNIE-ViLG
    - Stable Diffusion API
  - Advanced features:
    - Image editing and modification
    - Batch image generation
    - Style transfer capabilities
    - Custom model fine-tuning support
  - Enhanced MCP integration:
    - Real-time generation progress
    - Image history and management
    - Advanced prompt templates

> Community contributions for more model integrations and new features are welcome!

## Compatibility

- **Local IDE Integration (stdio)**: Verified to work with Cursor and Windsurf IDE
- **Remote Access (HTTP)**: Compatible with any MCP client supporting HTTP transport
- **Claude Remote MCP**: HTTP transport enables connection to Claude with public HTTP endpoint

  - windsurf is also supported to integrated now

    - screenshot of mcp tool call in windsurf

    - ![windsurf run interface](https://wechat-img-1317551199.cos.ap-shanghai.myqcloud.com/github/windsurf_inte.png)

    - and the result as follows

    - ![windsurf call result](https://wechat-img-1317551199.cos.ap-shanghai.myqcloud.com/github/img_1746070231.jpg)

- Future plans include supporting more IDEs and development environments compatible with the Model Context Protocol (MCP).

## Acknowledgments

This project is built with [FastMCP](https://github.com/jlowin/fastmcp) as the core framework, a powerful implementation of the Model Context Protocol. The MCP integration is based on:
- [FastMCP](https://github.com/jlowin/fastmcp): A fast, Pythonic way to build MCP servers
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk): The official Python SDK for Model Context Protocol

We also use these excellent open-source projects:
- [UV](https://github.com/astral-sh/uv): A fast Python package installer and resolver
- [Python-dotenv](https://github.com/theskumar/python-dotenv): Reads key-value pairs from .env file
- [Tencentcloud-sdk-python](https://github.com/TencentCloud/tencentcloud-sdk-python): Official Tencent Cloud SDK for Python

## Contributing

We welcome contributions of all kinds! Here are some ways you can help:

- 🐛 Report bugs and issues
- 💡 Suggest new features or improvements
- 🔧 Submit pull requests
- 🎨 Add support for more image generation models

### Getting Started with Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'feat: add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

Please make sure to update tests as appropriate and follow the existing coding style.

> We appreciate your interest in making this project better!
