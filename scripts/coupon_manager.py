# -*- coding: utf-8 -*-
"""
优惠券与购买模块
处理优惠信息展示、购买链接、点击跟踪
"""

import os
import json
import yaml
from datetime import datetime

# 基础目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), 'data')
CONFIG_DIR = os.path.join(os.path.dirname(BASE_DIR), 'config')


class CouponManager:
    """优惠券管理器"""
    
    def __init__(self):
        """初始化"""
        # 加载商户数据库
        from merchant_db import get_merchant_database
        self.merchant_db = get_merchant_database()
        
        # 加载购买链接配置
        self.purchase_links = self._load_purchase_links()
    
    def _load_purchase_links(self):
        """加载购买链接配置"""
        config_path = os.path.join(CONFIG_DIR, 'purchase_links.yaml')
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                print(f"加载购买链接失败: {e}")
        
        return {}
    
    def get_coupon(self, merchant_name):
        """获取商户的优惠券信息"""
        merchant = self.merchant_db.get_merchant(merchant_name)
        
        if not merchant:
            return None
        
        promotion = merchant.get('promotion', '').strip()
        if not promotion:
            return None
        
        # 获取购买链接
        purchase_link = self.purchase_links.get(merchant_name, {}).get('link', '')
        
        coupon = {
            'merchant_name': merchant_name,
            'promotion': promotion,
            'purchase_link': purchase_link,
            'location': merchant.get('location', '')
        }
        
        return coupon
    
    def get_all_coupons(self):
        """获取所有优惠券"""
        merchants = self.merchant_db.get_all_merchants()
        coupons = []
        
        for merchant in merchants:
            promotion = merchant.get('promotion', '').strip()
            if promotion:
                merchant_name = merchant['name']
                purchase_link = self.purchase_links.get(merchant_name, {}).get('link', '')
                
                coupons.append({
                    'merchant_name': merchant_name,
                    'promotion': promotion,
                    'purchase_link': purchase_link,
                    'location': merchant.get('location', ''),
                    'type': merchant.get('type', '')
                })
        
        return coupons
    
    def get_coupons_by_type(self, merchant_type):
        """按类型获取优惠券"""
        merchants = self.merchant_db.get_merchants_by_type(merchant_type)
        coupons = []
        
        for merchant in merchants:
            promotion = merchant.get('promotion', '').strip()
            if promotion:
                merchant_name = merchant['name']
                purchase_link = self.purchase_links.get(merchant_name, {}).get('link', '')
                
                coupons.append({
                    'merchant_name': merchant_name,
                    'promotion': promotion,
                    'purchase_link': purchase_link,
                    'location': merchant.get('location', '')
                })
        
        return coupons
    
    def format_coupon_reply(self, merchant_name):
        """格式化优惠券回复"""
        coupon = self.get_coupon(merchant_name)
        
        if not coupon:
            return None
        
        reply = f"🎫 **{merchant_name}** 优惠\n"
        reply += f"   {coupon['promotion']}\n"
        
        if coupon['purchase_link']:
            reply += f"\n[点击领取]({coupon['purchase_link']})"
        
        return reply
    
    def format_all_coupons_reply(self):
        """格式化所有优惠券回复"""
        coupons = self.get_all_coupons()
        
        if not coupons:
            return "抱歉，当前没有优惠活动"
        
        # 按类型分组
        type_groups = {}
        for coupon in coupons:
            ctype = coupon.get('type', '其他')
            if ctype not in type_groups:
                type_groups[ctype] = []
            type_groups[ctype].append(coupon)
        
        reply = "🎫 **当前优惠活动**\n\n"
        
        for ctype, clist in type_groups.items():
            type_names = {
                '餐饮': '🍜 餐饮',
                '娱乐': '🎬 娱乐',
                '购物': '🛍️ 购物'
            }
            reply += f"**{type_names.get(ctype, ctype)}：**\n"
            
            for c in clist:
                reply += f"• **{c['merchant_name']}**: {c['promotion']}"
                if c['purchase_link']:
                    reply += f" [领取]({c['purchase_link']})"
                reply += "\n"
            
            reply += "\n"
        
        return reply
    
    def format_type_coupons_reply(self, merchant_type):
        """格式化特定类型优惠券"""
        coupons = self.get_coupons_by_type(merchant_type)
        
        if not coupons:
            type_names = {
                '餐饮': '餐饮',
                '娱乐': '娱乐',
                '购物': '购物'
            }
            return f"抱歉，暂无{type_names.get(merchant_type, merchant_type)}类优惠"
        
        type_names = {
            '餐饮': '🍜 餐饮优惠',
            '娱乐': '🎬 娱乐优惠',
            '购物': '🛍️ 购物优惠'
        }
        
        reply = f"🎫 **{type_names.get(merchant_type, merchant_type)}**\n\n"
        
        for c in coupons:
            reply += f"• **{c['merchant_name']}**: {c['promotion']}"
            if c['purchase_link']:
                reply += f" [领取]({c['purchase_link']})"
            reply += "\n"
        
        return reply


class ClickTracker:
    """点击跟踪器"""
    
    def __init__(self):
        """初始化"""
        self.data_path = os.path.join(DATA_DIR, 'clicks')
        os.makedirs(self.data_path, exist_ok=True)
    
    def track_click(self, visitor_id, merchant_name, coupon_promotion):
        """记录点击"""
        click_record = {
            'visitor_id': visitor_id,
            'merchant_name': merchant_name,
            'coupon_promotion': coupon_promotion,
            'click_time': datetime.now().isoformat()
        }
        
        # 保存到文件
        filename = f"{visitor_id}_{datetime.now().strftime('%Y%m%d')}.json"
        filepath = os.path.join(self.data_path, filename)
        
        # 读取现有记录
        clicks = []
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    clicks = json.load(f)
            except:
                clicks = []
        
        clicks.append(click_record)
        
        # 保存
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(clicks, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存点击记录失败: {e}")
            return False
    
    def get_click_stats(self, visitor_id=None, date=None):
        """获取点击统计"""
        if not date:
            date = datetime.now().strftime('%Y%m%d')
        
        if visitor_id:
            filename = f"{visitor_id}_{date}.json"
            filepath = os.path.join(self.data_path, filename)
            
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except:
                    return []
            return []
        
        # 获取所有点击
        all_clicks = []
        for filename in os.listdir(self.data_path):
            if filename.endswith('.json'):
                filepath = os.path.join(self.data_path, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        all_clicks.extend(json.load(f))
                except:
                    pass
        
        return all_clicks


# 全局实例
_coupon_manager = None
_click_tracker = None


def get_coupon_manager():
    """获取优惠券管理器实例"""
    global _coupon_manager
    if _coupon_manager is None:
        _coupon_manager = CouponManager()
    return _coupon_manager


def get_click_tracker():
    """获取点击跟踪器实例"""
    global _click_tracker
    if _click_tracker is None:
        _click_tracker = ClickTracker()
    return _click_tracker


def handle_coupon_query(message):
    """便捷函数：处理优惠券查询"""
    manager = get_coupon_manager()
    
    # 提取商户名称
    merchants = manager.merchant_db.get_all_merchants()
    merchant_name = None
    
    for merchant in merchants:
        if merchant['name'] in message:
            merchant_name = merchant['name']
            break
    
    if merchant_name:
        # 查询特定商户优惠
        return manager.format_coupon_reply(merchant_name)
    
    # 查询所有优惠
    return manager.format_all_coupons_reply()


if __name__ == '__main__':
    # 测试
    manager = get_coupon_manager()
    
    print("=== 优惠券管理测试 ===\n")
    
    # 测试获取单个优惠
    coupon = manager.get_coupon("星巴克")
    print(f"星巴克优惠: {coupon}")
    
    # 测试获取所有优惠
    coupons = manager.get_all_coupons()
    print(f"\n优惠券总数: {len(coupons)}")
    for c in coupons:
        print(f"  - {c['merchant_name']}: {c['promotion']}")
    
    # 测试格式化回复
    print("\n=== 格式化回复测试 ===")
    print(manager.format_all_coupons_reply())
