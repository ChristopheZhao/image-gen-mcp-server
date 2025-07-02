# MCP 图像生成服务

一个基于 Model Context Protocol (MCP) 的图像生成服务，支持多个主流AI提供商，包括腾讯混元、OpenAI DALL-E 3 和豆包 API。

## 特性

### 🎯 多API提供商支持
- **腾讯混元**: 18种艺术风格，中文优化
- **OpenAI DALL-E 3**: 高质量图像生成，英文优化
- **豆包（字节跳动）**: 平衡的质量和速度，12种风格

### 🚀 核心功能
- 支持根据文本描述生成图片
- 支持跨不同提供商的多种图像风格
- 支持不同分辨率
- 支持负面提示词（排除不想要的元素）
- 智能提供商选择和管理
- 统一参数格式，支持提供商特定选项

### 🔧 智能提供商管理
- 自动检测可用的API提供商
- 支持指定特定提供商或自动选择
- 统一的错误处理和重试机制
- 灵活的参数格式：`provider:style` 和 `provider:resolution`

## 安装

### 推荐使用 UV

UV 是一个快速、现代的 Python 包管理器，推荐如下用法：

```bash
# 安装 UV（Windows）
curl -sSf https://astral.sh/uv/install.ps1 | powershell

# 安装 UV（macOS/Linux）
curl -sSf https://astral.sh/uv/install.sh | bash

# 克隆项目并进入目录
cd path/to/image-gen-mcp-server

# 创建 UV 虚拟环境
uv venv
# 或指定环境名
# uv venv my-env-name

# 激活虚拟环境（Windows）
.venv\Scripts\activate
# 激活虚拟环境（macOS/Linux）
source .venv/bin/activate

# 安装依赖（推荐）
uv pip install -e .

# 或使用锁定文件安装精确版本
uv pip install -r requirements.lock.txt
```

### 传统 pip 安装

```bash
# 创建虚拟环境
python -m venv venv
# 激活虚拟环境（Windows）
venv\Scripts\activate
# 激活虚拟环境（macOS/Linux）
source venv/bin/activate

# 安装依赖
pip install -e .
# 或使用锁定文件
pip install -r requirements.lock.txt
```

### 环境变量配置

在项目根目录下创建 `.env` 文件，内容如下：
```
TENCENT_SECRET_ID=你的腾讯云SecretId
TENCENT_SECRET_KEY=你的腾讯云SecretKey
MCP_IMAGE_SAVE_DIR=你的保存生成图片的位置
```

## 用法

### 🔄 选择服务器版本

本项目提供两种服务器实现：

#### 单API服务器（原版）
```bash
# 仅支持腾讯混元API
python mcp_image_server.py
```

#### 多API服务器（新版 - 推荐）
```bash
# 支持腾讯混元、OpenAI DALL-E 3 和豆包 API
python mcp_image_server_multi.py
```

**推荐**：使用多API服务器（`mcp_image_server_multi.py`）以获得所有支持的提供商和增强功能。

### 启动 MCP 服务

```bash
# 多API服务器（推荐）
python mcp_image_server_multi.py

# 或原版单API服务器
python mcp_image_server.py
```

MCP 服务器成功运行截图：

![MCP 服务器运行](https://wechat-img-1317551199.cos.ap-shanghai.myqcloud.com/github/mcp_server_runsuc.png)


### 连接到服务

你可以用任何兼容 MCP 协议的客户端连接本服务。服务端提供如下功能：

#### 资源
- `styles://list` - 获取所有可用图像风格
- `resolutions://list` - 获取所有可用分辨率

#### 工具
- `generate_image` - 根据提示词、风格、分辨率生成图片

#### 提示模板
- `image_generation_prompt` - 生成图片请求的标准提示模板

### 🎨 多API使用示例

#### 基础用法
```python
# 自动选择最佳可用提供商
generate_image(prompt="花园里的可爱小猫")

# 指定特定提供商
generate_image(prompt="A cute cat", provider="openai")
generate_image(prompt="一只可爱的小猫", provider="hunyuan")
generate_image(prompt="Cute kitten", provider="doubao")
```

#### 高级参数用法
```python
# 使用提供商特定的风格和分辨率
generate_image(
    prompt="赛博朋克城市天际线", 
    style="hunyuan:saibopengke", 
    resolution="hunyuan:1024:768"
)

# 混合提供商选择与标准参数
generate_image(
    prompt="奇幻魔法森林",
    provider="doubao",
    style="fantasy",
    resolution="1024x768",
    negative_prompt="低质量，模糊"
)

# OpenAI高分辨率输出
generate_image(
    prompt="音乐家的艺术肖像",
    provider="openai",
    style="artistic",
    resolution="1792x1024"
)
```

### 📊 支持的提供商和参数

#### 腾讯混元
- **风格**: 18种选项，包括 `riman`、`xieshi`、`shuimo`、`saibopengke`、`youhua`
- **分辨率**: 8种选项，从 `768:768` 到 `1280:720`
- **特色**: 中文优化，丰富的艺术风格

#### OpenAI DALL-E 3
- **风格**: 12种选项，包括 `natural`、`vivid`、`realistic`、`artistic`、`anime`
- **分辨率**: 7种选项，包括超高分辨率 `1792x1024`
- **特色**: 高质量输出，英文优化

#### 豆包（字节跳动）
- **风格**: 12种选项，包括 `general`、`anime`、`chinese_painting`、`cyberpunk`
- **分辨率**: 9种选项，从 `512x512` 到 `1024x576`
- **特色**: 平衡的质量和速度

### Cursor 集成

1. 打开 Cursor
2. 进入 Settings > Features > MCP
3. 点击"+ Add New MCP Server"
4. 填写配置：
   - **Name**: `多API图像生成服务`（或自定义）
   - **Type**: `stdio`
   - **Command**: Python 解释器和脚本的绝对路径

#### 单API配置（原版）
```json
{
  "mcpServers": {
    "image-generation": {
      "name": "图像生成服务",
      "description": "使用腾讯混元API的图像生成服务",
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

#### 多API配置（推荐）
```json
{
  "mcpServers": {
    "multi-image-generation": {
      "name": "多API图像生成服务",
      "description": "使用混元、OpenAI和豆包API的多提供商图像生成服务",
      "type": "stdio",
      "command": "D:\\your_path\\image-gen-mcp-server\\.venv\\Scripts\\python.exe",
      "args": ["D:\\your_path\\image-gen-mcp-server\\mcp_image_server_multi.py"],
      "environment": [
        "TENCENT_SECRET_ID", 
        "TENCENT_SECRET_KEY",
        "OPENAI_API_KEY",
        "DOUBAO_ACCESS_KEY",
        "DOUBAO_SECRET_KEY",
        "MCP_IMAGE_SAVE_DIR"
      ],
      "autoRestart": true,
      "startupTimeoutMs": 30000
    }
  }
}
```

#### 环境变量

在 Cursor 配置 MCP server 时，设置以下环境变量：

**单API配置（仅混元）**:
- `TENCENT_SECRET_ID`: 你的腾讯云 API Secret ID
- `TENCENT_SECRET_KEY`: 你的腾讯云 API Secret Key
- `MCP_IMAGE_SAVE_DIR`: 图片保存的位置，例如: D:\data\mcp_img

**多API配置（所有提供商）**:
- `TENCENT_SECRET_ID`: 你的腾讯云 API Secret ID
- `TENCENT_SECRET_KEY`: 你的腾讯云 API Secret Key
- `OPENAI_API_KEY`: 你的 OpenAI API 密钥
- `DOUBAO_ACCESS_KEY`: 你的豆包 Access Key
- `DOUBAO_SECRET_KEY`: 你的豆包 Secret Key
- `MCP_IMAGE_SAVE_DIR`: 图片保存的位置，例如: D:\data\mcp_img
- `OPENAI_BASE_URL`: （可选）自定义 OpenAI 端点
- `DOUBAO_ENDPOINT`: （可选）自定义豆包端点

**注意**: 你只需要配置想要使用的提供商的API密钥。系统会自动检测可用的提供商。

### 🎯 在Cursor中使用多API

使用多API服务器时，你可以在Cursor中用自然语言指定不同的提供商：

```
# 自动选择最佳提供商
"生成一张赛博朋克城市图片"

# 指定特定提供商
"使用OpenAI生成一张卡通风格的猫咪图片"
"请用混元创建一幅传统中国画"
"用豆包生成一张奇幻风格的森林场景"

# 使用提供商特定风格
"创建一张hunyuan:shuimo风格的山水画"
"生成一张doubao:chinese_painting风格的风景画"

# 混合参数使用
"使用OpenAI生成1792x1024分辨率的艺术肖像"
"创建一张hunyuan:saibopengke风格的1024:768分辨率图片"
```

#### 验证

1. 保存配置
2. 重启 Cursor
3. 新建对话，输入"生成一张山水风景图"
4. 若配置无误，AI 会调用 MCP 服务生成图片并返回URL

**注意**：首次使用时，Cursor 可能会请求你批准使用该 MCP server。

让我们看看在 Cursor 中的具体步骤：

1. 在 Cursor 中输入生成命令：

   ![山景图](https://wechat-img-1317551199.cos.ap-shanghai.myqcloud.com/github/mountain_cursor.png)

2. 在你批准后，它会调用 MCP 图像生成工具并保存：

   ![生成的山景图](https://wechat-img-1317551199.cos.ap-shanghai.myqcloud.com/github/mountain_gtips.png)

3. 查看或使用保存在指定目录（MCP_IMAGE_SAVE_DIR）中的图片：

   ![生成的山景图](https://wechat-img-1317551199.cos.ap-shanghai.myqcloud.com/github/mountain_curg.jpg)

你也可以让 Cursor 为你的网站设计图片 ✨。Cursor 可以使用 MCP 工具根据特定布局要求生成匹配的图片 🎨。

提示：你无需手动将生成的图片从保存目录移动到项目目录。Cursor 会在得到你的批准后自动处理这个过程。这是使用 Cursor 的主要优势之一。

- 计划移动图片

  ![计划移动](https://wechat-img-1317551199.cos.ap-shanghai.myqcloud.com/github/move_img_to_project.png)

- 执行移动

  ![执行移动](https://wechat-img-1317551199.cos.ap-shanghai.myqcloud.com/github/move_handle.png)

- 效果展示

  原始网页设计：
  ![设计前](https://wechat-img-1317551199.cos.ap-shanghai.myqcloud.com/github/before_design.png)

  使用 Cursor 生成并移动图片后的新设计：
  ![设计后](https://wechat-img-1317551199.cos.ap-shanghai.myqcloud.com/github/after_design.png)


#### 常见问题排查
- 检查环境变量是否正确
- 路径有空格时请加引号
- 确认虚拟环境已激活
- 可直接运行服务端脚本排查报错
- 检查 UV 环境 `uv --version`

## API 参考

### 多API架构

项目现在通过统一接口支持多个图像生成API：

#### 支持的API
1. **腾讯混元图像生成API**（原版）
2. **OpenAI DALL-E 3 API**（新增）
3. **豆包图像生成API**（新增）

#### 统一MCP资源
- `providers://list` - 列出所有可用提供商
- `styles://list` - 列出所有提供商的风格
- `resolutions://list` - 列出所有提供商的分辨率
- `styles://provider/{provider_name}` - 获取特定提供商的风格
- `resolutions://provider/{provider_name}` - 获取特定提供商的分辨率

#### 增强的MCP工具
- `generate_image` - 具有智能路由的多提供商图像生成

### 腾讯混元生图 API

项目最初使用并继续支持腾讯混元生图 API，以下是主要信息：

#### API 接入点
- 域名：`hunyuan.tencentcloudapi.com`
- 地域：`ap-guangzhou`（目前仅支持广州地域）
- 默认接口请求频率限制：20次/秒
- 并发任务数：默认支持1个并发任务

#### 任务流程
1. 提交任务：提交包含文本描述的异步图像生成任务
2. 查询任务：使用任务 ID 获取任务状态和结果
3. 结果 URL：生成的图片 URL 有效期为1小时

详细信息请参考：
- [API 文档](https://cloud.tencent.com/document/api/1729/105970)
- [计费说明](https://cloud.tencent.com/document/product/1729/105925)

### OpenAI DALL-E 3 API

#### API特性
- 高质量图像生成
- 自动提示词优化
- 多种风格选项
- 高分辨率输出支持

### 豆包API（字节跳动）

#### API特性
- 字节跳动自研图像生成模型
- 平衡的质量和速度
- 中英文提示词支持
- 多种艺术风格

## RoadMap

- **当前版本**
  - ✅ 腾讯混元图像生成API
  - ✅ OpenAI DALL-E 3 API集成
  - ✅ 豆包API集成
  - ✅ 多提供商管理系统
  - ✅ 智能提供商选择
  - ✅ 统一参数接口

- **未来计划**
  - 支持更多主流文生图模型 API，包括：
    - 阿里通义万相
    - 百度文心一格（ERNIE-ViLG）
    - Stable Diffusion API
  - 高级功能：
    - 图像编辑和修改
    - 批量图像生成
    - 风格转换功能
    - 自定义模型微调支持
  - 增强MCP集成：
    - 实时生成进度
    - 图像历史和管理
    - 高级提示模板

> 欢迎社区贡献更多模型集成和新功能！

## 前端演示

查看前端集成示例请访问 [`web-design-demo/`](web-design-demo/)。
这个示例展示了如何使用 Cursor IDE 开发实际项目，您可以直接在开发环境中使用我们的 MCP 工具生成和管理图片 🛠️。无需在不同的图片生成工具之间切换或离开 IDE - 所有操作都可以在您的开发工作流程中完成 ✨。

- 演示网站截图
![网站演示截图](https://wechat-img-1317551199.cos.ap-shanghai.myqcloud.com/github/webdemo.png)

## 许可证

[MIT License](LICENSE)

## 兼容性

- 本项目已在 Cursor 和 Windsurf IDE 的 MCP 集成环境下验证可用。

  - Windsurf IDE 现已支持集成

    - Windsurf 中调用 MCP 工具的截图

    ![Windsurf 运行界面](https://wechat-img-1317551199.cos.ap-shanghai.myqcloud.com/github/windsurf_inte.png)

    - 生成结果如下

    ![Windsurf 调用结果](https://wechat-img-1317551199.cos.ap-shanghai.myqcloud.com/github/img_1746070231.jpg)

- 未来计划支持更多兼容 MCP 协议的 IDE 和开发环境。

## 致谢

本项目以 [FastMCP](https://github.com/jlowin/fastmcp) 作为核心框架构建，这是一个强大的 Model Context Protocol 实现。MCP 集成基于：
- [FastMCP](https://github.com/jlowin/fastmcp)：一个快速、Pythonic 的 MCP 服务器构建框架
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)：Model Context Protocol 的官方 Python SDK

我们同时使用了以下优秀的开源项目：
- [UV](https://github.com/astral-sh/uv)：快速的 Python 包安装和解析工具
- [Python-dotenv](https://github.com/theskumar/python-dotenv)：用于读取 .env 文件的键值对
- [Tencentcloud-sdk-python](https://github.com/TencentCloud/tencentcloud-sdk-python)：腾讯云官方 Python SDK

## 参与贡献

我们欢迎各种形式的贡献！以下是您可以帮助的方式：

- 🐛 报告 bug 和问题
- 💡 提出新功能或改进建议
- 🔧 提交代码改进
- 🎨 添加更多图像生成模型支持

### 如何开始贡献

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

请确保适当更新测试，并遵循现有的代码风格。

> 感谢您对改进这个项目的关注！

