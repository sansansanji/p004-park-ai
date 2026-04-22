# -*- coding: utf-8 -*-
"""
数据存储管理模块
统一管理各类数据的存储路径和格式
"""

import os
import json
import yaml
from datetime import datetime

# 基础目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), 'data')
CONFIG_DIR = os.path.join(os.path.dirname(BASE_DIR), 'config')


class DataStorage:
    """数据存储管理器"""
    
    def __init__(self):
        """初始化"""
        self.config = self._load_config()
        
        # 数据目录
        self.visitors_dir = os.path.join(DATA_DIR, 'visitors')
        self.exports_dir = os.path.join(DATA_DIR, 'exports')
        self.logs_dir = os.path.join(DATA_DIR, 'logs')
        self.merchants_dir = os.path.join(DATA_DIR, 'merchants')
        
        # 确保目录存在
        self._ensure_directories()
    
    def _load_config(self):
        """加载配置"""
        config_path = os.path.join(CONFIG_DIR, 'system.yaml')
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            except Exception as e:
                print(f"加载配置失败: {e}")
        
        return {}
    
    def _ensure_directories(self):
        """确保数据目录存在"""
        dirs = [
            self.visitors_dir,
            self.exports_dir,
            self.logs_dir,
            self.merchants_dir
        ]
        
        for d in dirs:
            os.makedirs(d, exist_ok=True)
    
    # ==================== 游客数据 ====================
    
    def get_visitor_profile_path(self, visitor_id):
        """获取游客档案路径"""
        return os.path.join(self.visitors_dir, f'{visitor_id}.json')
    
    def save_visitor_profile(self, visitor_id, profile):
        """保存游客档案"""
        filepath = self.get_visitor_profile_path(visitor_id)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(profile, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存游客档案失败: {e}")
            return False
    
    def load_visitor_profile(self, visitor_id):
        """加载游客档案"""
        filepath = self.get_visitor_profile_path(visitor_id)
        
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载游客档案失败: {e}")
        
        return None
    
    def get_all_visitors(self):
        """获取所有游客"""
        visitors = []
        
        if os.path.exists(self.visitors_dir):
            for filename in os.listdir(self.visitors_dir):
                if filename.endswith('.json'):
                    visitor_id = filename[:-5]
                    profile = self.load_visitor_profile(visitor_id)
                    if profile:
                        visitors.append(profile)
        
        return visitors
    
    def get_visitor_count(self):
        """获取游客数量"""
        if os.path.exists(self.visitors_dir):
            return len([f for f in os.listdir(self.visitors_dir) if f.endswith('.json')])
        return 0
    
    # ==================== 商户数据 ====================
    
    def get_merchants_path(self):
        """获取商户数据路径"""
        # 优先使用CSV
        csv_path = os.path.join(DATA_DIR, 'merchants_sample.csv')
        if os.path.exists(csv_path):
            return csv_path
        
        # 其次使用JSON
        json_path = os.path.join(self.merchants_dir, 'merchants.json')
        if os.path.exists(json_path):
            return json_path
        
        return None
    
    # ==================== 导出数据 ====================
    
    def get_export_path(self, filename):
        """获取导出文件路径"""
        return os.path.join(self.exports_dir, filename)
    
    def list_exports(self):
        """列出导出文件"""
        if os.path.exists(self.exports_dir):
            return os.listdir(self.exports_dir)
        return []
    
    # ==================== 对话日志 ====================
    
    def save_conversation_log(self, visitor_id, messages):
        """保存对话日志"""
        date_str = datetime.now().strftime('%Y%m%d')
        filename = f'conversation_{visitor_id}_{date_str}.json'
        filepath = os.path.join(self.logs_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    'visitor_id': visitor_id,
                    'date': date_str,
                    'messages': messages
                }, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存对话日志失败: {e}")
            return False
    
    # ==================== 统计摘要 ====================
    
    def get_summary(self):
        """获取数据摘要"""
        summary = {
            'total_visitors': self.get_visitor_count(),
            'export_files': len(self.list_exports()),
            'last_updated': datetime.now().isoformat()
        }
        
        return summary


# 全局实例
_data_storage = None


def get_data_storage():
    """获取数据存储实例"""
    global _data_storage
    if _data_storage is None:
        _data_storage = DataStorage()
    return _data_storage


if __name__ == '__main__':
    # 测试
    storage = DataStorage()
    
    print("=== 数据存储测试 ===")
    print(f"游客目录: {storage.visitors_dir}")
    print(f"导出目录: {storage.exports_dir}")
    print(f"日志目录: {storage.logs_dir}")
    
    print("\n=== 数据摘要 ===")
    print(storage.get_summary())
