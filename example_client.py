import asyncio
import os
import json
import base64
from typing import Dict, Any
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

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
    print(f"启动图像生成: prompt={prompt}, style={style}, resolution={resolution}")
    
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
    print("连接到MCP服务器...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 初始化连接
            await session.initialize()
            print("成功连接到MCP图像生成服务器")
            
            # 列出可用资源
            print("\n查询可用风格...")
            styles_response = await session.read_resource("styles://list")
            if hasattr(styles_response, 'contents') and styles_response.contents:
                print(f"可用风格: \n{styles_response.contents[0].text}")
            
            print("\n查询可用分辨率...")
            resolutions_response = await session.read_resource("resolutions://list")
            if hasattr(resolutions_response, 'contents') and resolutions_response.contents:
                print(f"可用分辨率: \n{resolutions_response.contents[0].text}")
            
            # 设置一个定时打印任务，每10秒打印一次进度提醒
            progress_task = None
            
            async def print_client_progress():
                count = 0
                while True:
                    count += 1
                    print(f"[客户端进度] 等待服务器响应... 已等待 {count*10} 秒")
                    await asyncio.sleep(10)
            
            # 生成图像
            print("\n开始生成图像，这可能需要几分钟时间...")
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
                
                print(f"收到服务器响应")
                
                # 处理结果
                if hasattr(result, 'content') and result.content:
                    content_item = result.content[0]
                    print(f"内容项类型: {type(content_item)}")
                    
                    # 处理文本内容类型
                    if hasattr(content_item, 'text'):
                        text = content_item.text
                        print(f"文本内容: {text[:100]}..." if len(text) > 100 else text)
                        
                        # 尝试解析JSON
                        try:
                            json_data = json.loads(text)
                            
                            # 检查是否有错误
                            if "error" in json_data:
                                print(f"服务器返回错误: {json_data['error']}")
                                return False
                                
                            # 检查是否有内容
                            if "content" in json_data:
                                # 保存base64编码的图像
                                image_data = base64.b64decode(json_data["content"])
                                filename = f"generated_{style}_{resolution.replace(':', 'x')}.jpg"
                                
                                with open(filename, "wb") as f:
                                    f.write(image_data)
                                    
                                print(f"图像成功保存为 '{filename}'")
                                return True
                        except json.JSONDecodeError:
                            print(f"无法解析JSON: {text[:50]}...")
                            
                    # 处理字典类型
                    elif hasattr(content_item, 'keys') or hasattr(content_item, '__getitem__'):
                        print(f"字典内容: {content_item}")
                        
                        # 检查是否有错误
                        if "error" in content_item:
                            print(f"服务器返回错误: {content_item['error']}")
                            return False
                            
                        # 检查是否有内容
                        if "content" in content_item:
                            # 保存base64编码的图像
                            image_data = base64.b64decode(content_item["content"])
                            filename = f"generated_{style}_{resolution.replace(':', 'x')}.jpg"
                            
                            with open(filename, "wb") as f:
                                f.write(image_data)
                                
                            print(f"图像成功保存为 '{filename}'")
                            return True
                else:
                    print("服务器未返回内容")
                
            except asyncio.TimeoutError:
                print("图像生成超时，请稍后重试")
                return False
            except Exception as e:
                import traceback
                print(f"图像生成过程中发生异常: {e}")
                print(traceback.format_exc())
                return False
            finally:
                # 确保进度任务被取消
                if progress_task and not progress_task.done():
                    progress_task.cancel()
    
    print("未能生成图像")
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
        print("图像生成过程成功完成")
    else:
        print("图像生成过程未成功完成")

if __name__ == "__main__":
    asyncio.run(main()) 