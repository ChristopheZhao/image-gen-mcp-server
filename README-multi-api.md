# MCP 多API图像生成服务

一个基于 Model Context Protocol (MCP) 的图像生成服务，支持多个主流的图像生成API，包括腾讯混元、OpenAI GPT-4o/DALL-E 和豆包。

## 🎯 新特性

### 多API提供者支持
- **腾讯混元 (Hunyuan)**: 支持多种中文优化的艺术风格
- **OpenAI DALL-E 3**: 高质量图像生成，支持英文描述优化
- **豆包 (Doubao)**: 字节跳动的图像生成服务

### 智能提供者管理
- 自动检测可用的API提供者
- 支持指定特定提供者或自动选择
- 统一的错误处理和重试机制

### 灵活的参数格式
- 支持 `provider:style` 格式指定特定提供者的风格
- 支持 `provider:resolution` 格式指定特定提供者的分辨率
- 向后兼容原有的参数格式

## 📦 安装

### 环境要求
- Python 3.8+
- 有效的API密钥（至少配置一个提供者）

### 使用 UV 安装（推荐）

```bash
# 安装 UV
curl -sSf https://astral.sh/uv/install.sh | bash  # Linux/macOS
# 或
curl -sSf https://astral.sh/uv/install.ps1 | powershell  # Windows

# 克隆项目
git clone <repository-url>
cd image-gen-mcp-server

# 创建虚拟环境并安装依赖
uv venv
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate  # Windows

uv pip install -e .
```

### 传统 pip 安装

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -e .
```

## ⚙️ 配置

在项目根目录创建 `.env` 文件，配置所需的API密钥：

```env
# 通用配置
MCP_IMAGE_SAVE_DIR=./generated_images

# 腾讯混元 API（混元绘画）
TENCENT_SECRET_ID=你的腾讯云SecretId
TENCENT_SECRET_KEY=你的腾讯云SecretKey

# OpenAI API（DALL-E 3）
OPENAI_API_KEY=你的OpenAI_API密钥
OPENAI_BASE_URL=https://api.openai.com/v1  # 可选，自定义端点

# 豆包 API（字节跳动）
DOUBAO_ACCESS_KEY=你的豆包AccessKey
DOUBAO_SECRET_KEY=你的豆包SecretKey
DOUBAO_ENDPOINT=https://visual.volcengineapi.com  # 可选，自定义端点
```

**注意**: 你只需要配置想要使用的API提供者的密钥，系统会自动检测可用的提供者。

## 🚀 使用方法

### 启动多API服务器

```bash
# 使用新的多API服务器
python mcp_image_server_multi.py
```

### 基本用法

```python
# 使用默认提供者
generate_image(prompt="一只可爱的小猫")

# 指定特定提供者
generate_image(prompt="A cute cat", provider="openai")

# 使用提供者特定的风格和分辨率
generate_image(
    prompt="赛博朋克风格的城市", 
    style="hunyuan:saibopengke", 
    resolution="hunyuan:1024:768"
)

# 混合使用不同提供者的参数
generate_image(
    prompt="Future city", 
    provider="openai",
    style="cyberpunk", 
    resolution="1024x1792"
)
```

## 📊 支持的提供者和参数

### 腾讯混元 (Hunyuan)

**风格选项**:
- `riman`: 日漫动画
- `xieshi`: 写实
- `monai`: 莫奈画风
- `shuimo`: 水墨画
- `saibopengke`: 赛博朋克
- `youhua`: 油画
- 等18种风格...

**分辨率选项**:
- `768:768`, `1024:1024`: 正方形
- `768:1024`, `1024:768`: 3:4 和 4:3
- `720:1280`, `1280:720`: 16:9 和 9:16
- 等8种分辨率...

### OpenAI DALL-E 3

**风格选项**:
- `natural`: 自然风格
- `vivid`: 生动风格
- `realistic`: 写实风格
- `artistic`: 艺术风格
- `anime`: 动漫风格
- `oil_painting`: 油画风格
- 等12种风格...

**分辨率选项**:
- `1024x1024`: 正方形
- `1024x1792`, `1792x1024`: 16:9 和 9:16
- `1344x768`, `768x1344`: 7:4 和 4:7
- 等7种分辨率...

### 豆包 (Doubao)

**风格选项**:
- `general`: 通用风格
- `anime`: 动漫风格
- `realistic`: 写实风格
- `chinese_painting`: 国画风格
- `cyberpunk`: 赛博朋克
- `fantasy`: 奇幻风格
- 等12种风格...

**分辨率选项**:
- `512x512`, `768x768`, `1024x1024`: 正方形
- `576x1024`, `1024x576`: 9:16 和 16:9
- `768x1024`, `1024x768`: 3:4 和 4:3
- 等9种分辨率...

## 🔌 MCP 资源和工具

### 可用资源

```
providers://list                    # 获取可用的提供者列表
styles://list                       # 获取所有提供者的风格
resolutions://list                  # 获取所有提供者的分辨率
styles://provider/{provider_name}   # 获取特定提供者的风格
resolutions://provider/{provider_name} # 获取特定提供者的分辨率
```

### 可用工具

```
generate_image                      # 多提供者图像生成工具
```

### 提示模板

```
image_generation_prompt            # 多API图像生成提示模板
```

## 💡 高级用法

### 1. 自动提供者选择

系统会按照以下优先级自动选择提供者:
1. Hunyuan (如果配置了腾讯云密钥)
2. OpenAI (如果配置了OpenAI密钥)
3. Doubao (如果配置了豆包密钥)

### 2. 提供者特定优化

每个提供者都有其特色:

- **Hunyuan**: 中文描述友好，艺术风格丰富
- **OpenAI**: 英文描述优化，高质量输出
- **Doubao**: 平衡的质量和速度

### 3. 错误处理和降级

当指定的提供者不可用时，系统会:
1. 显示详细的错误信息
2. 提供可用提供者的列表
3. 建议正确的参数格式

## 🔧 Cursor IDE 集成

### 配置 MCP Server

在 Cursor 的 MCP 设置中添加:

```json
{
  "name": "多API图像生成服务",
  "type": "stdio", 
  "command": "python",
  "args": ["/path/to/mcp_image_server_multi.py"],
  "env": {
    "TENCENT_SECRET_ID": "你的腾讯云SecretId",
    "TENCENT_SECRET_KEY": "你的腾讯云SecretKey",
    "OPENAI_API_KEY": "你的OpenAI_API密钥",
    "DOUBAO_ACCESS_KEY": "你的豆包AccessKey", 
    "DOUBAO_SECRET_KEY": "你的豆包SecretKey",
    "MCP_IMAGE_SAVE_DIR": "D:\\data\\mcp_img"
  }
}
```

### 使用示例

在 Cursor 中，你可以这样使用:

```
# 自动选择最佳提供者
"请生成一张赛博朋克风格的城市图片"

# 指定使用OpenAI
"请使用OpenAI生成一张cartoon风格的猫咪图片"

# 使用特定提供者的风格
"请生成一张图片，风格为hunyuan:shuimo，内容是山水画"

# 混合参数使用
"请使用doubao生成1024x768分辨率的fantasy风格图片，内容是魔法森林"
```

## 🔍 故障排除

### 常见问题

1. **没有可用的提供者**
   - 检查 `.env` 文件中的API密钥配置
   - 确保至少配置了一个提供者的完整密钥

2. **特定提供者不可用**
   - 检查该提供者的API密钥是否正确
   - 检查网络连接和API配额

3. **风格或分辨率错误**
   - 使用 `providers://list` 查看可用提供者
   - 使用 `styles://provider/{provider}` 查看提供者支持的风格
   - 使用正确的格式：`provider:style` 或 `provider:resolution`

### 调试模式

启动服务器时会在stderr输出详细的调试信息，包括:
- 已初始化的提供者
- 默认提供者选择
- API调用过程
- 错误详情

## 🚗 路线图

- [x] 腾讯混元 API 支持
- [x] OpenAI DALL-E 3 支持  
- [x] 豆包 API 支持
- [x] 多提供者管理系统
- [ ] 阿里通义万相支持
- [ ] 百度文心一格支持
- [ ] Stable Diffusion API支持
- [ ] 图像风格转换功能
- [ ] 批量图像生成
- [ ] 图像编辑和修改功能

## 📄 许可证

[MIT License](LICENSE)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

### 添加新的API提供者

1. 在 `api_providers/` 目录下创建新的提供者文件
2. 继承 `BaseImageProvider` 类
3. 实现必要的方法
4. 在 `ProviderManager` 中注册新提供者
5. 更新文档和测试

## 📞 支持

如果你遇到问题或有建议，请：
1. 查看故障排除部分
2. 搜索现有的 Issues
3. 创建新的 Issue 并提供详细信息

---

*使用多个API提供者，让你的创意无限扩展！* ✨