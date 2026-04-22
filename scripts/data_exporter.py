# -*- coding: utf-8 -*-
"""
数据导出模块
生成CSV/Excel报表，支持定时任务和邮件发送
"""

import os
import json
import csv
from datetime import datetime, timedelta

# 基础目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), 'data')


class DataExporter:
    """数据导出器"""
    
    def __init__(self):
        """初始化"""
        self.exports_dir = os.path.join(DATA_DIR, 'exports')
        os.makedirs(self.exports_dir, exist_ok=True)
        
        # 加载数据存储
        from data_storage import get_data_storage
        self.storage = get_data_storage()
        
        # 加载商户数据
        from merchant_db import get_merchant_database
        self.merchant_db = get_merchant_database()
    
    def export_visitors(self, date=None):
        """
        导出游客明细数据
        文件名: 游客明细_YYYYMMDD.csv
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        filename = f'游客明细_{date}.csv'
        filepath = os.path.join(self.exports_dir, filename)
        
        visitors = self.storage.get_all_visitors()
        
        # CSV表头
        headers = [
            '游客ID', '首次访问', '最后活跃', 
            '会话次数', '消息总数',
            '兴趣偏好', '行为特征', '意向强度',
            '情感倾向', '消费能力', '出行目的',
            '关联商户', '咨询次数'
        ]
        
        try:
            with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                
                for v in visitors:
                    # 处理标签
                    tags = v.get('auto_tags', {})
                    
                    row = {
                        '游客ID': v.get('visitor_id', ''),
                        '首次访问': v.get('first_visit', ''),
                        '最后活跃': v.get('last_active', ''),
                        '会话次数': v.get('total_sessions', 0),
                        '消息总数': v.get('total_messages', 0),
                        '兴趣偏好': ','.join([t['tag'] for t in tags.get('兴趣偏好', [])]),
                        '行为特征': ','.join([t['tag'] for t in tags.get('行为特征', [])]),
                        '意向强度': ','.join([t['tag'] for t in tags.get('意向强度', [])]),
                        '情感倾向': ','.join([t['tag'] for t in tags.get('情感倾向', [])]),
                        '消费能力': ','.join([t['tag'] for t in tags.get('消费能力', [])]),
                        '出行目的': ','.join([t['tag'] for t in tags.get('出行目的', [])]),
                        '关联商户': ','.join(v.get('related_merchants', [])),
                        '咨询次数': v.get('total_messages', 0)
                    }
                    
                    writer.writerow(row)
            
            print(f"游客数据已导出: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"导出游客数据失败: {e}")
            return None
    
    def export_merchants(self, date=None):
        """
        导出商户汇总数据
        文件名: 商户数据汇总_YYYYMMDD.csv
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        filename = f'商户数据汇总_{date}.csv'
        filepath = os.path.join(self.exports_dir, filename)
        
        merchants = self.merchant_db.get_all_merchants()
        visitors = self.storage.get_all_visitors()
        
        # 统计每个商户被咨询的次数
        merchant_stats = {}
        for v in visitors:
            related = v.get('related_merchants', [])
            for m in related:
                merchant_stats[m] = merchant_stats.get(m, 0) + 1
        
        # CSV表头
        headers = [
            '商户名称', '位置', '类型', 
            '总咨询人数', '意向高人数', '价格敏感人数',
            '亲子家庭人数', '餐饮偏好人数', '活动感兴趣人数', '购物意向人数'
        ]
        
        try:
            with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                
                for m in merchants:
                    mname = m.get('name', '')
                    consult_count = merchant_stats.get(mname, 0)
                    
                    # 统计意向相关标签
                    intent_count = 0
                    price_sensitive = 0
                    family = 0
                    dining = 0
                    shopping = 0
                    
                    for v in visitors:
                        tags = v.get('auto_tags', {})
                        related = v.get('related_merchants', [])
                        
                        if mname in related:
                            # 检查意向强度
                            intent_tags = tags.get('意向强度', [])
                            if any(t['tag'] == '意向高' for t in intent_tags):
                                intent_count += 1
                            
                            # 检查行为特征
                            behavior_tags = tags.get('行为特征', [])
                            if any(t['tag'] == '价格敏感' for t in behavior_tags):
                                price_sensitive += 1
                            
                            # 检查兴趣偏好
                            interest_tags = tags.get('兴趣偏好', [])
                            if any(t['tag'] == '亲子' for t in interest_tags):
                                family += 1
                            if any(t['tag'] == '餐饮' for t in interest_tags):
                                dining += 1
                            if any(t['tag'] == '购物' for t in interest_tags):
                                shopping += 1
                    
                    row = {
                        '商户名称': mname,
                        '位置': m.get('location', ''),
                        '类型': m.get('type', ''),
                        '总咨询人数': consult_count,
                        '意向高人数': intent_count,
                        '价格敏感人数': price_sensitive,
                        '亲子家庭人数': family,
                        '餐饮偏好人数': dining,
                        '活动感兴趣人数': 0,  # 需要活动模块
                        '购物意向人数': shopping
                    }
                    
                    writer.writerow(row)
            
            print(f"商户数据已导出: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"导出商户数据失败: {e}")
            return None
    
    def generate_daily_report(self, date=None):
        """生成每日报告 - 优先从数据库读真实数据，兜底用JSON文件"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        # ─── 尝试从数据库生成（正式模式）────────────────────────
        try:
            from db_manager import get_db
            db = get_db()

            # 今日会话数
            today_sessions = db.query_one(
                "SELECT COUNT(DISTINCT session_id) as cnt FROM chat_logs WHERE DATE(created_at) = %s",
                (date,))['cnt'] or 0

            # 今日消息数
            today_messages = db.query_one(
                "SELECT COUNT(*) as cnt FROM chat_logs WHERE DATE(created_at) = %s",
                (date,))['cnt'] or 0

            # 今日新增会员
            today_new_members = db.query_one(
                "SELECT COUNT(*) as cnt FROM members WHERE DATE(created_at) = %s",
                (date,))['cnt'] or 0

            # 累计会员
            total_members = db.query_one("SELECT COUNT(*) as cnt FROM members")['cnt'] or 0

            # 热门商户
            hot_merchants = db.query_all(
                """SELECT m.name, COUNT(*) as cnt
                   FROM chat_logs cl
                   JOIN merchants m ON cl.content LIKE CONCAT('%%', m.name, '%%')
                   WHERE DATE(cl.created_at) = %s
                   GROUP BY m.id ORDER BY cnt DESC LIMIT 5""", (date,))

            # 用户标签分布
            tag_rows = db.query_all(
                """SELECT tags FROM members
                   WHERE DATE(created_at) >= DATE_SUB(%s, INTERVAL 7 DAY)
                   AND tags IS NOT NULL AND tags != '' AND tags != '[]'""", (date,))

            import json as _json
            tag_counter = {}
            for row in tag_rows:
                try:
                    tags = _json.loads(row['tags']) if isinstance(row['tags'], str) else row['tags']
                    if isinstance(tags, list):
                        for t in tags:
                            tag_counter[t] = tag_counter.get(t, 0) + 1
                except Exception:
                    pass
            top_tags = sorted(tag_counter.items(), key=lambda x: x[1], reverse=True)[:5]

            # 构建报告
            report = f"📊 星汇广场每日数据报告 - {date}\n\n"
            report += f"💬 今日对话\n"
            report += f"  会话数: {today_sessions}\n"
            report += f"  消息数: {today_messages}\n\n"
            report += f"👥 会员数据\n"
            report += f"  今日新增: {today_new_members}\n"
            report += f"  累计会员: {total_members}\n\n"

            if hot_merchants:
                report += f"🔥 今日热门商户\n"
                for i, row in enumerate(hot_merchants, 1):
                    report += f"  {i}. {row['name']}: {row['cnt']}次咨询\n"
                report += "\n"

            if top_tags:
                report += f"🏷️ 近7日热门标签\n"
                for tag, cnt in top_tags:
                    report += f"  • {tag}: {cnt}人\n"
                report += "\n"

            report += "📱 管理后台: https://luckeepro.top/admin\n"
            print("[每日报告] ✅ 从数据库生成成功")
            return report

        except Exception as db_err:
            print(f"[每日报告] 数据库生成失败，走JSON兜底: {db_err}")

        # ─── 兜底：从本地JSON文件生成（演示模式）────────────────
        visitors = self.storage.get_all_visitors()
        merchants = self.merchant_db.get_all_merchants()
        
        # 今日活跃
        today_visitors = []
        for v in visitors:
            last_active = v.get('last_active', '')
            if date in last_active:
                today_visitors.append(v)
        
        # 热门商户
        merchant_mentions = {}
        for v in today_visitors:
            related = v.get('related_merchants', [])
            for m in related:
                merchant_mentions[m] = merchant_mentions.get(m, 0) + 1
        
        sorted_merchants = sorted(
            merchant_mentions.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        # 标签统计
        tag_stats = {}
        for v in today_visitors:
            tags = v.get('auto_tags', {})
            for category, tag_list in tags.items():
                if category not in tag_stats:
                    tag_stats[category] = {}
                for t in tag_list:
                    tag_name = t.get('tag', '')
                    if tag_name:
                        tag_stats[category][tag_name] = tag_stats[category].get(tag_name, 0) + 1
        
        # 构建报告
        report = f"📊 每日数据报告 - {date}\n\n"
        report += f"👥 访客统计\n"
        report += f"  今日访客: {len(today_visitors)}\n"
        report += f"  累计访客: {len(visitors)}\n"
        report += f"  商户总数: {len(merchants)}\n\n"
        
        if sorted_merchants:
            report += f"🔥 热门商户TOP5\n"
            for i, (m, count) in enumerate(sorted_merchants, 1):
                report += f"  {i}. {m}: {count}次咨询\n"
            report += "\n"
        
        if tag_stats:
            report += f"🏷️ 今日用户标签\n"
            for category, tags in tag_stats.items():
                top_tags = sorted(tags.items(), key=lambda x: x[1], reverse=True)[:3]
                if top_tags:
                    report += f"\n  {category}:\n"
                    for tag, count in top_tags:
                        report += f"    • {tag}: {count}\n"
        
        return report
    
    def run_daily_export(self):
        """运行每日导出任务"""
        date = datetime.now().strftime('%Y%m%d')
        
        print(f"开始每日数据导出: {date}")
        
        # 导出数据
        visitor_file = self.export_visitors(date)
        merchant_file = self.export_merchants(date)
        
        # 生成报告
        report = self.generate_daily_report()
        
        print("每日导出完成")
        
        return {
            'date': date,
            'visitor_file': visitor_file,
            'merchant_file': merchant_file,
            'report': report
        }


# 全局实例
_data_exporter = None


def get_data_exporter():
    """获取数据导出器实例"""
    global _data_exporter
    if _data_exporter is None:
        _data_exporter = DataExporter()
    return _data_exporter


if __name__ == '__main__':
    # 测试
    exporter = DataExporter()
    
    print("=== 数据导出测试 ===")
    result = exporter.run_daily_export()
    
    print("\n" + "="*50)
    print(result['report'])
