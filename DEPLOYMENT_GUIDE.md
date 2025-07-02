# 多API图像生成服务部署指南

## 🚀 快速开始

### 第一步：环境准备

1. **Python 环境**（要求 Python 3.8+）
   ```bash
   python --version  # 确认版本 >= 3.8
   ```

2. **安装 UV 包管理器**（推荐）
   ```bash
   # Linux/macOS
   curl -sSf https://astral.sh/uv/install.sh | bash
   
   # Windows
   curl -sSf https://astral.sh/uv/install.ps1 | powershell
   ```

### 第二步：项目设置

1. **克隆或下载项目**
   ```bash
   cd /path/to/your/workspace
   # 如果是 git 项目，执行：git clone <repository-url>
   ```

2. **创建虚拟环境**
   ```bash
   # 使用 UV（推荐）
   uv venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows
   
   # 或使用传统方式
   python -m venv venv
   source venv/bin/activate   # Linux/macOS
   venv\Scripts\activate      # Windows
   ```

3. **安装依赖**
   ```bash
   # 使用 UV
   uv pip install -e .
   
   # 或使用 pip
   pip install -e .
   ```

### 第三步：配置API密钥

1. **复制配置模板**
   ```bash
   cp .env.example .env
   ```

2. **编辑 `.env` 文件**，添加你的API密钥：
   ```env
   # 图像保存目录
   MCP_IMAGE_SAVE_DIR=./generated_images
   
   # 选择性配置以下API（至少配置一个）
   
   # 腾讯混元 API
   TENCENT_SECRET_ID=你的腾讯云SecretId
   TENCENT_SECRET_KEY=你的腾讯云SecretKey
   
   # OpenAI API
   OPENAI_API_KEY=你的OpenAI_API密钥
   
   # 豆包 API
   DOUBAO_ACCESS_KEY=你的豆包AccessKey
   DOUBAO_SECRET_KEY=你的豆包SecretKey
   ```

### 第四步：测试运行

1. **运行测试客户端**
   ```bash
   python test_multi_api_client.py
   ```

2. **启动MCP服务器**
   ```bash
   # 多API版本
   python mcp_image_server_multi.py
   
   # 或使用命令行工具
   multi-api-image-mcp
   ```

## 🔧 Cursor IDE 集成

### 配置步骤

1. **打开 Cursor 设置**
   - 进入 `Settings` > `Features` > `MCP`

2. **添加新的 MCP Server**
   - 点击 `+ Add New MCP Server`

3. **填写配置**
   ```json
   {
     "name": "多API图像生成服务",
     "type": "stdio",
     "command": "python",
     "args": ["/绝对路径/to/mcp_image_server_multi.py"],
     "env": {
       "TENCENT_SECRET_ID": "你的腾讯云SecretId",
       "TENCENT_SECRET_KEY": "你的腾讯云SecretKey",
       "OPENAI_API_KEY": "你的OpenAI_API密钥",
       "DOUBAO_ACCESS_KEY": "你的豆包AccessKey",
       "DOUBAO_SECRET_KEY": "你的豆包SecretKey",
       "MCP_IMAGE_SAVE_DIR": "D:\\your\\save\\directory"
     }
   }
   ```

4. **保存并重启 Cursor**

### 使用示例

在 Cursor 中，你可以这样使用：

```
# 基本使用
"请生成一张可爱小猫的图片"

# 指定提供者
"请使用OpenAI生成一张卡通风格的狗狗图片"

# 指定风格和分辨率
"请生成一张图片，使用hunyuan:shuimo风格，分辨率1024:768，内容是山水画"

# 使用负面提示词
"请生成森林图片，避免包含：dark, scary"
```

## 🎨 API 提供者详细说明

### 腾讯混元 (Hunyuan)

**获取密钥**: [腾讯云控制台](https://console.cloud.tencent.com/cam/capi)

**特点**:
- 中文友好
- 艺术风格丰富
- 支持负面提示词

**推荐用途**:
- 中文描述的图像生成
- 艺术风格图片
- 中国风元素

### OpenAI DALL-E 3

**获取密钥**: [OpenAI Platform](https://platform.openai.com/account/api-keys)

**特点**:
- 高质量输出
- 英文描述优化
- 自动提示词优化

**推荐用途**:
- 高质量照片级图像
- 英文描述
- 创意概念图

### 豆包 (Doubao)

**获取密钥**: [火山引擎控制台](https://console.volcengine.com/)

**特点**:
- 平衡的质量和速度
- 多种风格支持
- 成本效益好

**推荐用途**:
- 批量图像生成
- 快速原型设计
- 成本敏感的应用

## 🛠️ 高级配置

### 自定义端点

如果你使用代理或自定义端点：

```env
# OpenAI 自定义端点
OPENAI_BASE_URL=https://your-proxy.com/v1

# 豆包自定义端点
DOUBAO_ENDPOINT=https://your-endpoint.com
```

### 图像保存设置

```env
# 自定义保存目录
MCP_IMAGE_SAVE_DIR=/path/to/your/images

# Windows 示例
MCP_IMAGE_SAVE_DIR=D:\Projects\Images
```

### 日志级别

在启动脚本时可以设置环境变量：

```bash
# 详细日志
export DEBUG=1
python mcp_image_server_multi.py

# Windows
set DEBUG=1
python mcp_image_server_multi.py
```

## 🐛 故障排除

### 常见问题

1. **启动时显示"没有可用的提供者"**
   - 检查 `.env` 文件是否存在
   - 确认至少配置了一个完整的API密钥对
   - 验证密钥格式是否正确

2. **API调用失败**
   - 检查网络连接
   - 验证API密钥是否有效
   - 确认API配额是否充足

3. **图像保存失败**
   - 检查保存目录是否有写权限
   - 确认目录路径是否正确
   - 查看磁盘空间是否充足

4. **Cursor 中无法识别MCP服务**
   - 确认Python解释器路径是否正确
   - 检查虚拟环境是否激活
   - 验证环境变量是否设置正确

### 调试方法

1. **查看详细日志**
   ```bash
   python mcp_image_server_multi.py 2>&1 | tee debug.log
   ```

2. **测试单个提供者**
   ```bash
   # 只配置一个API进行测试
   python test_multi_api_client.py
   ```

3. **验证环境变量**
   ```bash
   python -c "import os; print('OPENAI_API_KEY:', bool(os.getenv('OPENAI_API_KEY')))"
   ```

## 📈 性能优化

### 提供者选择策略

系统会按以下优先级自动选择提供者：
1. Hunyuan（如果配置）
2. OpenAI（如果配置）
3. Doubao（如果配置）

你可以通过环境变量自定义优先级：

```env
DEFAULT_PROVIDER=openai  # 设置默认提供者
```

### 并发控制

对于批量生成，建议：
- 控制并发数量（通常不超过3个并发请求）
- 添加请求间隔（避免触发限流）
- 监控API配额使用情况

## 🔄 升级和维护

### 更新依赖

```bash
# 使用 UV
uv pip install --upgrade -e .

# 使用 pip
pip install --upgrade -e .
```

### 备份配置

```bash
# 备份配置文件
cp .env .env.backup

# 备份生成的图像
tar -czf images_backup.tar.gz generated_images/
```

### 监控和日志

建议定期检查：
- API调用成功率
- 图像生成质量
- 错误日志和异常

## 📞 获取帮助

如果遇到问题：

1. 查看本指南的故障排除部分
2. 检查项目的 README 文档
3. 查看 GitHub Issues（如果是开源项目）
4. 运行测试客户端验证环境配置

---

**祝你使用愉快！** 🎉