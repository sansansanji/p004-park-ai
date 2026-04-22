# -*- coding: utf-8 -*-
"""
地图服务模块
集成天地图API，提供位置查询和导航功能
"""

import os
import json
import urllib.request
import urllib.parse
import yaml
from datetime import datetime

# 基础目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(os.path.dirname(BASE_DIR), 'config')


class MapService:
    """地图服务（天地图）"""
    
    def __init__(self, config_path=None):
        """初始化"""
        if config_path is None:
            config_path = os.path.join(CONFIG_DIR, 'system.yaml')
        
        self.config = self._load_config(config_path)
        
        # 地图配置
        map_config = self.config.get('map', {})
        self.provider = map_config.get('provider', 'tianditu')
        self.api_key = map_config.get('api_key', '')
        
        # 默认位置
        default_loc = map_config.get('default_location', {})
        self.default_lng = default_loc.get('lng', 116.4074)
        self.default_lat = default_loc.get('lat', 39.9042)
        
        # 园区名称（用于地理编码）
        self.park_name = "XX园区"
    
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
    
    def _make_request(self, url, timeout=10):
        """发送HTTP请求"""
        try:
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            print(f"请求失败: {e}")
            return None
    
    def geocode(self, address):
        """
        地理编码：将地址转换为坐标
        使用天地图地理编码API
        """
        # 构建请求URL
        base_url = "https://apis.map.qq.com/v3/geocoder"
        
        # 如果有API Key，使用腾讯地图（更稳定）
        if self.api_key:
            params = {
                'key': self.api_key,
                'address': self.park_name + address,
                'output': 'json'
            }
            url = f"{base_url}?{urllib.parse.urlencode(params)}"
            data = self._make_request(url)
            
            if data and data.get('status') == 0:
                result = data.get('result', {})
                location = result.get('location', {})
                return {
                    'lng': location.get('lng'),
                    'lat': location.get('lat'),
                    'address': result.get('address')
                }
        
        # 无API Key时，返回默认坐标（测试用）
        # 实际使用时需要配置API Key或手动输入坐标
        return {
            'lng': self.default_lng,
            'lat': self.default_lat,
            'address': address,
            'note': '默认坐标，请配置API Key获取准确位置'
        }
    
    def reverse_geocode(self, lng, lat):
        """
        逆地理编码：将坐标转换为地址
        """
        if not self.api_key:
            return {'address': '未知地址'}
        
        base_url = "https://apis.map.qq.com/v3/geocoder"
        params = {
            'key': self.api_key,
            'location': f"{lat},{lng}",
            'output': 'json'
        }
        
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        data = self._make_request(url)
        
        if data and data.get('status') == 0:
            return data.get('result', {})
        
        return {'address': '未知地址'}
    
    def get_static_map_url(self, lng, lat, zoom=16, width=400, height=300):
        """
        获取静态地图图片URL
        """
        if self.api_key:
            # 腾讯地图静态图
            return (f"https://apis.map.qq.com/ws/staticmap/v2/"
                    f"?key={self.api_key}&center={lat},{lng}"
                    f"&zoom={zoom}&size={width}x{height}&markers= {lat},{lng}")
        else:
            # 天地图（无需API Key）
            return (f"https://www.tianditu.gov.cn/marker/"
                    f"?position={lng},{lat}&zoom={zoom}")
    
    def get_map_link(self, lng, lat, zoom=16):
        """
        获取地图查看链接
        """
        # 腾讯地图
        if self.api_key:
            return (f"https://apis.map.qq.com/uri/v1/marker"
                    f"?marker=coord:{lat},{lng}&referer=myapp")
        
        # 天地图（无需API Key）
        return f"https://www.tianditu.gov.cn/?#lng={lng},lat={lat},zoom={zoom}"
    
    def build_navigation_reply(self, merchant_name, merchant_info):
        """
        构建导航回复
        """
        location = merchant_info.get('location', '未知')
        lng = merchant_info.get('lng', '')
        lat = merchant_info.get('lat', '')
        
        reply = f"📍 **{merchant_name}** 位于 **{location}**\n\n"
        
        # 地图链接
        if lng and lat:
            map_link = self.get_map_link(lng, lat)
            reply += f"🗺️ [点击查看地图]({map_link})\n"
        else:
            # 尝试获取坐标
            coords = self.geocode(location)
            if coords:
                map_link = self.get_map_link(coords['lng'], coords['lat'])
                reply += f"🗺️ [点击查看地图]({map_link})\n"
        
        # 优惠信息
        promotion = merchant_info.get('promotion', '')
        if promotion:
            reply += f"\n🎫 当前优惠: {promotion}"
        
        return reply
    
    def search_nearby(self, lng, lat, radius=1000, keyword=''):
        """
        搜索附近商户
        """
        if not self.api_key:
            return []
        
        base_url = "https://apis.map.qq.com/ws/place/v1/search"
        params = {
            'key': self.api_key,
            'boundary': f"nearby({lat},{lng},{radius})",
            'keyword': keyword,
            'page_size': 10
        }
        
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        data = self._make_request(url)
        
        if data and data.get('status') == 0:
            return data.get('data', [])
        
        return []


# 全局实例
_map_service = None


def get_map_service():
    """获取地图服务实例"""
    global _map_service
    if _map_service is None:
        _map_service = MapService()
    return _map_service


if __name__ == '__main__':
    # 测试
    service = MapService()
    
    print("=== 地图服务测试 ===")
    
    # 测试地理编码
    result = service.geocode("A区3号")
    print(f"地理编码结果: {result}")
    
    # 测试地图链接
    link = service.get_map_link(116.4074, 39.9042)
    print(f"地图链接: {link}")
