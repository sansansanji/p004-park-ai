# -*- coding: utf-8 -*-
"""
每日报告发送模块
自动生成日报，并通过邮件 + 企业微信发送给管理员
"""

import os
import sys
import json
import smtplib
import urllib.request
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import yaml

# Windows编码兼容
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加 scripts 目录到路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
sys.path.insert(0, SCRIPT_DIR)


class DailySender:
    """每日报告发送器"""
    
    def __init__(self):
        """初始化"""
        self.config = self._load_config()
        self.email_config = self.config.get('email', {})
        self.ww_config = self.config.get('wechat_work', {})
        self.recipients_config = self.config.get('scheduled_tasks', {}).get('daily_report', {}).get('recipients', [])
        
        # 导入数据导出模块
        from data_exporter import get_data_exporter
        self.exporter = get_data_exporter()
    
    def _load_config(self):
        """加载管理端配置"""
        config_path = os.path.join(CONFIG_DIR, 'admin_wechat.yaml')
        
        if not os.path.exists(config_path):
            print(f"⚠️  配置文件不存在: {config_path}")
            return {}
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"⚠️  加载配置失败: {e}")
            return {}
    
    def _get_access_token(self):
        """获取企业微信 access_token"""
        try:
            corp_id = self.ww_config.get('corp_id', '')
            secret = self.ww_config.get('agent', {}).get('secret', '')
            
            if not (corp_id and secret):
                return None
            
            url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corp_id}&corpsecret={secret}"
            req = urllib.request.Request(url)
            
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                return data.get('access_token', '')
        except Exception as e:
            print(f"⚠️  获取 access_token 失败: {e}")
            return None
    
    def send_email(self, subject, body, attachments=None):
        """发送邮件（带附件）"""
        try:
            enabled = self.email_config.get('enabled', False)
            if not enabled:
                print("📧 邮件发送未启用")
                return False
            
            smtp_server = self.email_config.get('smtp_server', '')
            smtp_port = self.email_config.get('smtp_port', 465)
            smtp_user = self.email_config.get('smtp_user', '')
            smtp_password = self.email_config.get('smtp_password', '')
            from_addr = self.email_config.get('from_address', smtp_user)
            to_addrs = self.email_config.get('to_addresses', [])
            
            if not (smtp_server and smtp_user and smtp_password and to_addrs):
                print("⚠️  邮件配置不完整")
                return False
            
            # 构建邮件
            msg = MIMEMultipart()
            msg['From'] = from_addr
            msg['To'] = ', '.join(to_addrs)
            msg['Subject'] = subject
            
            # 正文
            text_part = MIMEText(body, 'plain', 'utf-8')
            msg.attach(text_part)
            
            # 附件
            if attachments:
                for filepath in attachments:
                    if os.path.exists(filepath):
                        filename = os.path.basename(filepath)
                        with open(filepath, 'rb') as f:
                            part = MIMEApplication(f.read(), Name=filename)
                        part['Content-Disposition'] = f'attachment; filename="{filename}"'
                        msg.attach(part)
            
            # 发送
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as smtp:
                smtp.login(smtp_user, smtp_password)
                smtp.sendmail(from_addr, to_addrs, msg.as_string())
            
            print(f"✅ 邮件发送成功: {to_addrs}")
            return True
            
        except Exception as e:
            print(f"❌ 邮件发送失败: {e}")
            return False
    
    def send_wechat_message(self, content):
        """发送企业微信消息"""
        try:
            access_token = self._get_access_token()
            if not access_token:
                print("⚠️  获取 access_token 失败，跳过企微发送")
                return False
            
            agent_id = self.ww_config.get('agent', {}).get('agent_id', '')
            
            # 从配置读取接收人
            if not self.recipients_config:
                print("⚠️  未配置接收人，跳过企微发送")
                return False
            
            # 构建发送请求
            for to_user in self.recipients_config:
                url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
                payload = json.dumps({
                    "touser": to_user,
                    "msgtype": "text",
                    "agentid": agent_id,
                    "text": {"content": content},
                    "safe": 0
                }, ensure_ascii=False).encode('utf-8')
                
                req = urllib.request.Request(
                    url,
                    data=payload,
                    headers={'Content-Type': 'application/json'}
                )
                
                with urllib.request.urlopen(req, timeout=5) as resp:
                    resp_data = json.loads(resp.read().decode('utf-8'))
                    if resp_data.get('errcode') == 0:
                        print(f"✅ 企微消息发送成功: {to_user}")
                    else:
                        print(f"❌ 企微消息发送失败: {resp_data.get('errmsg', '')}")
            
            return True
            
        except Exception as e:
            print(f"❌ 企微消息发送失败: {e}")
            return False
    
    def run_daily_report(self, date=None):
        """执行每日报告任务"""
        print("="*60)
        print(f"📊 每日报告任务开始 - {datetime.now()}")
        print("="*60)

        # 生成日报
        result = self.exporter.run_daily_export()
        report_text = result.get('report', '')
        visitor_file = result.get('visitor_file')
        merchant_file = result.get('merchant_file')
        
        # 1. 发送企微摘要
        print("\n📱 发送企微摘要...")
        wechat_success = self.send_wechat_message(report_text)
        
        # 2. 发送邮件（带附件）
        print("\n📧 发送邮件报告...")
        subject = f"📊 园区AI助手每日数据报告 - {result.get('date', datetime.now().strftime('%Y-%m-%d'))}"
        attachments = []
        if visitor_file and os.path.exists(visitor_file):
            attachments.append(visitor_file)
        if merchant_file and os.path.exists(merchant_file):
            attachments.append(merchant_file)
        
        email_success = self.send_email(subject, report_text, attachments)
        
        # 汇总
        print("\n" + "="*60)
        print("📊 每日报告任务完成")
        print(f"  企微摘要: {'✅ 成功' if wechat_success else '❌ 失败/跳过'}")
        print(f"  邮件报告: {'✅ 成功' if email_success else '❌ 失败/跳过'}")
        print("="*60)
        
        return {
            'wechat_success': wechat_success,
            'email_success': email_success,
            'report': report_text,
            'attachments': attachments
        }


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='发送每日报告')
    parser.add_argument('--date', '-d', help='指定日期，格式：YYYYMMDD（默认今天）')
    args = parser.parse_args()
    
    sender = DailySender()
    
    if args.date:
        sender.run_daily_report(args.date)
    else:
        sender.run_daily_report()


if __name__ == '__main__':
    main()
