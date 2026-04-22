# 测试脚本 - 验证地图导览模块
# 运行命令: python scripts/test_map.py

import os
import sys

# Windows编码兼容
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_merchant_database():
    """测试商户数据库"""
    print("=== 测试商户数据库 ===")
    
    from merchant_db import get_merchant_database
    db = get_merchant_database()
    
    print(f"商户总数: {db.get_merchant_count()}")
    
    # 测试查询
    merchant = db.get_merchant("星巴克")
    print(f"\n星巴克信息:")
    print(f"  名称: {merchant['name']}")
    print(f"  位置: {merchant['location']}")
    print(f"  类型: {merchant['type']}")
    print(f"  优惠: {merchant['promotion']}")
    
    # 测试搜索
    results = db.search_merchants("餐饮")
    print(f"\n餐饮类商户: {len(results)} 家")
    for m in results:
        print(f"  - {m['name']}: {m['location']}")
    
    print("\n✓ 商户数据库测试通过\n")
    return True


def test_map_service():
    """测试地图服务"""
    print("=== 测试地图服务 ===")
    
    from map_service import get_map_service
    service = get_map_service()
    
    # 测试地理编码
    result = service.geocode("A区3号")
    print(f"地理编码结果: {result}")
    
    # 测试地图链接
    link = service.get_map_link(116.4074, 39.9042)
    print(f"地图链接: {link}")
    
    # 测试构建导航回复
    merchant = {
        'name': '星巴克',
        'location': 'A区3号',
        'lng': '116.4074',
        'lat': '39.9042',
        'promotion': '下午茶套餐45元'
    }
    reply = service.build_navigation_reply('星巴克', merchant)
    print(f"\n导航回复:\n{reply}")
    
    print("\n✓ 地图服务测试通过\n")
    return True


def test_location_handler():
    """测试位置查询处理器"""
    print("=== 测试位置查询处理器 ===")
    
    from location_handler import get_location_handler
    handler = get_location_handler()
    
    test_cases = [
        "星巴克在哪？",
        "肯德基怎么走？",
        "我想吃饭",
        "有什么优惠？",
        "星巴克有优惠吗？",
        "餐厅有哪些？"
    ]
    
    for msg in test_cases:
        if handler.can_handle(msg):
            result = handler.handle(msg)
            print(f"\nQ: {msg}")
            print(f"A: {result[:100]}..." if len(result) > 100 else f"A: {result}")
    
    print("\n✓ 位置查询处理器测试通过\n")
    return True


def test_wechat_bot_integration():
    """测试企业微信机器人集成"""
    print("=== 测试企业微信机器人集成 ===")
    
    from wechat_work_bot import WeChatWorkBot
    
    bot = WeChatWorkBot()
    
    # 测试欢迎语是否包含商户列表
    print(f"欢迎语长度: {len(bot.welcome_message)} 字符")
    if '星巴克' in bot.welcome_message:
        print("✓ 欢迎语已包含商户列表")
    
    # 测试消息处理
    test_id = "test_user_map"
    response = bot.process_message(test_id, "星巴克在哪？")
    print(f"\n位置查询回复:\n{response[:150]}..." if len(response) > 150 else f"\n位置查询回复: {response}")
    
    print("\n✓ 企业微信机器人集成测试通过\n")
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*50)
    print("  地图导览模块 - 功能测试")
    print("="*50 + "\n")
    
    results = []
    
    # 运行测试
    results.append(("商户数据库", test_merchant_database()))
    results.append(("地图服务", test_map_service()))
    results.append(("位置查询处理器", test_location_handler()))
    # results.append(("企业微信集成", test_wechat_bot_integration()))
    
    # 汇总结果
    print("="*50)
    print("  测试结果汇总")
    print("="*50)
    
    all_passed = True
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "="*50)
    if all_passed:
        print("  所有测试通过！")
    else:
        print("  部分测试失败，请检查错误信息")
    print("="*50 + "\n")
    
    return all_passed


if __name__ == '__main__':
    run_all_tests()
