# -*- coding: utf-8 -*-
"""
三层标签体系核心模块
用于自动为游客打标签

- 第一层：预设规则标签（关键词匹配）
- 第二层：知识库增强标签（从商户信息提取）
- 第三层：AI智能分析标签（大模型分析）
"""

import os
import json
import yaml
import re
from datetime import datetime

# 基础目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(os.path.dirname(BASE_DIR), 'config')


class TaggingSystem:
    """三层标签体系"""
    
    def __init__(self, config_path=None):
        """初始化"""
        if config_path is None:
            config_path = os.path.join(CONFIG_DIR, 'system.yaml')
        
        self.config = self._load_config(config_path)
        
        # 标签配置
        self.tags_config = self.config.get('tags', {})
        
        # 三层标签配置
        self.layer_1_config = self.tags_config.get('layer_1_preset', {})
        self.layer_2_config = self.tags_config.get('layer_2_knowledge', {})
        self.layer_3_config = self.tags_config.get('layer_3_ai', {})
    
    def _load_config(self, config_path):
        """加载配置"""
        config = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
            except Exception as e:
                print(f"加载配置失败: {e}")
        return config
    
    # ==================== 第一层：预设规则标签 ====================
    
    def layer1_preset_tagging(self, message, context=None):
        """
        第一层：预设规则标签
        基于关键词匹配进行打标签
        """
        if not self.layer_1_config.get('enabled', True):
            return []
        
        tags = []
        confidence = self.layer_1_config.get('confidence', 0.9)
        categories = self.layer_1_config.get('categories', {})
        
        for category_name, category_rules in categories.items():
            for rule in category_rules:
                tag = rule.get('tag', '')
                keywords = rule.get('keywords', [])
                
                # 检查是否包含关键词
                for keyword in keywords:
                    if keyword in message:
                        tags.append({
                            'layer': 1,
                            'category': category_name,
                            'tag': tag,
                            'confidence': confidence,
                            'matched_keyword': keyword
                        })
                        break  # 一个标签只添加一次
        
        return tags
    
    # ==================== 第二层：知识库增强标签 ====================
    
    def layer2_knowledge_tagging(self, message, merchant_info=None):
        """
        第二层：知识库增强标签
        从商户信息中提取标签——根据用户提到的商户类型打标签
        """
        if not self.layer_2_config.get('enabled', True):
            return []

        tags = []
        confidence = self.layer_2_config.get('confidence', 0.85)

        # 如果没有提供商户信息，从消息中提取商户名称
        if merchant_info is None:
            merchant_info = self._extract_merchant_from_message(message)

        # 根据商户类型打标签
        if merchant_info:
            # 方式1：直接用商户的category打标签（来自CSV的"类型"字段）
            merchant_category = merchant_info.get('category', '')
            if merchant_category:
                tags.append({
                    'layer': 2,
                    'category': '商户类型',
                    'tag': merchant_category,
                    'confidence': confidence,
                    'matched_merchant': merchant_info.get('name', ''),
                    'source': 'merchant_category'
                })

            # 方式2：用配置文件里的 merchant_keywords 规则（补充匹配）
            categories = self.layer_2_config.get('categories', {})
            merchant_name = merchant_info.get('name', '')
            for category_name, category_rules in categories.items():
                for rule in category_rules:
                    tag = rule.get('tag', '')
                    merchant_keywords = rule.get('merchant_keywords', [])

                    # 检查商户名是否匹配关键词
                    for keyword in merchant_keywords:
                        if keyword in merchant_name:
                            # 避免跟方式1重复打标签
                            if not any(t['tag'] == tag for t in tags):
                                tags.append({
                                    'layer': 2,
                                    'category': category_name,
                                    'tag': tag,
                                    'confidence': confidence,
                                    'matched_merchant': merchant_name,
                                    'source': 'keyword_rule'
                                })
                            break

        return tags
    
    def _extract_merchant_from_message(self, message):
        """从消息中提取商户信息：匹配商户名称和别名"""
        merchants = self._load_merchants()
        if not merchants:
            return None

        for m in merchants:
            name = m.get('name', '')
            # 商户名在消息中出现
            if name and name in message:
                return {
                    'name': name,
                    'category': m.get('category', ''),
                    'floor': m.get('floor', ''),
                }

        # 别名匹配（常见简称/昵称）
        alias_map = self._get_merchant_aliases()
        for alias, merchant_name in alias_map.items():
            if alias in message:
                # 找到对应商户
                for m in merchants:
                    if m.get('name') == merchant_name:
                        return {
                            'name': merchant_name,
                            'category': m.get('category', ''),
                            'floor': m.get('floor', ''),
                        }
        return None

    def _load_merchants(self):
        """加载商户列表（CSV或数据库）"""
        if hasattr(self, '_merchants_cache'):
            return self._merchants_cache

        merchants = []

        # 方式1：从CSV加载
        csv_path = os.path.join(os.path.dirname(BASE_DIR), 'data', 'merchants_sample.csv')
        if os.path.exists(csv_path):
            try:
                import csv
                with open(csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        name = row.get('商户名称', '').strip()
                        if not name:
                            continue
                        merchants.append({
                            'name': name,
                            'category': row.get('类型', '').strip(),
                            'floor': row.get('楼层', '').strip(),
                            'location': row.get('位置描述', '').strip(),
                        })
            except Exception as e:
                print(f"[标签] 加载商户CSV失败: {e}")

        # 方式2：从数据库加载（如果有的话）
        if not merchants:
            try:
                from db_manager import MemberDAO
                dao = MemberDAO()
                rows = dao.query("SELECT name, category FROM merchants WHERE status = 1")
                if rows:
                    merchants = [{'name': r['name'], 'category': r.get('category', '')} for r in rows]
            except Exception:
                pass

        self._merchants_cache = merchants
        return merchants

    def _get_merchant_aliases(self):
        """商户别名映射（简称→全称）"""
        # 常见简称/昵称→商户全称
        return {
            '星巴克': '星巴克',
            'KFC': '肯德基',
            '肯德基': '肯德基',
            '海底捞': '海底捞',
            '奈雪': '奈雪的茶',
            '瑞幸': '瑞幸咖啡',
            '优衣库': '优衣库',
            '屈臣氏': '屈臣氏',
            'ZARA': 'ZARA',
            '名创': '名创优品',
            '小米': '小米之家',
            '华为': '华为体验店',
            '万达': '万达影城',
            '电影院': '万达影城',
            '影城': '万达影城',
        }
    
    # ==================== 第三层：AI智能分析标签 ====================
    
    def layer3_ai_tagging(self, message, conversation_history=None, visitor_profile=None):
        """
        第三层：AI智能分析标签
        需要调用大模型进行分析
        
        注意：这里只是接口预留，实际调用需要接入OpenClaw
        """
        if not self.layer_3_config.get('enabled', True):
            return []
        
        # 构造Prompt
        prompt = self._build_ai_tagging_prompt(message, conversation_history, visitor_profile)
        
        # TODO: 调用OpenClaw进行AI分析
        # 暂时返回空列表，后续接入大模型后完善
        # 
        # 模拟返回（开发测试用）
        # return self._simulate_ai_tagging(message)
        
        return []
    
    def _build_ai_tagging_prompt(self, message, conversation_history, visitor_profile):
        """构建AI标签分析的Prompt"""
        prompt_parts = [
            "你是一个用户行为分析专家。请分析以下游客的消息，为他打上合适的标签。",
            f"\n游客消息: {message}"
        ]
        
        if conversation_history:
            prompt_parts.append(f"\n对话历史: {conversation_history}")
        
        if visitor_profile:
            prompt_parts.append(f"\n游客档案: {visitor_profile}")
        
        prompt_parts.append("\n请从以下维度分析并返回JSON格式的标签：")
        prompt_parts.append("1. 情感倾向：正面/中性/负面")
        prompt_parts.append("2. 消费能力：高/中/低")
        prompt_parts.append("3. 出行目的：家庭出游/朋友聚会/商务接待/个人休闲")
        prompt_parts.append("4. 特殊需求：无障碍需求/婴儿车/宠物友好/素食/清真")
        
        prompt_parts.append("\n返回格式：")
        prompt_parts.append("""
{
  "情感倾向": {"tag": "正面", "confidence": 0.85},
  "消费能力": {"tag": "中", "confidence": 0.70},
  "出行目的": {"tag": "家庭出游", "confidence": 0.90},
  "特殊需求": []
}
""")
        
        return '\n'.join(prompt_parts)
    
    def _simulate_ai_tagging(self, message):
        """模拟AI标签（开发测试用）"""
        tags = []
        message_lower = message.lower()
        
        # 情感倾向分析（简单规则）
        positive_words = ['好', '棒', '喜欢', '谢谢', '开心', '满意']
        negative_words = ['差', '烂', '垃圾', '生气', '不满', '失望']
        
        for word in positive_words:
            if word in message:
                tags.append({
                    'layer': 3,
                    'category': '情感倾向',
                    'tag': '正面',
                    'confidence': 0.8,
                    'matched_word': word
                })
                break
        
        for word in negative_words:
            if word in message:
                tags.append({
                    'layer': 3,
                    'category': '情感倾向',
                    'tag': '负面',
                    'confidence': 0.8,
                    'matched_word': word
                })
                break
        
        # 出行目的分析
        if any(w in message for w in ['孩子', '家人', '亲子']):
            tags.append({
                'layer': 3,
                'category': '出行目的',
                'tag': '家庭出游',
                'confidence': 0.75
            })
        
        return tags
    
    # ==================== 统一标签接口 ====================
    
    def process_message(self, message, context=None):
        """
        处理消息，返回所有三层标签
        """
        all_tags = []
        
        # 获取商户信息
        merchant_info = context.get('merchant_info') if context else None
        
        # 第一层：预设规则标签
        layer1_tags = self.layer1_preset_tagging(message, context)
        all_tags.extend(layer1_tags)
        
        # 第二层：知识库增强标签
        layer2_tags = self.layer2_knowledge_tagging(message, merchant_info)
        all_tags.extend(layer2_tags)
        
        # 第三层：AI智能分析标签（需要历史记录）
        if context and context.get('visitor_id'):
            visitor_id = context.get('visitor_id')
            from memory_system import get_memory_system
            ms = get_memory_system()
            
            history = ms.get_conversation_history(visitor_id, last_n=5)
            profile = ms.load_visitor_profile(visitor_id)
            
            layer3_tags = self.layer3_ai_tagging(message, history, profile)
            all_tags.extend(layer3_tags)
        
        return all_tags
    
    def merge_tags(self, existing_tags, new_tags):
        """
        合并新旧标签，保留高置信度的标签
        """
        merged = {}
        
        # 先添加已有标签
        for tag_info in existing_tags:
            key = f"{tag_info.get('category')}_{tag_info.get('tag')}"
            merged[key] = tag_info
        
        # 添加新标签（如果有更高置信度则覆盖）
        for tag_info in new_tags:
            key = f"{tag_info.get('category')}_{tag_info.get('tag')}"
            if key not in merged:
                merged[key] = tag_info
            else:
                # 如果新标签置信度更高，则覆盖
                if tag_info.get('confidence', 0) > merged[key].get('confidence', 0):
                    merged[key] = tag_info
        
        return list(merged.values())
    
    def format_tags_for_profile(self, tags):
        """
        格式化标签为游客档案格式
        """
        formatted = {}
        
        for tag_info in tags:
            category = tag_info.get('category', '其他')
            tag = tag_info.get('tag', '')
            confidence = tag_info.get('confidence', 0.5)
            
            if category not in formatted:
                formatted[category] = []
            
            # 检查是否已存在相同标签
            existing = formatted[category]
            for i, existing_tag in enumerate(existing):
                if existing_tag['tag'] == tag:
                    # 更新置信度
                    if confidence > existing_tag['confidence']:
                        existing[i]['confidence'] = confidence
                    break
            else:
                # 添加新标签
                formatted[category].append({
                    'tag': tag,
                    'confidence': confidence
                })
        
        return formatted


# 全局实例
_tagging_system = None


def get_tagging_system():
    """获取标签系统实例"""
    global _tagging_system
    if _tagging_system is None:
        _tagging_system = TaggingSystem()
    return _tagging_system


def tag_message(message, context=None):
    """
    便捷函数：对消息进行标签处理
    """
    system = get_tagging_system()
    return system.process_message(message, context)


if __name__ == '__main__':
    # 测试
    system = TaggingSystem()
    
    print("=== 三层标签体系测试 ===\n")
    
    # 测试消息
    test_messages = [
        "我想找个餐厅吃饭，孩子饿 了",
        "有没有便宜点的优惠？",
        "星巴克在哪？",
        "谢谢你们，服务很棒！"
    ]
    
    for msg in test_messages:
        print(f"消息: {msg}")
        
        # 第一层标签
        layer1 = system.layer1_preset_tagging(msg)
        print(f"第一层标签: {layer1}")
        
        # 第二层标签
        layer2 = system.layer2_knowledge_tagging(msg)
        print(f"第二层标签: {layer2}")
        
        # 合并标签
        all_tags = layer1 + layer2
        formatted = system.format_tags_for_profile(all_tags)
        print(f"格式化标签: {formatted}")
        print("-" * 50)
