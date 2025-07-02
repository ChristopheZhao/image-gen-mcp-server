#!/usr/bin/env python3
"""
测试多API图像生成服务的客户端脚本
用于验证不同提供者的功能和参数
"""

import asyncio
import json
import sys
from pathlib import Path

from api_providers import ProviderManager

async def test_provider_manager():
    """测试提供者管理器功能"""
    print("=" * 50)
    print("测试多API提供者管理器")
    print("=" * 50)
    
    # 初始化提供者管理器
    manager = ProviderManager()
    
    # 检查可用提供者
    available_providers = manager.get_available_providers()
    print(f"可用提供者: {available_providers}")
    print(f"默认提供者: {manager.default_provider}")
    
    if not available_providers:
        print("\n❌ 没有可用的提供者！请检查环境变量配置。")
        print("需要配置的环境变量：")
        print("- TENCENT_SECRET_ID 和 TENCENT_SECRET_KEY (腾讯混元)")
        print("- OPENAI_API_KEY (OpenAI)")
        print("- DOUBAO_ACCESS_KEY 和 DOUBAO_SECRET_KEY (豆包)")
        return False
    
    # 显示所有提供者的风格和分辨率
    print("\n📊 提供者详细信息：")
    for provider_name in available_providers:
        provider = manager.get_provider(provider_name)
        if provider:
            print(f"\n🔹 {provider_name.upper()}:")
            print(f"  风格: {list(provider.get_available_styles().keys())}")
            print(f"  分辨率: {list(provider.get_available_resolutions().keys())}")
    
    return True

async def test_image_generation(manager: ProviderManager):
    """测试图像生成功能"""
    print("\n" + "=" * 50)
    print("测试图像生成功能")
    print("=" * 50)
    
    test_cases = [
        {
            "name": "默认提供者测试",
            "params": {
                "query": "一只可爱的小猫坐在花园里",
                "provider_name": None,  # 使用默认提供者
                "style": "",
                "resolution": "",
                "negative_prompt": ""
            }
        },
        {
            "name": "Hunyuan提供者测试",
            "params": {
                "query": "赛博朋克风格的未来城市",
                "provider_name": "hunyuan",
                "style": "saibopengke",
                "resolution": "1024:768",
                "negative_prompt": "low quality, blurry"
            }
        },
        {
            "name": "OpenAI提供者测试",
            "params": {
                "query": "A magical forest with glowing mushrooms",
                "provider_name": "openai",
                "style": "fantasy",
                "resolution": "1024x1024",
                "negative_prompt": "dark, scary"
            }
        },
        {
            "name": "Doubao提供者测试",
            "params": {
                "query": "中国风山水画，有竹子和小桥",
                "provider_name": "doubao",
                "style": "chinese_painting",
                "resolution": "768x1024",
                "negative_prompt": "modern, city"
            }
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        print(f"\n🧪 {test_case['name']}")
        params = test_case['params']
        
        # 检查提供者是否可用
        if params['provider_name'] and params['provider_name'] not in manager.get_available_providers():
            print(f"   ⏭️  跳过 - 提供者 '{params['provider_name']}' 不可用")
            continue
            
        try:
            print(f"   📝 提示词: {params['query']}")
            print(f"   🎨 提供者: {params['provider_name'] or '默认'}")
            print(f"   🖼️  风格: {params['style'] or '默认'}")
            print(f"   📐 分辨率: {params['resolution'] or '默认'}")
            
            # 模拟生成（不实际调用API以节省费用）
            print("   ⏳ 模拟生成中...")
            
            # 这里注释掉实际的API调用，避免产生费用
            # result = await manager.generate_images(**params)
            
            # 模拟成功结果
            result = [{
                "content": "base64_encoded_image_data_here",
                "content_type": "image/jpeg",
                "description": params['query'],
                "style": params['style'],
                "provider": params['provider_name'] or manager.default_provider
            }]
            
            print("   ✅ 模拟生成成功")
            results.append({
                "test_case": test_case['name'],
                "status": "success",
                "provider": result[0].get('provider'),
                "result": result
            })
            
        except Exception as e:
            print(f"   ❌ 生成失败: {str(e)}")
            results.append({
                "test_case": test_case['name'],
                "status": "failed",
                "error": str(e)
            })
    
    return results

async def test_parameter_validation(manager: ProviderManager):
    """测试参数验证功能"""
    print("\n" + "=" * 50)
    print("测试参数验证功能")
    print("=" * 50)
    
    available_providers = manager.get_available_providers()
    if not available_providers:
        print("⏭️  跳过参数验证测试 - 没有可用提供者")
        return
    
    # 选择第一个可用提供者进行测试
    test_provider = available_providers[0]
    provider_instance = manager.get_provider(test_provider)
    
    if not provider_instance:
        print(f"❌ 无法获取提供者实例: {test_provider}")
        return
    
    print(f"\n🧪 使用提供者 '{test_provider}' 进行参数验证测试")
    
    # 测试风格验证
    print("\n🎨 风格验证测试:")
    available_styles = list(provider_instance.get_available_styles().keys())
    valid_style = available_styles[0] if available_styles else "default"
    invalid_style = "invalid_style_xyz"
    
    print(f"   ✅ 有效风格 '{valid_style}': {provider_instance.validate_style(valid_style)}")
    print(f"   ❌ 无效风格 '{invalid_style}': {provider_instance.validate_style(invalid_style)}")
    
    # 测试分辨率验证
    print("\n📐 分辨率验证测试:")
    available_resolutions = list(provider_instance.get_available_resolutions().keys())
    valid_resolution = available_resolutions[0] if available_resolutions else "1024x1024"
    invalid_resolution = "999x999"
    
    print(f"   ✅ 有效分辨率 '{valid_resolution}': {provider_instance.validate_resolution(valid_resolution)}")
    print(f"   ❌ 无效分辨率 '{invalid_resolution}': {provider_instance.validate_resolution(invalid_resolution)}")

def print_summary(results):
    """打印测试结果摘要"""
    print("\n" + "=" * 50)
    print("测试结果摘要")
    print("=" * 50)
    
    total_tests = len(results)
    successful_tests = len([r for r in results if r['status'] == 'success'])
    failed_tests = total_tests - successful_tests
    
    print(f"📊 总测试数: {total_tests}")
    print(f"✅ 成功: {successful_tests}")
    print(f"❌ 失败: {failed_tests}")
    
    if failed_tests > 0:
        print("\n❌ 失败的测试:")
        for result in results:
            if result['status'] == 'failed':
                print(f"   - {result['test_case']}: {result['error']}")
    
    print(f"\n🎉 测试完成! 成功率: {(successful_tests/total_tests*100):.1f}%")

async def main():
    """主函数"""
    print("🚀 启动多API图像生成服务测试")
    
    # 测试提供者管理器
    if not await test_provider_manager():
        sys.exit(1)
    
    # 创建管理器实例
    manager = ProviderManager()
    
    # 测试参数验证
    await test_parameter_validation(manager)
    
    # 测试图像生成
    results = await test_image_generation(manager)
    
    # 打印摘要
    print_summary(results)
    
    print("\n💡 提示:")
    print("- 这是模拟测试，没有实际调用API")
    print("- 要进行真实测试，请取消注释 test_image_generation 函数中的API调用")
    print("- 确保你有足够的API配额，因为图像生成会产生费用")

if __name__ == "__main__":
    # 设置事件循环策略（Windows兼容性）
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main())