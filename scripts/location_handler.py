# -*- coding: utf-8 -*-
"""
位置查询处理器
处理游客的位置查询、导航等请求
"""

import re
from merchant_db import get_merchant_database
from map_service import get_map_service


class LocationHandler:
    """位置查询处理器"""
    
    def __init__(self):
        """初始化"""
        self.merchant_db = get_merchant_database()
        self.map_service = get_map_service()
        
        # 位置查询关键词
        self.location_keywords = ['在哪', '位置', '怎么走', '导航', '去', '位置在哪']
        
        # 地图查询关键词
        self.map_keywords = ['地图', '查看地图']
    
    def can_handle(self, message):
        """判断是否可以处理此消息"""
        message = message.lower()
        
        # 检查是否是位置查询
        for keyword in self.location_keywords:
            if keyword in message:
                return True
        
        # 检查是否是商户名称（直接查询）
        merchants = self.merchant_db.get_all_merchants()
        for merchant in merchants:
            if merchant['name'] in message:
                return True
        
        return False
    
    def handle(self, message, visitor_id=None):
        """处理位置查询"""
        # 提取商户名称
        merchant_name = self._extract_merchant_name(message)
        
        if merchant_name:
            return self._handle_merchant_query(merchant_name, message)
        
        # 如果没有明确商户，尝试搜索
        return self._handle_search(message)
    
    def _extract_merchant_name(self, message):
        """从消息中提取商户名称"""
        # 获取所有商户名称
        merchants = self.merchant_db.get_all_merchants()
        
        # 精确匹配
        for merchant in merchants:
            if merchant['name'] in message:
                return merchant['name']
        
        # 模糊匹配
        keywords = ['星巴克', '肯德基', '麦当劳', '万达', '屈臣氏', 
                   '奈雪', '瑞幸', '优衣库', '小米']
        
        for keyword in keywords:
            if keyword in message:
                # 尝试找到完整名称
                for merchant in merchants:
                    if keyword in merchant['name']:
                        return merchant['name']
        
        return None
    
    def _handle_merchant_query(self, merchant_name, message):
        """处理商户查询"""
        merchant = self.merchant_db.get_merchant(merchant_name)
        
        if not merchant:
            return f"抱歉，未找到关于 {merchant_name} 的信息"
        
        # 检查是否询问优惠
        if '优惠' in message or '便宜' in message or '打折' in message:
            return self._handle_promotion_query(merchant_name)
        
        # 返回位置信息
        return self.map_service.build_navigation_reply(merchant_name, merchant)
    
    def _handle_promotion_query(self, merchant_name=None):
        """处理优惠查询"""
        if merchant_name:
            # 查询特定商户优惠
            merchant = self.merchant_db.get_merchant(merchant_name)
            if merchant and merchant.get('promotion'):
                return f"🎫 **{merchant_name}** 当前优惠：\n{merchant['promotion']}"
            else:
                return f"抱歉，{merchant_name} 当前没有优惠活动"
        
        # 查询所有优惠
        all_merchants = self.merchant_db.get_all_merchants()
        promotions = []
        
        for m in all_merchants:
            if m.get('promotion'):
                promotions.append(f"- {m['name']}: {m['promotion']}")
        
        if promotions:
            reply = "🎫 **当前优惠活动：**\n\n" + '\n'.join(promotions)
            return reply
        else:
            return "抱歉，当前没有优惠活动"
    
    def _handle_search(self, message):
        """处理搜索请求"""
        # 检查是否是优惠查询
        if '优惠' in message or '打折' in message:
            return self._handle_promotion_query()
        
        # 检查是否是特定类型查询
        if '餐厅' in message or '吃饭' in message or '美食' in message:
            return self._handle_type_query('餐饮')
        
        if '电影' in message:
            return self._handle_type_query('娱乐')
        
        if '购物' in message or '商店' in message:
            return self._handle_type_query('购物')
        
        # 通用搜索
        keyword = message.replace('在哪', '').replace('怎么走', '').replace('位置', '').strip()
        
        if keyword:
            results = self.merchant_db.search_merchants(keyword)
            if results:
                return self._format_search_results(results, keyword)
        
        return "抱歉，我不太明白您的意思。请告诉我您想去的商户名称，例如：'星巴克在哪？'"
    
    def _handle_type_query(self, merchant_type):
        """按类型查询商户"""
        merchants = self.merchant_db.get_merchants_by_type(merchant_type)
        
        if not merchants:
            return f"抱歉，暂无 {merchant_type} 类型的商户"
        
        type_names = {
            '餐饮': '餐厅',
            '娱乐': '娱乐场所',
            '购物': '商店'
        }
        
        reply = f"📋 **{type_names.get(merchant_type, merchant_type)}列表：**\n\n"
        
        for m in merchants:
            reply += f"• **{m['name']}** - {m['location']}"
            if m.get('promotion'):
                reply += f" 🎫{m['promotion']}"
            reply += "\n"
        
        reply += "\n您可以输入商户名称查询具体位置"
        
        return reply
    
    def _format_search_results(self, results, keyword):
        """格式化搜索结果"""
        if not results:
            return f"未找到与 '{keyword}' 相关的商户"
        
        reply = f"🔍 搜索 '{keyword}' 结果：\n\n"
        
        for m in results[:5]:  # 最多显示5个
            reply += f"• **{m['name']}** - {m['location']}\n"
        
        if len(results) > 5:
            reply += f"\n...还有 {len(results) - 5} 个结果"
        
        return reply
    
    def get_welcome_with_merchants(self):
        """获取带商户列表的欢迎语"""
        merchants = self.merchant_db.get_all_merchants()
        
        if not merchants:
            return None
        
        # 按类型分组
        type_groups = {}
        for m in merchants:
            mtype = m.get('type', '其他')
            if mtype not in type_groups:
                type_groups[mtype] = []
            type_groups[mtype].append(m)
        
        reply = "🏪 **园区商户列表：**\n\n"
        
        for mtype, mlist in type_groups.items():
            type_names = {
                '餐饮': '🍜 餐饮',
                '娱乐': '🎬 娱乐',
                '购物': '🛍️ 购物'
            }
            reply += f"**{type_names.get(mtype, mtype)}：**\n"
            
            for m in mlist[:3]:  # 每类最多显示3个
                reply += f"  • {m['name']} ({m['location']})\n"
            
            reply += "\n"
        
        reply += "请告诉我您想去的商户，我会帮您导航～"
        
        return reply


# 全局实例
_location_handler = None


def get_location_handler():
    """获取位置处理器实例"""
    global _location_handler
    if _location_handler is None:
        _location_handler = LocationHandler()
    return _location_handler


def handle_location_query(message, visitor_id=None):
    """便捷函数：处理位置查询"""
    handler = get_location_handler()
    if handler.can_handle(message):
        return handler.handle(message, visitor_id)
    return None


if __name__ == '__main__':
    # 测试
    handler = LocationHandler()
    
    print("=== 位置查询处理器测试 ===\n")
    
    test_messages = [
        "星巴克在哪？",
        "肯德基怎么走？",
        "我想吃饭",
        "有什么优惠？",
        "星巴克有优惠吗？"
    ]
    
    for msg in test_messages:
        if handler.can_handle(msg):
            result = handler.handle(msg)
            print(f"Q: {msg}")
            print(f"A: {result}")
            print("-" * 40)
