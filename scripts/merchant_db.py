# -*- coding: utf-8 -*-
"""
商户知识库管理模块
用于存储、加载和管理商户信息
"""

import os
import json
import csv
import yaml
from datetime import datetime

# 基础目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), 'data')


class MerchantDatabase:
    """商户知识库"""
    
    def __init__(self, data_path=None):
        """初始化"""
        if data_path is None:
            data_path = os.path.join(DATA_DIR, 'merchants_sample.csv')
        
        self.data_path = data_path
        self.merchants = {}
        self.locations = {}  # 位置 -> 商户列表
        
        # 加载商户数据
        self.load_merchants()
    
    def load_merchants(self):
        """从CSV文件加载商户数据"""
        if not os.path.exists(self.data_path):
            print(f"商户数据文件不存在: {self.data_path}")
            return
        
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get('商户名称', '').strip()
                    if not name:
                        continue
                    
                    merchant = {
                        'name': name,
                        'location': row.get('位置描述', '').strip(),
                        'lng': row.get('经度', '').strip(),
                        'lat': row.get('纬度', '').strip(),
                        'type': row.get('类型', '').strip(),
                        'promotion': row.get('优惠活动', '').strip()
                    }
                    
                    self.merchants[name] = merchant
                    
                    # 建立位置索引
                    location = merchant['location']
                    if location not in self.locations:
                        self.locations[location] = []
                    self.locations[location].append(name)
            
            print(f"已加载 {len(self.merchants)} 个商户")
            
        except Exception as e:
            print(f"加载商户数据失败: {e}")
    
    def get_merchant(self, name):
        """获取商户信息"""
        # 精确匹配
        if name in self.merchants:
            return self.merchants[name]
        
        # 模糊匹配
        for merchant_name, merchant in self.merchants.items():
            if name in merchant_name or merchant_name in name:
                return merchant
        
        return None
    
    def search_merchants(self, keyword):
        """搜索商户"""
        results = []
        
        for name, merchant in self.merchants.items():
            if keyword in name:
                results.append(merchant)
            elif keyword in merchant.get('location', ''):
                results.append(merchant)
            elif keyword in merchant.get('type', ''):
                results.append(merchant)
        
        return results
    
    def get_merchants_by_type(self, merchant_type):
        """按类型获取商户"""
        results = []
        
        for merchant in self.merchants.values():
            if merchant.get('type') == merchant_type:
                results.append(merchant)
        
        return results
    
    def get_all_merchants(self):
        """获取所有商户"""
        return list(self.merchants.values())
    
    def get_merchant_count(self):
        """获取商户数量"""
        return len(self.merchants)
    
    def add_merchant(self, merchant):
        """添加商户"""
        name = merchant.get('name')
        if name:
            self.merchants[name] = merchant
            
            # 更新位置索引
            location = merchant.get('location')
            if location:
                if location not in self.locations:
                    self.locations[location] = []
                if name not in self.locations[location]:
                    self.locations[location].append(name)
    
    def save_to_json(self, output_path=None):
        """保存为JSON格式"""
        if output_path is None:
            output_path = os.path.join(DATA_DIR, 'merchants.json')
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.merchants, f, ensure_ascii=False, indent=2)
            print(f"商户数据已保存到: {output_path}")
            return True
        except Exception as e:
            print(f"保存商户数据失败: {e}")
            return False
    
    def format_for_knowledge_base(self):
        """格式化输出为知识库格式"""
        lines = ["# 商户知识库\n"]
        lines.append(f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append(f"商户总数: {len(self.merchants)}\n\n")
        
        # 按类型分组
        type_groups = {}
        for merchant in self.merchants.values():
            mtype = merchant.get('type', '其他')
            if mtype not in type_groups:
                type_groups[mtype] = []
            type_groups[mtype].append(merchant)
        
        for mtype, merchants in type_groups.items():
            lines.append(f"## {mtype}\n")
            for m in merchants:
                lines.append(f"### {m['name']}")
                lines.append(f"- 位置: {m['location']}")
                if m.get('lng') and m.get('lat'):
                    lines.append(f"- 坐标: {m['lng']}, {m['lat']}")
                if m.get('promotion'):
                    lines.append(f"- 优惠: {m['promotion']}")
                lines.append("")
        
        return '\n'.join(lines)
    
    def export_to_markdown(self, output_path=None):
        """导出为Markdown格式"""
        if output_path is None:
            output_path = os.path.join(DATA_DIR, 'merchants.md')
        
        content = self.format_for_knowledge_base()
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"商户知识库已导出到: {output_path}")
            return True
        except Exception as e:
            print(f"导出失败: {e}")
            return False


# 全局实例
_merchant_db = None


def get_merchant_database():
    """获取商户数据库实例"""
    global _merchant_db
    if _merchant_db is None:
        _merchant_db = MerchantDatabase()
    return _merchant_db


if __name__ == '__main__':
    # 测试
    db = get_merchant_database()
    
    print(f"\n=== 商户数据库测试 ===")
    print(f"商户总数: {db.get_merchant_count()}")
    
    # 测试查询
    merchant = db.get_merchant("星巴克")
    if merchant:
        print(f"\n星巴克信息: {merchant}")
    
    # 测试搜索
    results = db.search_merchants("餐饮")
    print(f"\n餐饮类商户: {len(results)} 家")
    for m in results:
        print(f"  - {m['name']}: {m['location']}")
    
    # 测试导出
    db.export_to_markdown()
