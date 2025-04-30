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

# Or if installed as a package
hunyuan-image-mcp

# Or use the MCP CLI
mcp run mcp_image_server.py
```

### Connecting to the Server

You can connect from any MCP-compatible client. The server provides the following features:

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

#### Using UV Environment (Recommended)

**Windows:**
1. Get the Python interpreter path:
   ```
   echo %cd%\.venv\Scripts\python.exe
   ```
2. Get the script path:
   ```
   echo %cd%\mcp_image_server.py
   ```
3. In Cursor, enter the full command:
   ```
   D:\path\to\image-gen-mcp-server\.venv\Scripts\python.exe D:\path\to\image-gen-mcp-server\mcp_image_server.py
   ```

**macOS/Linux:**
1. Get the Python interpreter path:
   ```
   echo $(pwd)/.venv/bin/python
   ```
2. Get the script path:
   ```
   echo $(pwd)/mcp_image_server.py
   ```
3. In Cursor, enter the full command:
   ```
   /path/to/image-gen-mcp-server/.venv/bin/python /path/to/image-gen-mcp-server/mcp_image_server.py
   ```

#### Using System Python

**Windows:**
1. Get Python path:
   ```
   where python
   ```
2. In Cursor, enter:
   ```
   C:\Users\YourName\AppData\Local\Programs\Python\Python39\python.exe D:\path\to\image-gen-mcp-server\mcp_image_server.py
   ```

**macOS/Linux:**
1. Get Python path:
   ```
   which python3
   ```
2. In Cursor, enter:
   ```
   /usr/bin/python3 /path/to/image-gen-mcp-server/mcp_image_server.py
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
4. If everything is set up, the AI will use your MCP server to generate the image

**Note:** The first time you use it, Cursor may ask for permission to use this MCP server.

#### Image generated in Cursor by MCP and saved
![Mountain Landscape](https://wechat-img-1317551199.cos.ap-shanghai.myqcloud.com/github/mh_eng.png)

![Generated Mountain Image](https://wechat-img-1317551199.cos.ap-shanghai.myqcloud.com/github/img_1746021141.jpg)

You can also ask Cursor to design images for your website. Cursor can use the MCP tool to generate images that match your requirements for specific layouts.

![Before Design](https://wechat-img-1317551199.cos.ap-shanghai.myqcloud.com/github/before_design.png)

![After Design](https://wechat-img-1317551199.cos.ap-shanghai.myqcloud.com/github/after_design.png)



#### Troubleshooting
- Ensure environment variables are set correctly
- Check for spaces in paths; use quotes if needed
- Ensure the virtual environment is activated (if using one)
- Try running the server script directly to check for errors
- Check UV environment with `uv --version`

### Examples

Using the `generate_image` tool:

```python
result = await generate_image(
    prompt="A beautiful mountain landscape with a lake and trees",
    style="xieshi",  # Realistic style
    resolution="1792:1024",  # 16:9 landscape
    negative_prompt="blurry, low quality"
)
```


## Front-end Demo

For a front-end integration example, see [`web-design-demo/`](web-design-demo/).

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

- This project has been verified to work with the Cursor IDE MCP integration.
- Future plans include supporting more IDEs and development environments compatible with the Model Context Protocol (MCP). 