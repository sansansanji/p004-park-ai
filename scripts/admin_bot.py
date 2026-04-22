# -*- coding: utf-8 -*-
"""
管理者机器人
面向园区管理方的数据查询和管理功能
"""

import os
import json
import yaml
import hashlib
import time
from datetime import datetime, timedelta
from xml.etree import ElementTree

# 基础目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(os.path.dirname(BASE_DIR), 'config')


class AdminBot:
    """管理者机器人"""
    
    def __init__(self, config_path=None):
        """初始化"""
        if config_path is None:
            config_path = os.path.join(CONFIG_DIR, 'admin_wechat.yaml')
        
        # 加载配置
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = {}
        
        # 加载数据存储
        from data_storage import get_data_storage
        self.storage = get_data_storage()
        
        # 加载数据导出
        from data_exporter import get_data_exporter
        self.exporter = get_data_exporter()
        
        # 加载商户数据
        from merchant_db import get_merchant_database
        self.merchant_db = get_merchant_database()
    
    def verify_callback(self, signature, timestamp, nonce, echostr):
        """验证回调URL"""
        token = self.config.get('wechat_work', {}).get('callback', {}).get('token', '')
        tmp_list = sorted([token, timestamp, nonce])
        tmp_str = ''.join(tmp_list)
        calc_signature = hashlib.sha1(tmp_str.encode('utf-8')).hexdigest()
        
        if calc_signature == signature:
            return echostr
        return None
    
    def parse_message(self, xml_data):
        """解析消息"""
        try:
            root = ElementTree.fromstring(xml_data)
            msg = {
                'msg_type': root.find('MsgType').text,
                'from_user': root.find('FromUserName').text,
                'create_time': root.find('CreateTime').text,
                'content': root.find('Content').text if root.find('Content') is not None else '',
                'msg_id': root.find('MsgId').text if root.find('MsgId') is not None else '',
            }
            return msg
        except Exception as e:
            print(f"解析消息失败: {e}")
            return None
    
    def create_response(self, to_user, content, msg_type='text'):
        """创建回复"""
        response = f"""<xml>
<ToUserName><![CDATA[{to_user}]]></ToUserName>
<FromUserName><![CDATA[gh_xxxxxxxx]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[{msg_type}]]></MsgType>
<Content><![CDATA[{content}]]></Content>
</xml>"""
        return response
    
    def process_message(self, user_id, content):
        """处理管理消息"""
        content = content.strip()
        
        # 检查是否是管理员
        if not self._is_admin(user_id):
            return "抱歉，您没有管理员权限"
        
        # 解析命令
        return self._handle_command(content)
    
    def _is_admin(self, user_id):
        """检查是否是管理员"""
        admin_users = self.config.get('admin_users', [])
        
        # 如果没有配置，允许所有用户（测试模式）
        if not admin_users:
            return True
        
        return user_id in admin_users
    
    def _handle_command(self, content):
        """处理命令"""
        # 帮助命令
        if content in ['帮助', 'help', '?']:
            return self._get_help()
        
        # 数据统计
        if content in ['统计', '数据', 'dashboard']:
            return self._get_statistics()
        
        # 游客列表
        if content in ['游客', '访客', '游客列表']:
            return self._get_visitor_list()
        
        # 商户数据
        if content in ['商户', '商家', '商户列表']:
            return self._get_merchant_list()
        
        # 导出数据
        if content in ['导出', '下载', 'export']:
            return self._export_data()
        
        # 今日数据
        if content in ['今日', 'today']:
            return self._get_today_data()
        
        # 定时发送报告（手动触发）
        if content in ['报告', '日报', 'report']:
            return self._send_daily_report()
        
        # 未知命令
        return f"未知命令：{content}\n\n" + self._get_help()
    
    def _get_help(self):
        """获取帮助信息"""
        return """📊 **管理者命令帮助**

可用命令：
• 统计/dashboard - 查看数据统计
• 游客 - 查看游客列表
• 商户 - 查看商户列表
• 今日/today - 今日数据
• 导出/export - 导出数据
• 报告/report - 发送日报
• 帮助/help - 显示帮助

如需自动接收日报，请配置定时任务
"""
    
    def _get_statistics(self):
        """获取统计数据"""
        summary = self.storage.get_summary()
        
        # 获取游客标签统计
        visitors = self.storage.get_all_visitors()
        
        # 统计标签
        tag_stats = {
            '兴趣偏好': {},
            '行为特征': {},
            '意向强度': {},
        }
        
        for v in visitors:
            tags = v.get('auto_tags', {})
            for category, tag_list in tags.items():
                if category not in tag_stats:
                    continue
                for t in tag_list:
                    tag_name = t.get('tag', '')
                    if tag_name:
                        tag_stats[category][tag_name] = tag_stats[category].get(tag_name, 0) + 1
        
        reply = "📊 **数据统计**\n\n"
        reply += f"👥 游客总数: {summary.get('total_visitors', 0)}\n"
        reply += f"📁 导出文件: {summary.get('export_files', 0)}\n"
        reply += f"🕐 更新时间: {summary.get('last_updated', '')}\n\n"
        
        # 标签统计
        reply += "🏷️ **热门标签**\n"
        for category, tags in tag_stats.items():
            if tags:
                sorted_tags = sorted(tags.items(), key=lambda x: x[1], reverse=True)[:3]
                reply += f"\n{category}:\n"
                for tag, count in sorted_tags:
                    reply += f"  • {tag}: {count}\n"
        
        return reply
    
    def _get_visitor_list(self):
        """获取游客列表"""
        visitors = self.storage.get_all_visitors()
        
        if not visitors:
            return "暂无游客数据"
        
        reply = "👥 **游客列表**\n\n"
        
        # 显示最近5个
        sorted_visitors = sorted(
            visitors, 
            key=lambda x: x.get('last_active', ''), 
            reverse=True
        )[:5]
        
        for v in sorted_visitors:
            visitor_id = v.get('visitor_id', '')[:8] + '...'
            last_active = v.get('last_active', '')[:10]
            sessions = v.get('total_sessions', 0)
            
            # 兴趣标签
            tags = v.get('auto_tags', {})
            interest_tags = tags.get('兴趣偏好', [])
            interest = interest_tags[0].get('tag', '-') if interest_tags else '-'
            
            reply += f"• {visitor_id} | 访问{sessions}次 | 兴趣:{interest} | {last_active}\n"
        
        if len(visitors) > 5:
            reply += f"\n...还有 {len(visitors) - 5} 位游客"
        
        return reply
    
    def _get_merchant_list(self):
        """获取商户列表"""
        merchants = self.merchant_db.get_all_merchants()
        
        if not merchants:
            return "暂无商户数据"
        
        # 按类型分组
        type_groups = {}
        for m in merchants:
            mtype = m.get('type', '其他')
            if mtype not in type_groups:
                type_groups[mtype] = []
            type_groups[mtype].append(m)
        
        reply = "🏪 **商户列表**\n\n"
        
        for mtype, mlist in type_groups.items():
            reply += f"**{mtype}** ({len(mlist)}家)\n"
            for m in mlist[:3]:
                reply += f"  • {m['name']} - {m['location']}\n"
            if len(mlist) > 3:
                reply += f"  ...还有{len(mlist)-3}家\n"
            reply += "\n"
        
        return reply
    
    def _export_data(self):
        """导出数据"""
        try:
            # 导出游客数据
            visitor_file = self.exporter.export_visitors()
            merchant_file = self.exporter.export_merchants()
            
            return f"""📁 **数据导出完成**

游客数据: {visitor_file}
商户数据: {merchant_file}

文件保存在服务器上，请通过FTP或管理后台下载
"""
        except Exception as e:
            return f"导出失败: {str(e)}"
    
    def _get_today_data(self):
        """获取今日数据"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        visitors = self.storage.get_all_visitors()
        
        # 统计今日活跃游客
        today_visitors = []
        for v in visitors:
            last_active = v.get('last_active', '')
            if today in last_active:
                today_visitors.append(v)
        
        reply = f"📅 **今日数据 ({today})**\n\n"
        reply += f"👥 今日访客: {len(today_visitors)}\n"
        reply += f"📊 总访客: {len(visitors)}\n"
        
        if today_visitors:
            # 统计今日热门商户
            merchant_mentions = {}
            for v in today_visitors:
                related = v.get('related_merchants', [])
                for m in related:
                    merchant_mentions[m] = merchant_mentions.get(m, 0) + 1
            
            if merchant_mentions:
                sorted_merchants = sorted(
                    merchant_mentions.items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )[:5]
                
                reply += "\n🔥 **热门商户**\n"
                for m, count in sorted_merchants:
                    reply += f"  • {m}: {count}次\n"
        
        return reply
    
    def _send_daily_report(self):
        """发送日报"""
        try:
            report = self.exporter.generate_daily_report()
            
            return f"📊 **每日报告**\n\n{report}"
        except Exception as e:
            return f"生成报告失败: {str(e)}"


# 全局实例
_admin_bot = None


def get_admin_bot():
    """获取管理者机器人实例"""
    global _admin_bot
    if _admin_bot is None:
        _admin_bot = AdminBot()
    return _admin_bot


def handle_admin_message(user_id, content):
    """处理管理消息"""
    bot = get_admin_bot()
    return bot.process_message(user_id, content)


if __name__ == '__main__':
    # 测试
    bot = AdminBot()
    
    print("=== 管理者机器人测试 ===")
    print(bot._get_help())
    print("\n" + "="*50)
    print(bot._get_statistics())
