# -*- coding: utf-8 -*-
"""
欢迎语处理模块
根据不同场景生成动态欢迎语
"""

import os
import yaml
from datetime import datetime, time

# 基础目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(os.path.dirname(BASE_DIR), 'config')


class WelcomeHandler:
    """欢迎语处理器"""
    
    def __init__(self, config_path=None):
        """初始化"""
        if config_path is None:
            config_path = os.path.join(CONFIG_DIR, 'welcome.md')
        
        self.config = self._load_config(config_path)
        self.base_welcome = self.config.get('welcome_message', '')
    
    def _load_config(self, config_path):
        """加载配置"""
        config = {
            'welcome_message': self._get_default_welcome(),
            'quick_actions': [],
            'frequent_questions': []
        }
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 简单解析markdown格式的welcome_message
                if 'welcome_message:' in content:
                    lines = content.split('\n')
                    in_message = False
                    message_lines = []
                    
                    for line in lines:
                        if line.strip() == 'welcome_message:':
                            in_message = True
                            continue
                        elif in_message:
                            if line.startswith('    ') or line.startswith('\t'):
                                message_lines.append(line.strip())
                            elif line.strip() == '':
                                continue
                            else:
                                break
                    
                    if message_lines:
                        config['welcome_message'] = '\n'.join(message_lines)
                
                # 解析quick_actions
                if 'quick_actions:' in content:
                    lines = content.split('\n')
                    in_actions = False
                    
                    for line in lines:
                        if line.strip() == 'quick_actions:':
                            in_actions = True
                            continue
                        if in_actions:
                            if line.strip().startswith('- label:'):
                                config['quick_actions'].append(line.strip())
                
                # 解析frequent_questions
                if 'frequent_questions:' in content:
                    lines = content.split('\n')
                    in_questions = False
                    
                    for line in lines:
                        if line.strip() == 'frequent_questions:':
                            in_questions = True
                            continue
                        if in_questions:
                            if line.strip().startswith('- "'):
                                question = line.strip()[2:-1]
                                config['frequent_questions'].append(question)
                                
            except Exception as e:
                print(f"加载配置失败: {e}")
        
        return config
    
    def _get_default_welcome(self):
        """获取默认欢迎语"""
        return """欢迎来到XX园区！我是您的智能导游。

您可以问我：
- 某商户怎么走？
- 今天有什么活动？
- 附近有什么餐厅？
- 领取商户优惠券

请直接输入您的问题，我会尽力帮助您！"""
    
    def get_welcome_message(self, user_id=None, context=None):
        """获取欢迎语"""
        # 获取时间相关的欢迎语
        time_greeting = self._get_time_greeting()
        
        # 组合欢迎语
        welcome = f"{time_greeting}\n\n{self.base_welcome}"
        
        # 添加快捷操作提示
        if self.config.get('quick_actions'):
            welcome += "\n\n💡 您也可以直接点击以下快捷操作："
        
        return welcome
    
    def _get_time_greeting(self):
        """根据时间获取问候语"""
        now = datetime.now()
        hour = now.hour
        
        if 5 <= hour < 9:
            return "🌅 早上好！"
        elif 9 <= hour < 12:
            return "☀️ 上午好！"
        elif 12 <= hour < 14:
            return "🌤️ 中午好！"
        elif 14 <= hour < 18:
            return "☀️ 下午好！"
        elif 18 <= hour < 22:
            return "🌆 晚上好！"
        else:
            return "🌙 夜深了！"
    
    def get_quick_action_buttons(self):
        """获取快捷操作按钮"""
        return [
            {"label": "🗺️ 园区地图", "action": "map"},
            {"label": "🎉 今日活动", "action": "events"},
            {"label": "🍜 餐饮推荐", "action": "dining"},
            {"label": "🎫 优惠券", "action": "coupons"}
        ]
    
    def get_frequent_questions(self):
        """获取常见问题"""
        return self.config.get('frequent_questions', [
            "星巴克在哪？",
            "今天有什么活动？",
            "附近有什么餐厅？",
            "有哪些优惠？"
        ])
    
    def get_followup_suggestion(self, last_message):
        """根据最后一条消息获取跟进建议"""
        suggestions = {
            "地图": "您可以输入商户名称查询具体位置，例如：'星巴克在哪'",
            "活动": "您可以点击上方快捷操作查看今日活动详情",
            "餐厅": "您可以告诉我您想吃什么类型的美食",
            "优惠": "您可以点击上方优惠券查看最新优惠"
        }
        
        for key, suggestion in suggestions.items():
            if key in last_message:
                return suggestion
        
        return "请问还有其他我可以帮您的吗？"


def generate_welcome_message(user_id=None, context=None):
    """生成欢迎语（便捷函数）"""
    handler = WelcomeHandler()
    return handler.get_welcome_message(user_id, context)


if __name__ == '__main__':
    # 测试
    handler = WelcomeHandler()
    print("=== 欢迎语测试 ===")
    print(handler.get_welcome_message())
    print("\n=== 快捷操作 ===")
    for btn in handler.get_quick_action_buttons():
        print(f"  {btn['label']}")
    print("\n=== 常见问题 ===")
    for q in handler.get_frequent_questions():
        print(f"  - {q}")
