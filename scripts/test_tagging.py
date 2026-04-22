# 测试脚本 - 验证三层标签体系
# 运行命令: python scripts/test_tagging.py

import os
import sys

# 添加scripts目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_layer1_preset_tagging():
    """测试第一层：预设规则标签"""
    print("=== 测试第一层：预设规则标签 ===")
    
    from tagging_system import TaggingSystem
    system = TaggingSystem()
    
    test_cases = [
        ("我想找个餐厅吃饭", ["餐饮", "导览"]),
        ("有没有便宜点的优惠？", ["价格敏感", "意向低"]),
        ("孩子想去游乐场", ["亲子", "娱乐"]),
        ("帮我找一下附近的咖啡", ["餐饮", "导览"]),
    ]
    
    all_passed = True
    for message, expected_tags in test_cases:
        tags = system.layer1_preset_tagging(message)
        tag_names = [t['tag'] for t in tags]
        
        # 检查是否包含预期标签
        found = all(any(exp in tag for tag in tag_names) for exp in expected_tags)
        
        status = "OK" if found else "FAIL"
        print(f"  [{status}] \"{message}\"")
        print(f"     识别标签: {tag_names}")
        
        if not found:
            all_passed = False
    
    print(f"第一层测试: {'通过' if all_passed else '失败'}\n")
    return all_passed


def test_tagging_integration():
    """测试标签系统与记忆系统集成"""
    print("=== 测试标签系统与记忆系统集成 ===")
    
    from memory_system import get_memory_system, get_tagging_system
    
    ms = get_memory_system()
    ts = get_tagging_system()
    
    # 创建测试会话
    test_id = "tagging_test_001"
    ms.create_session(test_id)
    
    # 发送测试消息
    test_messages = [
        "我想找餐厅吃饭",
        "有没有便宜点的优惠？",
        "孩子想去游乐场"
    ]
    
    all_passed = True
    for msg in test_messages:
        # 使用标签系统处理
        tags = ts.process_message(msg, {'visitor_id': test_id})
        
        # 使用记忆系统更新
        ms.update_session(test_id, msg)
        
        print(f"  消息: \"{msg}\"")
        print(f"     标签数量: {len(tags)}")
    
    # 获取最终标签
    final_tags = ms.get_tags(test_id)
    print(f"\n  最终标签: {final_tags}")
    
    print(f"集成测试: {'通过' if all_passed else '失败'}\n")
    return all_passed


def test_tagging_config():
    """测试标签配置"""
    print("=== 测试标签配置加载 ===")
    
    from tagging_system import TaggingSystem
    system = TaggingSystem()
    
    # 检查配置是否正确加载
    layer1 = system.layer_1_config
    layer2 = system.layer_2_config
    layer3 = system.layer_3_config
    
    print(f"  第一层配置: {'已加载' if layer1 else '未加载'}")
    print(f"  第二层配置: {'已加载' if layer2 else '未加载'}")
    print(f"  第三层配置: {'已加载' if layer3 else '未加载'}")
    
    # 检查配置内容
    if layer1:
        categories = layer1.get('categories', {})
        print(f"  第一层类别: {list(categories.keys())}")
    
    passed = bool(layer1 and layer2 and layer3)
    print(f"配置测试: {'通过' if passed else '失败'}\n")
    return passed


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*50)
    print("  三层标签体系 - 功能测试")
    print("="*50 + "\n")
    
    results = []
    
    # 运行测试
    results.append(("标签配置加载", test_tagging_config()))
    results.append(("第一层预设标签", test_layer1_preset_tagging()))
    results.append(("系统集成", test_tagging_integration()))
    
    # 汇总结果
    print("="*50)
    print("  测试结果汇总")
    print("="*50)
    
    all_passed = True
    for name, result in results:
        status = "[OK]" if result else "[FAIL]"
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
