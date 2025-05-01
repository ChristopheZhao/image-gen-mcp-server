# MCP Image Generation Server

A Model Context Protocol (MCP) server for image generation using Tencent Hunyuan API.

## Features

- Generate images from text descriptions
- Support for multiple image styles
- Support for different image resolutions
- Negative prompts for excluding unwanted elements

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

Create a `.env` file in the project root with the following content:
```
TENCENT_SECRET_ID=your_tencent_secret_id
TENCENT_SECRET_KEY=your_tencent_secret_key
```

## Usage

### Running the MCP Server

You can run the MCP server as follows:

```bash
# Directly run the script
python mcp_image_server.py

```

### Connecting to the Server

You can connect from MCP-compatible client(recommand cursor now). The server provides the following features:

#### Resources
- `styles://list` - List all available image styles
- `resolutions://list` - List all available image resolutions

#### Tools
- `generate_image` - Generate images based on prompt, style, and resolution

#### Prompts
- `image_generation_prompt` - Create image generation prompt templates

### Cursor Integration

To add this MCP server in Cursor:

1. Open Cursor
2. Go to Settings > Features > MCP
3. Click "+ Add New MCP Server"
4. Fill in the configuration:
   - **Name**: `Image Generator` (or any descriptive name)
   - **Type**: `stdio`
   - **Command**: Full command, must include the absolute path to Python and the script

mcp.json format:
```json
{
  "mcpServers": {
    "image-generation": {
      "name": "image-generation service",
      "description": "support the image generation service using tencent hunyuan API",
      "type": "stdio",
      "command": "D:\\your_path\\image-gen-mcp-server\\.venv\\Scripts\\python.exe",
      "args": ["D:\\your_path\\image-gen-mcp-server\\mcp_image_server.py"],
      "environment": ["TENCENT_SECRET_ID", "TENCENT_SECRET_KEY","MCP_IMAGE_SAVE_DIR"],
      "autoRestart": true,
      "startupTimeoutMs": 30000
    }
  }
} 
```

#### Environment Variables

When configuring the MCP server in Cursor, set the following environment variables:
- `TENCENT_SECRET_ID`: Your Tencent Cloud API Secret ID
- `TENCENT_SECRET_KEY`: Your Tencent Cloud API Secret Key
- `MCP_IMAGE_SAVE_DIR`: Yur save image dir,e.g.: D:\data\mcp_img

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



#### Troubleshooting
- Ensure environment variables are set correctly
- Check for spaces in paths; use quotes if needed
- Ensure the virtual environment is activated (if using one)
- Try running the server script directly to check for errors
- Check UV environment with `uv --version`

## Front-end Demo

For a front-end integration example, see [`web-design-demo/`](web-design-demo/).
This example demonstrates how to develop a real project using Cursor IDE, where you can generate and manage images directly within your development environment using our MCP tool 🛠️. No need to switch between different image generation tools or leave your IDE - everything can be done right in your development workflow ✨.

- screenshot of the demo web
![web demo screenshot](https://wechat-img-1317551199.cos.ap-shanghai.myqcloud.com/github/webdemo.png)


## API Reference

### Tencent Hunyuan Image Generation API

The project currently uses Tencent Hunyuan Image Generation API. Here are the key details:

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


## License

[MIT License](LICENSE)

## RoadMap

- **Current Version**
  - Only supports Tencent Hunyuan image generation API

- **Future Plans**
  - Support more mainstream text-to-image model APIs, including:
    - OpenAI GPT-4o / gpt-image-1
    - Alibaba Tongyi Wanxiang
    - Baidu ERNIE-ViLG
  - Select backend model via environment variable for flexible switching and extension

> Community contributions for more model integrations and new features are welcome!


## Compatibility

- This project has been verified to work with the Cursor and Windsurf IDE MCP integration.
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


