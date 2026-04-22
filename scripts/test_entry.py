# 测试脚本 - 验证游客入口模块
# 运行命令: python scripts/test_entry.py

import os
import sys
import json
from datetime import datetime

# Windows编码兼容
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加scripts目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_welcome_handler():
    """测试欢迎语处理器"""
    print("=== 测试欢迎语处理器 ===")
    
    try:
        from welcome_handler import WelcomeHandler
        handler = WelcomeHandler()
        
        print(f"欢迎语内容:\n{handler.get_welcome_message()}\n")
        print("快捷操作:")
        for btn in handler.get_quick_action_buttons():
            print(f"  {btn['label']}")
        print("\n✓ 欢迎语处理器测试通过\n")
        return True
    except Exception as e:
        print(f"✗ 欢迎语处理器测试失败: {e}\n")
        return False


def test_memory_system():
    """测试记忆系统"""
    print("=== 测试记忆系统 ===")
    
    try:
        from memory_system import MemorySystem
        ms = MemorySystem()
        
        # 测试创建会话
        test_id = "test_visitor_001"
        ms.create_session(test_id)
        
        # 更新会话
        ms.update_session(test_id, "星巴克在哪？")
        ms.update_context(test_id, 'current_topic', '商户位置查询')
        ms.add_merchant_mention(test_id, '星巴克')
        
        # 获取上下文
        context = ms.get_context_summary(test_id)
        print(f"上下文摘要: {context}\n")
        
        # 添加标签
        ms.add_tag(test_id, '兴趣偏好', '咖啡', 0.9)
        tags = ms.get_tags(test_id, '兴趣偏好')
        print(f"兴趣标签: {tags}\n")
        
        # 格式化上下文
        context_str = ms.format_context_for_ai(test_id)
        print(f"格式化上下文:\n{context_str}\n")
        
        print("✓ 记忆系统测试通过\n")
        return True
    except Exception as e:
        print(f"✗ 记忆系统测试失败: {e}\n")
        return False


def test_wechat_bot():
    """测试企业微信机器人"""
    print("=== 测试企业微信机器人 ===")
    
    try:
        # 测试解析消息
        test_xml = """<xml>
<ToUserName><![CDATA[gh_xxxxxxxx]]></ToUserName>
<FromUserName><![CDATA[test_user_001]]></FromUserName>
<CreateTime>1234567890</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[你好]]></Content>
<MsgId>1234567890123456</MsgId>
</xml>"""
        
        from wechat_bot import WeChatWorkBot
        bot = WeChatWorkBot()
        
        # 解析消息
        msg = bot.parse_message(test_xml)
        print(f"解析消息: {msg}\n")
        
        # 测试新会话回复
        response = bot.process_message("test_user_001", "你好")
        print(f"新会话回复:\n{response[:100]}...\n")
        
        print("✓ 企业微信机器人测试通过\n")
        return True
    except Exception as e:
        print(f"✗ 企业微信机器人测试失败: {e}\n")
        return False


def create_data_directories():
    """创建数据目录"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data')
    visitors_dir = os.path.join(data_dir, 'visitors')
    exports_dir = os.path.join(data_dir, 'exports')
    
    os.makedirs(visitors_dir, exist_ok=True)
    os.makedirs(exports_dir, exist_ok=True)
    
    print(f"✓ 创建数据目录: {data_dir}")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*50)
    print("  游客入口模块 - 功能测试")
    print("="*50 + "\n")
    
    create_data_directories()
    
    results = []
    
    # 运行测试
    results.append(("欢迎语处理器", test_welcome_handler()))
    results.append(("记忆系统", test_memory_system()))
    results.append(("企业微信机器人", test_wechat_bot()))
    
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
