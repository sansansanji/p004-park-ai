# -*- coding: utf-8 -*-
"""
多轮对话记忆系统模块
用于记住游客在对话中的上下文信息
"""

import os
import json
import yaml
from datetime import datetime
from collections import defaultdict

# 基础目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(os.path.dirname(BASE_DIR), 'config')


class MemorySystem:
    """多轮对话记忆系统"""
    
    def __init__(self, config_path=None):
        """初始化"""
        if config_path is None:
            config_path = os.path.join(CONFIG_DIR, 'memory.yaml')
        
        self.config = self._load_config(config_path)
        
        # 内存中的会话存储
        self.sessions = {}
        
        # 游客档案存储路径
        self.visitor_storage_path = os.path.join(
            os.path.dirname(BASE_DIR),
            'data/visitors'
        )
        
        # 确保目录存在
        os.makedirs(self.visitor_storage_path, exist_ok=True)
    
    def _load_config(self, config_path):
        """加载配置"""
        config = {
            'enabled': True,
            'session': {
                'timeout': 30,
                'max_turns': 20
            },
            'visitor_profile': {
                'auto_create': True,
                'storage_path': '/data/openclaw/memory/visitors'
            }
        }
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    loaded = yaml.safe_load(f)
                    if loaded:
                        config.update(loaded)
            except Exception as e:
                print(f"加载记忆配置失败: {e}")
        
        return config
    
    # ==================== 会话管理 ====================
    
    def create_session(self, visitor_id):
        """创建新会话"""
        self.sessions[visitor_id] = {
            'visitor_id': visitor_id,
            'start_time': datetime.now().isoformat(),
            'last_active': datetime.now().isoformat(),
            'turns': 0,
            'history': [],
            'context': {
                'mentioned_merchants': [],
                'mentioned_locations': [],
                'user_intent': None,
                'current_topic': None,
                'last_question': None
            }
        }
        
        # 加载历史档案
        profile = self.load_visitor_profile(visitor_id)
        if profile:
            self.sessions[visitor_id]['profile'] = profile
        
        return self.sessions[visitor_id]
    
    def get_session(self, visitor_id):
        """获取会话"""
        if visitor_id in self.sessions:
            return self.sessions[visitor_id]
        return None
    
    def is_session_expired(self, visitor_id):
        """检查会话是否过期"""
        if visitor_id not in self.sessions:
            return True
        
        last_active = datetime.fromisoformat(
            self.sessions[visitor_id]['last_active']
        )
        timeout_minutes = self.config.get('session', {}).get('timeout', 30)
        
        delta = datetime.now() - last_active
        return delta.total_seconds() > timeout_minutes * 60
    
    def update_session(self, visitor_id, message, response=None):
        """更新会话"""
        if visitor_id not in self.sessions:
            self.create_session(visitor_id)
        
        session = self.sessions[visitor_id]
        session['last_active'] = datetime.now().isoformat()
        session['turns'] += 1
        
        # 添加对话历史
        session['history'].append({
            'time': datetime.now().isoformat(),
            'user_message': message,
            'bot_response': response
        })
        
        # 限制历史长度
        max_turns = self.config.get('session', {}).get('max_turns', 20)
        if len(session['history']) > max_turns:
            session['history'] = session['history'][-max_turns:]
        
        # 自动标签：每条消息都触发第一层标签
        self._auto_tag_on_message(visitor_id, message)
    
    def clear_session(self, visitor_id):
        """清除会话"""
        if visitor_id in self.sessions:
            # 会话结束，自动标签
            self._auto_tag_on_session_end(visitor_id)
            
            # 保存会话信息到档案
            self._save_session_to_profile(visitor_id)
            del self.sessions[visitor_id]
    
    def _auto_tag_on_message(self, visitor_id, message):
        """自动标签：每条消息触发"""
        try:
            # 获取标签系统
            tagging_system = get_tagging_system()
            
            # 构建上下文
            context = {
                'visitor_id': visitor_id,
                'merchant_info': None
            }
            
            # 执行标签
            new_tags = tagging_system.process_message(message, context)
            
            if new_tags:
                # 获取现有标签
                existing_tags = self.get_tags(visitor_id)
                
                # 合并标签
                merged = tagging_system.merge_tags(existing_tags, new_tags)
                
                # 格式化并保存
                formatted = tagging_system.format_tags_for_profile(merged)
                
                # 更新档案
                profile = self.load_visitor_profile(visitor_id)
                if profile:
                    profile['auto_tags'] = formatted
                    profile['last_active'] = datetime.now().isoformat()
                    self.save_visitor_profile(visitor_id, profile)
                    
        except Exception as e:
            print(f"自动标签失败: {e}")
    
    def _auto_tag_on_session_end(self, visitor_id):
        """自动标签：会话结束触发（可扩展AI分析）"""
        # 这里可以添加第三层AI标签分析
        # 暂时保留为扩展接口
        pass
    
    # ==================== 上下文管理 ====================
    
    def update_context(self, visitor_id, key, value):
        """更新上下文"""
        if visitor_id not in self.sessions:
            self.create_session(visitor_id)
        
        self.sessions[visitor_id]['context'][key] = value
    
    def add_merchant_mention(self, visitor_id, merchant_name):
        """记录提到的商户"""
        if visitor_id not in self.sessions:
            self.create_session(visitor_id)
        
        merchants = self.sessions[visitor_id]['context'].get('mentioned_merchants', [])
        if merchant_name not in merchants:
            merchants.append(merchant_name)
            self.sessions[visitor_id]['context']['mentioned_merchants'] = merchants
    
    def set_user_intent(self, visitor_id, intent):
        """设置用户意图"""
        if visitor_id not in self.sessions:
            self.create_session(visitor_id)
        
        self.sessions[visitor_id]['context']['user_intent'] = intent
    
    def set_current_topic(self, visitor_id, topic):
        """设置当前话题"""
        if visitor_id not in self.sessions:
            self.create_session(visitor_id)
        
        self.sessions[visitor_id]['context']['current_topic'] = topic
    
    def get_context_summary(self, visitor_id):
        """获取上下文摘要"""
        if visitor_id not in self.sessions:
            return None
        
        session = self.sessions[visitor_id]
        context = session['context']
        
        summary = {
            'session_turns': session['turns'],
            'mentioned_merchants': context.get('mentioned_merchants', []),
            'current_topic': context.get('current_topic'),
            'user_intent': context.get('user_intent'),
            'last_question': context.get('last_question')
        }
        
        return summary
    
    # ==================== 游客档案管理 ====================
    
    def load_visitor_profile(self, visitor_id):
        """加载游客档案"""
        profile_path = os.path.join(
            self.visitor_storage_path,
            f'{visitor_id}.json'
        )
        
        if os.path.exists(profile_path):
            try:
                with open(profile_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载游客档案失败: {e}")
        
        return None
    
    def save_visitor_profile(self, visitor_id, profile):
        """保存游客档案"""
        profile_path = os.path.join(
            self.visitor_storage_path,
            f'{visitor_id}.json'
        )
        
        try:
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(profile, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存游客档案失败: {e}")
            return False
    
    def create_visitor_profile(self, visitor_id):
        """创建新游客档案"""
        profile = {
            'visitor_id': visitor_id,
            'first_visit': datetime.now().isoformat(),
            'last_active': datetime.now().isoformat(),
            'total_sessions': 1,
            'total_messages': 0,
            'auto_tags': {
                '兴趣偏好': [],
                '行为特征': [],
                '意向强度': [],
                '情感倾向': [],
                '消费能力': [],
                '出行目的': [],
                '特殊需求': []
            },
            'related_merchants': []
        }
        
        self.save_visitor_profile(visitor_id, profile)
        return profile
    
    def _save_session_to_profile(self, visitor_id):
        """将会话信息保存到档案"""
        if visitor_id not in self.sessions:
            return
        
        session = self.sessions[visitor_id]
        
        # 加载现有档案
        profile = self.load_visitor_profile(visitor_id)
        if not profile:
            profile = self.create_visitor_profile(visitor_id)
        
        # 更新档案
        profile['last_active'] = datetime.now().isoformat()
        profile['total_sessions'] = profile.get('total_sessions', 0) + 1
        profile['total_messages'] = profile.get('total_messages', 0) + session['turns']
        
        # 添加关联商户
        mentioned = session['context'].get('mentioned_merchants', [])
        existing_merchants = profile.get('related_merchants', [])
        for merchant in mentioned:
            if merchant not in existing_merchants:
                existing_merchants.append(merchant)
        profile['related_merchants'] = existing_merchants
        
        self.save_visitor_profile(visitor_id, profile)
    
    # ==================== 标签管理 ====================
    
    def add_tag(self, visitor_id, tag_category, tag, confidence=1.0):
        """添加标签"""
        profile = self.load_visitor_profile(visitor_id)
        if not profile:
            profile = self.create_visitor_profile(visitor_id)
        
        auto_tags = profile.get('auto_tags', {})
        if tag_category not in auto_tags:
            auto_tags[tag_category] = []
        
        # 检查是否已存在相同标签
        existing_tags = auto_tags[tag_category]
        for existing in existing_tags:
            if existing['tag'] == tag:
                existing['confidence'] = confidence
                break
        else:
            existing_tags.append({'tag': tag, 'confidence': confidence})
        
        profile['auto_tags'] = auto_tags
        self.save_visitor_profile(visitor_id, profile)
    
    def get_tags(self, visitor_id, category=None):
        """获取标签"""
        profile = self.load_visitor_profile(visitor_id)
        if not profile:
            return []
        
        auto_tags = profile.get('auto_tags', {})
        
        if category:
            return auto_tags.get(category, [])
        
        return auto_tags
    
    # ==================== 对话历史 ====================
    
    def get_conversation_history(self, visitor_id, last_n=None):
        """获取对话历史"""
        if visitor_id not in self.sessions:
            return []
        
        history = self.sessions[visitor_id]['history']
        
        if last_n:
            return history[-last_n:]
        
        return history
    
    def format_context_for_ai(self, visitor_id):
        """格式化上下文供AI使用"""
        context_summary = self.get_context_summary(visitor_id)
        profile = self.load_visitor_profile(visitor_id)
        history = self.get_conversation_history(visitor_id)
        
        # 构建上下文字符串
        context_parts = []
        
        # 基本信息
        if profile:
            context_parts.append(f"游客ID: {visitor_id}")
            context_parts.append(f"首次访问: {profile.get('first_visit', '未知')}")
            context_parts.append(f"会话次数: {profile.get('total_sessions', 1)}")
            
            # 标签
            tags = profile.get('auto_tags', {})
            if tags:
                context_parts.append("用户标签:")
                for category, tag_list in tags.items():
                    if tag_list:
                        tags_str = ', '.join([f"{t['tag']}({t['confidence']:.0%})" for t in tag_list])
                        context_parts.append(f"  {category}: {tags_str}")
        
        # 当前会话信息
        if context_summary:
            if context_summary.get('mentioned_merchants'):
                context_parts.append(
                    f"本次提到的商户: {', '.join(context_summary['mentioned_merchants'])}"
                )
            if context_summary.get('current_topic'):
                context_parts.append(f"当前话题: {context_summary['current_topic']}")
        
        # 最近对话
        if history:
            recent = history[-3:]
            context_parts.append("\n最近对话:")
            for h in recent:
                context_parts.append(f"  用户: {h['user_message']}")
                if h.get('bot_response'):
                    context_parts.append(f"  助手: {h['bot_response'][:50]}...")
        
        return '\n'.join(context_parts)


# 标签系统（延迟导入，避免循环依赖）
_tagging_system = None


def get_tagging_system():
    """获取标签系统实例"""
    global _tagging_system
    if _tagging_system is None:
        from tagging_system import TaggingSystem
        _tagging_system = TaggingSystem()
    return _tagging_system


# 全局实例
_memory_system = None


def get_memory_system():
    """获取记忆系统实例"""
    global _memory_system
    if _memory_system is None:
        _memory_system = MemorySystem()
    return _memory_system


if __name__ == '__main__':
    # 测试
    ms = MemorySystem()
    
    # 创建测试会话
    test_id = "test_visitor_001"
    ms.create_session(test_id)
    
    # 更新会话
    ms.update_session(test_id, "星巴克在哪？")
    ms.update_context(test_id, 'current_topic', '商户位置查询')
    ms.add_merchant_mention(test_id, '星巴克')
    
    # 获取上下文
    print("=== 上下文摘要 ===")
    print(ms.get_context_summary(test_id))
    
    # 添加标签
    ms.add_tag(test_id, '兴趣偏好', '咖啡', 0.9)
    
    print("\n=== 标签 ===")
    print(ms.get_tags(test_id))
    
    print("\n=== 格式化上下文 ===")
    print(ms.format_context_for_ai(test_id))
