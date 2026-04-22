# -*- coding: utf-8 -*-
"""
微信公众号消息接入层
处理公众号的消息回调，与游客端机器人逻辑打通
"""

import os
import sys
import hashlib
import time
import xml.etree.ElementTree as ET
from datetime import datetime

from flask import Flask, request, make_response

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import yaml

CONFIG_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), 'config')


def load_mp_config():
    """加载公众号配置"""
    config_file = os.path.join(CONFIG_DIR, 'mp_wechat.yaml')
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f).get('mp', {})
    return {}


def verify_signature(token, timestamp, nonce, signature):
    """验证微信签名"""
    data = sorted([token, timestamp, nonce])
    sign = hashlib.sha1(''.join(data).encode()).hexdigest()
    return sign == signature


def parse_xml_message(xml_str):
    """解析微信XML消息"""
    root = ET.fromstring(xml_str)
    msg = {}
    for child in root:
        msg[child.tag] = child.text
    return msg


def build_text_reply(to_user, from_user, content):
    """构建文本回复XML"""
    timestamp = int(time.time())
    return f"""<xml>
<ToUserName><![CDATA[{to_user}]]></ToUserName>
<FromUserName><![CDATA[{from_user}]]></FromUserName>
<CreateTime>{timestamp}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{content}]]></Content>
</xml>"""


class MPWechatHandler:
    """公众号消息处理器"""

    def __init__(self):
        self.config = load_mp_config()
        self.token = self.config.get('token', 'park_mp_token')
        # 延迟导入，避免循环依赖
        self._bot = None
        self._member_dao = None

    @property
    def bot(self):
        if self._bot is None:
            try:
                from wechat_bot import WeChatBot
                self._bot = WeChatBot()
            except Exception:
                self._bot = None
        return self._bot

    @property
    def member_dao(self):
        if self._member_dao is None:
            try:
                from db_manager import MemberDAO
                self._member_dao = MemberDAO()
            except Exception:
                self._member_dao = None
        return self._member_dao

    def handle_verify(self, args):
        """处理微信服务器验证"""
        signature = args.get('signature', '')
        timestamp = args.get('timestamp', '')
        nonce = args.get('nonce', '')
        echostr = args.get('echostr', '')

        if verify_signature(self.token, timestamp, nonce, signature):
            return echostr
        return 'error'

    def handle_message(self, xml_body):
        """处理消息回调"""
        try:
            msg = parse_xml_message(xml_body)
        except Exception:
            return ''

        msg_type = msg.get('MsgType', '')
        from_user = msg.get('FromUserName', '')  # 用户openid
        to_user = msg.get('ToUserName', '')       # 公众号原始ID
        content = msg.get('Content', '').strip()

        # 会员处理（如果数据库已连接）
        member = None
        if self.member_dao:
            try:
                member = self.member_dao.get_or_create_by_openid(
                    openid_mp=from_user, source='mp'
                )
            except Exception:
                pass

        # 处理关注事件
        if msg_type == 'event':
            event = msg.get('Event', '')
            if event == 'subscribe':
                reply_content = self._get_welcome_text()
                return build_text_reply(from_user, to_user, reply_content)
            elif event == 'unsubscribe':
                return ''  # 取关事件不需要回复
            return ''

        # 处理文本消息
        if msg_type == 'text':
            reply = self._process_text(content, from_user, member)
            return build_text_reply(from_user, to_user, reply)

        # 其他消息类型暂不处理
        return build_text_reply(from_user, to_user,
            '您好！我目前只能处理文字消息，请直接输入您想了解的内容 😊')

    def _get_welcome_text(self):
        """获取欢迎语"""
        welcome_file = os.path.join(
            os.path.dirname(SCRIPT_DIR), 'config', 'welcome.md'
        )
        if os.path.exists(welcome_file):
            with open(welcome_file, 'r', encoding='utf-8') as f:
                return f.read()[:500]  # 公众号消息长度限制
        return """🎉 欢迎关注园区AI助手！

我可以帮您：
📍 【地图导览】- 找到园区内任何商户
🎫 【优惠券】- 查看专属优惠
🎉 【活动】- 了解最新活动
❓ 【帮助】- 查看更多功能

直接输入您想了解的内容，或发送关键词开始探索！"""

    def _process_text(self, content, openid, member=None):
        """处理文本消息，返回回复内容"""
        # 如果有机器人实例，走机器人逻辑
        if self.bot:
            try:
                # 构造消息格式，复用现有机器人逻辑
                fake_msg = {
                    'FromUserName': openid,
                    'Content': content,
                    'MsgType': 'text',
                    'channel': 'mp',
                }
                reply = self.bot.process_message(fake_msg)
                return reply or '收到您的消息，正在处理中...'
            except Exception as e:
                pass

        # 降级处理：简单关键词匹配
        content_lower = content.lower()
        if any(kw in content for kw in ['地图', '导览', '在哪', '怎么走', '位置']):
            return '🗺️ 园区地图导览\n\n请告诉我您想找的商户名称，我来帮您定位！\n\n回复「商户名称」即可查询。'
        elif any(kw in content for kw in ['优惠', '券', '折扣', '活动']):
            return '🎫 最新优惠活动\n\n今日特惠活动正在进行中，更多优惠请扫码入园后领取专属优惠券！'
        elif any(kw in content for kw in ['帮助', '功能', 'help', '?', '？']):
            return """📋 功能菜单

发送以下关键词：
📍 【地图】- 园区导览地图
🎫 【优惠】- 查看优惠活动
🎉 【活动】- 最新活动信息
📞 【联系】- 联系客服

或直接输入商户名称查询位置！"""
        else:
            return f'您好！您发送了：{content}\n\n如需帮助，请发送【帮助】查看功能菜单。'


# 创建处理器实例
mp_handler = MPWechatHandler()
