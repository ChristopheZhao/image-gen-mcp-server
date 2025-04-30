# 多代理系统演示

这是一个展示多代理人工智能系统的简单网页演示，包含使用MCP（Model Context Protocol）图像生成功能。

## 项目结构

```
multi-agent-demo/
├── css/              # 样式文件
│   └── style.css     
├── images/           # 图片目录
│   └── README.txt    # 图片说明
├── js/               # JavaScript文件
│   └── script.js     # 图片保存和加载逻辑
├── index.html        # 主页面
└── README.md         # 项目说明
```

## 功能

1. **多代理系统介绍**：提供多代理系统的基本概念和架构说明
2. **MCP图像生成**：演示如何使用MCP工具生成图像
3. **图片保存**：允许用户将生成的图片保存到本地

## 使用方法

1. 打开`index.html`文件查看网页
2. 查看已经展示的示例图片（这些是通过MCP生成的）
3. 点击"Generate Image with MCP"按钮调用MCP图像生成工具
4. 输入提示词生成新图片
5. 点击"Save Image"按钮保存图片到本地

## 添加图片

在使用前，确保`images`目录包含以下图片：

- `multi-agent-overview.jpg`：多代理系统概述图
- `multi-agent-architecture.jpg`：多代理系统架构图
- `naruto-and-iruka.jpg`：鸣人和伊鲁卡图片（示例）

这些图片可以从对话中保存，或使用MCP重新生成。详细说明请查看`images/README.txt`文件。

## MCP集成

本项目通过`mcp:generate_image`协议链接调用MCP图像生成工具。当用户点击"Generate Image with MCP"按钮时，会触发MCP工具的调用。

## 注意事项

- 这是一个演示项目，主要展示MCP图像生成功能的集成
- 页面中的图片展示了MCP图像生成的能力
- 实际应用中，可以扩展此功能，创建更复杂的多代理系统 