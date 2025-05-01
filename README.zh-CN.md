# MCP 图像生成服务

一个基于 Model Context Protocol (MCP) 的图像生成服务，当前支持腾讯混元 API，未来将支持更多主流文生图模型。

## 特性

- 支持根据文本描述生成图片
- 支持多种图像风格
- 支持不同分辨率
- 支持负面提示词（排除不想要的元素）

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
```

## 用法

### 启动 MCP 服务

```bash
# 直接运行脚本
python mcp_image_server.py
```

### 连接到服务

你可以用任何兼容 MCP 协议的客户端连接本服务。服务端提供如下功能：

#### 资源
- `styles://list` - 获取所有可用图像风格
- `resolutions://list` - 获取所有可用分辨率

#### 工具
- `generate_image` - 根据提示词、风格、分辨率生成图片

#### 提示模板
- `image_generation_prompt` - 生成图片请求的标准提示模板

### Cursor 集成

1. 打开 Cursor
2. 进入 Settings > Features > MCP
3. 点击"+ Add New MCP Server"
4. 填写配置：
   - **Name**: `图像生成服务`（或自定义）
   - **Type**: `stdio`
   - **Command**: Python 解释器和脚本的绝对路径


#### 环境变量

在 Cursor 配置 MCP server 时，设置以下环境变量：
- `TENCENT_SECRET_ID`: 你的腾讯云 API Secret ID
- `TENCENT_SECRET_KEY`: 你的腾讯云 API Secret Key
- `MCP_IMAGE_SAVE_DIR`: 图片保存的位置,例如: D:\data\mcp_img

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





## 前端演示

查看前端集成示例请访问 [`web-design-demo/`](web-design-demo/)。
这个示例展示了如何使用 Cursor IDE 开发实际项目，您可以直接在开发环境中使用我们的 MCP 工具生成和管理图片 🛠️。无需在不同的图片生成工具之间切换或离开 IDE - 所有操作都可以在您的开发工作流程中完成 ✨。

- 演示网站截图
![网站演示截图](https://wechat-img-1317551199.cos.ap-shanghai.myqcloud.com/github/webdemo.png)

## 许可证

[MIT License](LICENSE)

## 路线图（RoadMap）

- **当前版本**
  - 仅支持腾讯混元（Hunyuan）图像生成 API

- **未来计划**
  - 支持更多主流文生图模型 API，包括：
    - OpenAI GPT-4o / gpt-image-1
    - 阿里通义万相
    - 百度文心一格（ERNIE-ViLG）
  - 通过环境变量配置选择后端模型，便于灵活切换和扩展

## 兼容性

- 本项目已在 Cursor 和 Windsurf IDE 的 MCP 集成环境下验证可用。
- 未来计划支持更多兼容 MCP 协议的 IDE 和开发环境。

> 欢迎社区贡献更多模型适配和新功能！

## API 参考

### 腾讯混元生图 API

本项目目前使用腾讯混元生图 API，以下是主要信息：

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

