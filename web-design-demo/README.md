# Web Design Demo with MCP Image Generation

This demo showcases how to integrate MCP (Multi-agent Collaboration Platform) image generation into a modern web design workflow. The project demonstrates how AI-generated images can be used directly in a static website, making it easy to create visually rich, dynamic content for company homepages or product showcases.

## Features
- Uses MCP to generate images for various roles and scenarios (e.g., AI Project Manager, Developer, QA Engineer, etc.)
- Images are generated once and then referenced directly in the HTML for fast loading
- Clean, modern web design suitable for tech companies or AI product teams
- Easy to extend with new images or roles

## Directory Structure
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
└── README.md
```

## How It Works
1. **Image Generation:** Use the MCP image generation tool to create images for each role or scenario you want to display on the website. Save the generated images in the `images/` directory.
2. **Static Reference:** In `index.html`, reference the generated images using standard `<img src="images/xxx.jpg">` tags.
3. **No Dynamic Loading:** All images are pre-generated and served as static assets for maximum performance and compatibility.

## Setup & Usage
1. Make sure you have Python installed (for running a local HTTP server).
2. In the `web-design-demo` directory, run:
   ```
   python -m http.server 8000
   ```
3. Open your browser and visit [http://localhost:8000](http://localhost:8000)
4. The homepage will display AI-generated images for each team role and service.

## Customization
- To add or update images, use the MCP image generation tool and place new images in the `images/` directory.
- Update `index.html` to reference new images as needed.
- You can change styles, prompts, or add new sections to fit your company's needs.

