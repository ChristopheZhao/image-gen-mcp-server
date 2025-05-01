import asyncio
import os
import json
import base64
from typing import Dict, Any
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import pprint

# Load environment variables
load_dotenv()

async def generate_and_save_image(prompt: str, style: str = "xieshi", resolution: str = "1792:1024", negative_prompt: str = "") -> bool:
    """
    生成并保存图像
    
    Args:
        prompt: 图像描述
        style: 图像风格
        resolution: 图像分辨率
        negative_prompt: 负面提示词
        
    Returns:
        bool: 是否成功生成并保存图像
    """
    print(f"Starting image generation: prompt={prompt}, style={style}, resolution={resolution}")
    
    # 设置服务器参数
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_image_server.py"],
        env={
            "TENCENT_SECRET_ID": os.getenv("TENCENT_SECRET_ID"),
            "TENCENT_SECRET_KEY": os.getenv("TENCENT_SECRET_KEY")
        },
        startupTimeout=30000  # 增加启动超时到30秒
    )
    
    # 连接到MCP服务器
    print("Connecting to MCP server...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 初始化连接
            await session.initialize()
            print("Successfully connected to MCP image generation server")
            
            # 列出可用资源
            print("\nQuerying available styles...")
            styles_response = await session.read_resource("styles://list")
            if hasattr(styles_response, 'contents') and styles_response.contents:
                styles_dict = json.loads(styles_response.contents[0].text)
                print("Available styles:")
                pprint.pprint(styles_dict)
            
            print("\nQuerying available resolutions...")
            resolutions_response = await session.read_resource("resolutions://list")
            if hasattr(resolutions_response, 'contents') and resolutions_response.contents:
                resolutions_dict = json.loads(resolutions_response.contents[0].text)
                print("Available resolutions:")
                pprint.pprint(resolutions_dict)
            
            # List available tools
            print("\nQuerying available tools...")
            try:
                tools = await session.list_tools()
                print("Available tools:")
                for tool in tools:
                    print('tool = ', tool)
                    # print(f"- {tool['name']}: {tool.get('description', '')}")
                    # if 'parameters' in tool:
                    #     print("  Parameters:")
                    #     for param, param_info in tool['parameters'].items():
                    #         print(f"    {param}: {param_info}")
            except Exception as e:
                print(f"Failed to list tools: {e}")
            
            # 设置一个定时打印任务，每10秒打印一次进度提醒
            progress_task = None
            
            async def print_client_progress():
                count = 0
                while True:
                    count += 1
                    print(f"[Client Progress] Waiting for server response... waited {count*10} seconds")
                    await asyncio.sleep(10)
            
            # 生成图像
            print("\nStarting image generation, this may take a few minutes...")
            try:
                # 启动进度打印任务
                progress_task = asyncio.create_task(print_client_progress())
                
                # 设置一个较长的超时时间（5分钟）
                result = await asyncio.wait_for(
                    session.call_tool(
                        "generate_image", 
                        arguments={
                            "prompt": prompt,
                            "style": style,
                            "resolution": resolution,
                            "negative_prompt": negative_prompt
                        }
                    ),
                    timeout=300.0  # 5分钟超时
                )
                
                # 任务完成后取消进度打印
                if progress_task and not progress_task.done():
                    progress_task.cancel()
                
                print("Received response from server")
                
                # 处理结果
                if hasattr(result, 'content') and result.content:
                    content_item = result.content[0]
                    print(f"Content item type: {type(content_item)}")
                    
                    # 处理文本内容类型
                    if hasattr(content_item, 'text'):
                        text = content_item.text
                        print(f"Server response: {text}")
                        # 判断是否包含图片保存路径
                        if "saved to:" in text:
                            print("Image has been saved by the server. No need to save on client side.")
                            return True
                        else:
                            print("Server response does not contain image save path.")
                            return False
                    # 处理字典类型
                    elif hasattr(content_item, 'keys') or hasattr(content_item, '__getitem__'):
                        print(f"Dictionary content: {content_item}")
                        
                        # 检查是否有错误
                        if "error" in content_item:
                            print(f"Server returned error: {content_item['error']}")
                            return False
                            
                        # 检查是否有内容
                        if "content" in content_item:
                            # 保存base64编码的图像
                            image_data = base64.b64decode(content_item["content"])
                            filename = f"generated_{style}_{resolution.replace(':', 'x')}.jpg"
                            
                            with open(filename, "wb") as f:
                                f.write(image_data)
                                
                            print(f"Image successfully saved as '{filename}'")
                            return True
                else:
                    print("No content returned from server")
                
            except asyncio.TimeoutError:
                print("Image generation timed out, please try again later")
                return False
            except Exception as e:
                import traceback
                print(f"Exception occurred during image generation: {e}")
                print(traceback.format_exc())
                return False
            finally:
                # 确保进度任务被取消
                if progress_task and not progress_task.done():
                    progress_task.cancel()
    
    print("Image generation was not successful")
    return False

async def main():
    """主程序入口"""
    prompt = "一朵红色的花"  # 更简单的提示
    style = "xieshi"  # 写实风格
    resolution = "1024:1024"  # 1:1 方形
    negative_prompt = "模糊的, 低质量的"
    
    success = await generate_and_save_image(
        prompt=prompt,
        style=style, 
        resolution=resolution,
        negative_prompt=negative_prompt
    )
    
    if success:
        print("Image generation process completed successfully")
    else:
        print("Image generation process was not successful")

if __name__ == "__main__":
    asyncio.run(main()) 