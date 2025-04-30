# Web Design Demo（网页设计演示）—— MCP图像生成集成

本项目演示了如何将MCP（多智能体协作平台）的图像生成功能集成到现代网页设计流程中。通过AI生成的图片，您可以轻松为公司主页、产品展示等静态网站添加丰富的视觉内容。

## 主要特性
- 使用MCP工具为不同角色和场景生成图片（如AI项目经理、开发者、测试工程师等）
- 图片生成后直接放入`images/`目录，通过HTML引用，加载速度快
- 现代、简洁的网页设计，适合科技公司或AI团队展示
- 易于扩展和自定义

## 目录结构
```
web-design-demo/
├── css/
│   └── style.css
├── images/
│   ├── agent_hero_banner_xxx.jpg
│   ├── ai_project_manager_xxx.jpg
│   └── ...
├── js/
│   └── main.js
├── index.html
└── README_ZH.md
```

## 使用说明
1. **图片生成**：使用MCP图像生成工具，为每个角色或场景生成图片，并保存到`images/`目录。
2. **静态引用**：在`index.html`中，通过`<img src="images/xxx.jpg">`标签引用图片。
3. **无需动态加载**：所有图片均为预生成静态资源，性能高、兼容性好。

## 运行方法
1. 确保已安装Python（用于本地HTTP服务器）。
2. 在`web-design-demo`目录下运行：
   ```
   python -m http.server 8000
   ```
3. 在浏览器访问 [http://localhost:8000](http://localhost:8000)
4. 首页会展示各团队角色和服务的AI生成图片。

## 自定义与扩展
- 如需添加或更新图片，使用MCP工具生成新图片，放入`images/`目录。
- 修改`index.html`，引用新图片。
- 可根据实际需求调整风格、提示词或添加新板块。
