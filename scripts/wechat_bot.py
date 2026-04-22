# -*- coding: utf-8 -*-
"""
企业微信机器人消息处理模块
用于处理游客通过企业微信机器人的对话请求
"""

import os
import json
import yaml
import hashlib
import time
import urllib.request
import urllib.parse
from datetime import datetime
from xml.etree import ElementTree

# 配置路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(os.path.dirname(BASE_DIR), 'config')

class WeChatWorkBot:
    """企业微信机器人"""
    
    def __init__(self, config_path=None):
        """初始化机器人"""
        if config_path is None:
            config_path = os.path.join(CONFIG_DIR, 'wechat_work.yaml')
        
        # 加载配置
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = {}
        
        # 加载欢迎语（优先从数据库，兜底从文件）
        self.welcome_message = self._load_welcome_message()
        
        # 加载记忆系统
        self.memory_config = self._load_memory_config()
        
        # 初始化记忆系统
        from memory_system import get_memory_system
        self.memory_system = get_memory_system()
        
        # 初始化位置查询处理器
        from location_handler import get_location_handler
        self.location_handler = get_location_handler()
        
        # 初始化游客会话存储（持久化到文件，防重启丢失）
        self._sessions_file = os.path.join(BASE_DIR, '..', 'data', 'sessions.json')
        self.sessions = self._load_sessions()

        # 初始化标签系统
        try:
            from tagging_system import get_tagging_system
            self.tagging_system = get_tagging_system()
            print("[标签系统] 初始化成功")
        except Exception as e:
            self.tagging_system = None
            print(f"[标签系统] 初始化失败（非阻塞）: {e}")
    
    def _load_sessions(self):
        """从文件加载会话状态"""
        try:
            if os.path.exists(self._sessions_file):
                with open(self._sessions_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"[会话] 加载失败，使用空字典: {e}")
        return {}
    
    def _save_sessions(self):
        """保存会话状态到文件"""
        try:
            os.makedirs(os.path.dirname(self._sessions_file), exist_ok=True)
            with open(self._sessions_file, 'w', encoding='utf-8') as f:
                json.dump(self.sessions, f, ensure_ascii=False)
        except Exception as e:
            print(f"[会话] 保存失败（非阻塞）: {e}")
    
    def _load_welcome_message(self):
        """加载欢迎语：优先从数据库system_configs读取，兜底从文件读取"""
        # 1. 尝试从数据库读取
        try:
            from db_manager import ConfigDAO
            config_dao = ConfigDAO()
            db_welcome = config_dao.get('welcome_msg')
            if db_welcome:
                print("[欢迎语] 从数据库加载成功")
                # 尝试追加商户列表
                return self._append_merchant_list(db_welcome)
        except Exception as e:
            print(f"[欢迎语] 数据库读取失败，走文件兜底: {e}")
        
        # 2. 从文件读取（兜底）
        welcome_path = os.path.join(BASE_DIR, 'skills/visitor-entry/prompts/welcome.txt')
        if os.path.exists(welcome_path):
            with open(welcome_path, 'r', encoding='utf-8') as f:
                base_welcome = f.read()
        else:
            base_welcome = "欢迎来到园区！我是您的智能导游，请问有什么可以帮您？"
        
        return self._append_merchant_list(base_welcome)
    
    def _append_merchant_list(self, base_welcome):
        """在欢迎语后追加商户列表"""
        try:
            from location_handler import get_location_handler
            handler = get_location_handler()
            merchant_list = handler.get_welcome_with_merchants()
            if merchant_list:
                return base_welcome + "\n\n" + merchant_list
        except Exception as e:
            print(f"[欢迎语] 加载商户列表失败: {e}")
        return base_welcome
    
    def _load_memory_config(self):
        """加载记忆配置"""
        memory_path = os.path.join(CONFIG_DIR, 'memory.yaml')
        if os.path.exists(memory_path):
            with open(memory_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return {}
    
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
        """解析接收到的消息"""
        try:
            root = ElementTree.fromstring(xml_data)
            msg = {
                'msg_type': root.find('MsgType').text if root.find('MsgType') is not None else '',
                'from_user': root.find('FromUserName').text if root.find('FromUserName') is not None else '',
                'create_time': root.find('CreateTime').text if root.find('CreateTime') is not None else '',
                'content': root.find('Content').text if root.find('Content') is not None else '',
                'msg_id': root.find('MsgId').text if root.find('MsgId') is not None else '',
                'event': root.find('Event').text if root.find('Event') is not None else '',
                'token': root.find('Token').text if root.find('Token') is not None else '',
                'open_kfid': root.find('OpenKfId').text if root.find('OpenKfId') is not None else '',
            }
            return msg
        except Exception as e:
            print(f"解析消息失败: {e}")
            return None
    
    def create_response(self, to_user, content, msg_type='text'):
        """创建回复消息"""
        response = f"""<xml>
<ToUserName><![CDATA[{to_user}]]></ToUserName>
<FromUserName><![CDATA[gh_xxxxxxxx]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[{msg_type}]]></MsgType>
<Content><![CDATA[{content}]]></Content>
</xml>"""
        return response
    
    def is_new_session(self, user_id):
        """判断是否是新会话"""
        if user_id not in self.sessions:
            return True
        
        # 检查会话是否超时
        last_time = self.sessions[user_id].get('last_time', 0)
        timeout = self.memory_config.get('session', {}).get('timeout', 30)
        
        if time.time() - last_time > timeout * 60:
            return True
        
        return False
    
    def process_message(self, user_id, content):
        """处理用户消息"""
        # ① 优先检测手机号绑定（无论新老会话都要处理，避免绑定消息被当普通消息处理）
        phone_result = self._try_bind_phone(user_id, content)
        if phone_result:
            return phone_result

        # ② 检查是否是新会话
        if self.is_new_session(user_id):
            # 使用记忆系统创建新会话
            self.memory_system.create_session(user_id)
            
            # ★ 记录会话状态，防止下条消息再次触发欢迎语
            self.sessions[user_id] = {
                'last_time': time.time(),
                'mentioned_merchants': []
            }
            self._save_sessions()  # 持久化

            # 更新游客档案（会话开始）
            self._update_visitor_profile(user_id, 'session_start')

            # ★ 自动打标签（新访客）+ 确保会员入库
            self._auto_tag(user_id, content, is_new_visitor=True)

            # 通知管理端：新游客进入
            self._notify_admin(user_id, content, event='new_session')

            # 检查该用户是否已绑定手机号，决定是否在欢迎语后追加引导
            bind_hint = self._get_phone_bind_hint(user_id)
            return self.welcome_message + bind_hint
        
        # ③ 检查是否是简短回复（可能是多轮对话的后续）
        if content in ['1', '2', '3', '4', '5', 'a', 'b', 'c', 'd']:
            # 处理快捷操作选择
            return self._handle_quick_action(user_id, content)
        
        # ④ 调用记忆系统更新会话
        self.memory_system.update_session(user_id, content)
        
        # ★ 更新会话时间戳，保持会话活跃
        if user_id in self.sessions:
            self.sessions[user_id]['last_time'] = time.time()
            self._save_sessions()  # 持久化
        
        # ⑤ 生成回复
        response = self._generate_response(content, user_id)
        
        # ★ 自动打标签（老访客）
        self._auto_tag(user_id, content)

        # 记录商户提及
        self._extract_and_save_merchants(user_id, content)

        # 通知管理端：游客发送了消息
        self._notify_admin(user_id, content, response=response, event='message')
        
        return response

    def _get_phone_bind_hint(self, user_id):
        """检查会员是否已绑定手机号，返回绑定引导语（未绑定）或空字符串（已绑定）"""
        try:
            from db_manager import MemberDAO
            dao = MemberDAO()
            member = dao.get_or_create_by_openid(openid_wx=user_id, source='wxwork')
            if member and member.get('phone'):
                return ''  # 已绑定，欢迎语不追加引导
            # 未绑定手机号，追加引导
            return '\n\n📱 回复您的手机号，即可绑定会员并领取专属优惠券！'
        except Exception:
            return ''  # 数据库不可用时静默跳过

    def _try_bind_phone(self, user_id, content):
        """
        检测消息是否为手机号，如果是则执行绑定逻辑。
        返回回复文本（已处理），或 None（不是手机号）。
        """
        import re
        content_stripped = content.strip()
        # 仅匹配11位纯数字手机号（1开头）
        if not re.fullmatch(r'1[3-9]\d{9}', content_stripped):
            return None

        phone = content_stripped
        try:
            from db_manager import MemberDAO
            dao = MemberDAO()

            # 检查该手机号是否已被其他会员绑定
            existing_by_phone = dao.get_by_phone(phone)
            if existing_by_phone:
                # 手机号已被绑定，看是否是本人
                member = dao.get_or_create_by_openid(openid_wx=user_id, source='wxwork')
                if member and member.get('id') == existing_by_phone.get('id'):
                    return '您已绑定该手机号，无需重复操作 😊'
                else:
                    return '该手机号已被其他账号绑定，如有疑问请联系服务台。'

            # 获取或创建当前用户的会员记录
            member = dao.get_or_create_by_openid(openid_wx=user_id, source='wxwork')
            if not member:
                return '系统繁忙，请稍后再试。'

            # 已有手机号则提示无需重复
            if member.get('phone'):
                return f'您已绑定手机号 {member["phone"][:3]}****{member["phone"][-4:]}，无需重复操作 😊'

            # 执行绑定
            dao.bind_phone(member['id'], phone)

            # 自动发放新会员优惠券（有模板则发，没有则跳过）
            coupon_msg = self._issue_welcome_coupon(member['id'])

            print(f"[会员绑定] user_id={user_id[:8]}... phone={phone[:3]}****{phone[-4:]} member_id={member['id']}")
            return f'🎉 绑定成功！欢迎加入星汇广场会员！{coupon_msg}'

        except Exception as e:
            print(f"[会员绑定] 失败: {e}")
            return '系统繁忙，请稍后再试。'

    def _issue_welcome_coupon(self, member_id):
        """为新绑定会员发放欢迎优惠券，返回提示文字"""
        try:
            from db_manager import get_db
            db = get_db()
            # 查找第一个有效的优惠券模板
            template = db.query_one(
                "SELECT * FROM coupon_templates WHERE status = 1 ORDER BY id ASC LIMIT 1"
            )
            if not template:
                return ''
            # 计算有效期
            from datetime import date, timedelta
            valid_days = template.get('valid_days', 30)
            expire_date = date.today() + timedelta(days=valid_days)
            # 发券
            db.execute(
                """INSERT INTO coupons (member_id, template_id, name, discount_type,
                   discount_value, min_amount, expire_date, status)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, 'unused')""",
                (member_id, template['id'], template['name'],
                 template['discount_type'], template['discount_value'],
                 template.get('min_amount', 0), expire_date)
            )
            name = template['name']
            val = template['discount_value']
            dtype = template['discount_type']
            if dtype == 'cash':
                desc = f'满减券 ¥{val}'
            elif dtype == 'discount':
                desc = f'{val}折优惠券'
            else:
                desc = name
            return f'\n🎁 已为您发放【{desc}】，有效期至 {expire_date}，到店消费时出示即可！'
        except Exception as e:
            print(f"[欢迎券] 发放失败（非阻塞）: {e}")
            return ''

    def _notify_admin(self, user_id, content, response=None, event='message'):
        """向管理端推送游客消息通知
        
        event 类型：
          new_session         - 新游客进入
          message             - 游客发消息（AI已回复）
          human_takeover_new_msg - 人工接管中，游客发了新消息（需人工处理）
        """
        try:
            # 加载管理端配置
            admin_config_path = os.path.join(CONFIG_DIR, 'admin_wechat.yaml')
            if not os.path.exists(admin_config_path):
                return  # 管理端未配置，跳过

            with open(admin_config_path, 'r', encoding='utf-8') as f:
                admin_config = yaml.safe_load(f) or {}

            ww = admin_config.get('wechat_work', {})
            corp_id = ww.get('corp_id', '')
            agent_id = ww.get('agent', {}).get('agent_id', '')
            secret = ww.get('agent', {}).get('secret', '')
            notify_users = admin_config.get('notify_users', [])

            if not (corp_id and agent_id and secret and notify_users):
                return  # 配置不完整，跳过

            # 获取 access_token
            token_url = (
                f"https://qyapi.weixin.qq.com/cgi-bin/gettoken"
                f"?corpid={corp_id}&corpsecret={secret}"
            )
            req = urllib.request.Request(token_url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                token_data = json.loads(resp.read().decode('utf-8'))
            access_token = token_data.get('access_token', '')
            if not access_token:
                return

            # 构建通知文本
            short_uid = user_id[:12] + '...' if len(user_id) > 12 else user_id
            admin_url = 'https://luckeepro.top/admin'

            if event == 'new_session':
                text = (
                    f"[新游客] {short_uid}\n"
                    f"首条消息：{content[:60]}\n\n"
                    f"🔗 查看后台：{admin_url}"
                )
            elif event == 'human_takeover_new_msg':
                # 人工接管中：游客发了新消息，提醒管理员手动回复
                text = (
                    f"[🙋 人工接管-新消息]\n"
                    f"游客：{short_uid}\n"
                    f"消息：{content[:80]}\n\n"
                    f"⚠️ 此会话正由您人工接管，AI已静默。\n"
                    f"请在企微客服工作台或后台手动回复。\n"
                    f"🔗 后台：{admin_url}"
                )
            else:
                # 普通消息通知（仅当游客消息较特殊时发，普通对话不打扰）
                # 判断是否值得打扰管理员：新手机号绑定、投诉词、呼叫人工等
                should_notify = any(kw in content for kw in [
                    '人工', '客服', '投诉', '投诉', '退款', '退钱', '不满', '差评',
                    '出事', '受伤', '危险', '紧急', '报警'
                ])
                if not should_notify:
                    return  # 普通消息不打扰管理员，后台自己查

                text = (
                    f"[⚠️ 需关注] 游客 {short_uid}\n"
                    f"消息：{content[:80]}\n"
                )
                if response:
                    text += f"AI回复：{response[:60]}\n"
                text += f"🔗 查看后台：{admin_url}"

            # 发送消息给每个管理员
            send_url = (
                f"https://qyapi.weixin.qq.com/cgi-bin/message/send"
                f"?access_token={access_token}"
            )
            for to_user in notify_users:
                payload = json.dumps({
                    "touser": to_user,
                    "msgtype": "text",
                    "agentid": agent_id,
                    "text": {"content": text},
                    "safe": 0
                }, ensure_ascii=False).encode('utf-8')
                send_req = urllib.request.Request(
                    send_url,
                    data=payload,
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(send_req, timeout=5) as send_resp:
                    pass  # 忽略返回结果，通知失败不影响主流程

        except Exception as e:
            print(f"通知管理端失败（非阻塞）: {e}")
    
    def _handle_quick_action(self, user_id, choice):
        """处理快捷操作选择"""
        # 使用位置处理器获取商户列表
        quick_actions = {
            '1': "请告诉我想去的商户名称，我帮您导航",
            '2': self.location_handler._handle_type_query('娱乐') if hasattr(self, 'location_handler') else "今日活动：xxx",
            '3': self.location_handler._handle_type_query('餐饮') if hasattr(self, 'location_handler') else "推荐餐厅：xxx",
            '4': self.location_handler._handle_promotion_query() if hasattr(self, 'location_handler') else "当前优惠：xxx"
        }
        
        result = quick_actions.get(choice)
        return result if result else "请输入您的问题"
    
    def _generate_response(self, user_message, user_id):
        """生成回复"""
        # 首先尝试位置查询处理器
        if self.location_handler.can_handle(user_message):
            return self.location_handler.handle(user_message, user_id)
        
        # ★ 从数据库读取回复规则（优先），找不到再走硬编码兜底
        try:
            from db_manager import ReplyRuleDAO
            rule_dao = ReplyRuleDAO()
            db_reply = rule_dao.match(user_message)
            if db_reply:
                return db_reply
        except Exception as e:
            print(f"[回复] 数据库规则匹配失败，走兜底: {e}")
        
        # 关键词匹配（兜底，数据库无规则时使用）
        keywords = {
            '地图': '点击查看园区地图：https://www.tianditu.gov.cn/',
            '活动': '今日活动：xxx（请在管理后台-回复规则中配置）',
            '优惠': '当前优惠：xxx（请在管理后台-回复规则中配置）',
            '餐厅': '园区内有星巴克、肯德基等餐厅，请问您想了解哪家？',
            '星巴克': '星巴克位于A区3号，点击查看地图：https://www.tianditu.gov.cn/',
        }
        
        for keyword, reply in keywords.items():
            if keyword in user_message:
                # 记录提到的商户
                if user_id in self.sessions and 'mentioned_merchants' in self.sessions[user_id]:
                    self.sessions[user_id]['mentioned_merchants'].append(keyword)
                return reply
        
        # 默认回复
        return "抱歉，我暂时无法回答这个问题。请问还有其他我可以帮您的吗？"
    
    def _auto_tag(self, user_id, content, is_new_visitor=False):
        """自动打标签：基于关键词匹配，结果保存到本地游客档案"""
        # ★ 优先从数据库读取标签规则
        db_tags = []
        try:
            from db_manager import TagRuleDAO
            tag_dao = TagRuleDAO()
            db_tags = tag_dao.match_tags(content)
            if db_tags:
                print(f"[标签-DB] 用户 {user_id[:10]}... 匹配数据库标签: {db_tags}")
        except Exception as e:
            print(f"[标签-DB] 数据库标签规则匹配失败: {e}")

        if not self.tagging_system and not db_tags:
            return

        try:
            # 第一层：关键词匹配标签（本地即可运行，不需要AI）
            tags = self.tagging_system.layer1_preset_tagging(content) if self.tagging_system else []

            # 合并数据库标签
            for tag_name in db_tags:
                if not any(t['tag'] == tag_name for t in tags):
                    tags.append({
                        'layer': 1,
                        'category': '数据库规则',
                        'tag': tag_name,
                        'confidence': 1.0,
                        'matched_keyword': 'db_rule'
                    })

            # 如果是新访客，自动加上"新访客"标签
            if is_new_visitor:
                tags.append({
                    'layer': 1,
                    'category': '用户状态',
                    'tag': '新访客',
                    'confidence': 1.0,
                    'matched_keyword': 'auto_first_visit'
                })

            if tags:
                tag_names = [t['tag'] for t in tags]
                print(f"[标签] 用户 {user_id[:10]}... 匹配标签: {tag_names}")

                # 保存到本地游客档案（JSON文件）
                profile = self._load_visitor_profile(user_id)
                existing_tags = profile.get('tags', {})

                # 格式化并合并标签
                formatted = self.tagging_system.format_tags_for_profile(tags)
                for category, tag_list in formatted.items():
                    if category not in existing_tags:
                        existing_tags[category] = []
                    for t in tag_list:
                        # 去重
                        if not any(et['tag'] == t['tag'] for et in existing_tags[category]):
                            existing_tags[category].append(t)

                profile['tags'] = existing_tags
                profile['last_tagged'] = datetime.now().isoformat()
                self._save_visitor_profile(user_id, profile)

            # ★ 同步到数据库（如果有数据库连接）
            try:
                from db_manager import MemberDAO
                dao = MemberDAO()
                # 无论是否匹配到标签，都确保会员记录存在
                member = dao.get_or_create_by_openid(openid_wx=user_id, source='wxwork')
                if member:
                    if tags:
                        new_tag_names = [t['tag'] for t in tags]
                        # 合并已有标签（避免覆盖）
                        existing = member.get('tags') or []
                        if isinstance(existing, str):
                            try:
                                existing = json.loads(existing)
                            except Exception:
                                existing = []
                        if not isinstance(existing, list):
                            existing = []
                        merged = list(dict.fromkeys(existing + new_tag_names))  # 去重保序
                        dao.update_tags(member['id'], merged)
                        print(f"[标签] 已同步到数据库, member_id={member['id']}, tags={merged}")
                    else:
                        print(f"[标签] 会员已存在, member_id={member['id']}, 本次无新标签")
            except Exception as db_err:
                # 数据库不可用时仅本地存储，不影响主流程
                print(f"[标签] 数据库同步跳过: {db_err}")

        except Exception as e:
            print(f"[标签] 自动打标签失败（非阻塞）: {e}")

    def _load_visitor_profile(self, user_id):
        """加载游客档案"""
        profile_path = os.path.join(
            os.path.dirname(BASE_DIR),
            'data/visitors',
            f'{user_id}.json'
        )
        if os.path.exists(profile_path):
            with open(profile_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'visitor_id': user_id,
            'first_visit': datetime.now().isoformat(),
            'total_sessions': 0,
            'total_messages': 0,
            'tags': {}
        }

    def _save_visitor_profile(self, user_id, profile):
        """保存游客档案"""
        profile_path = os.path.join(
            os.path.dirname(BASE_DIR),
            'data/visitors',
            f'{user_id}.json'
        )
        os.makedirs(os.path.dirname(profile_path), exist_ok=True)
        with open(profile_path, 'w', encoding='utf-8') as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)

    def _update_visitor_profile(self, user_id, event_type):
        """更新游客档案"""
        profile = self._load_visitor_profile(user_id)

        # 更新字段
        profile['last_active'] = datetime.now().isoformat()

        if event_type == 'session_start':
            profile['total_sessions'] = profile.get('total_sessions', 0) + 1

        profile['total_messages'] = profile.get('total_messages', 0) + 1

        # 保存档案
        self._save_visitor_profile(user_id, profile)
    
    def _extract_and_save_merchants(self, user_id, message):
        """提取并保存商户提及"""
        # 常见商户关键词（后续可从知识库加载）
        merchant_keywords = [
            "星巴克", "肯德基", "麦当劳", "汉堡王",
            "优衣库", "万达", "屈臣氏", "Nike", "Adidas",
            "电影院", "KTV", "健身房", "超市"
        ]
        
        mentioned = []
        for merchant in merchant_keywords:
            if merchant in message:
                mentioned.append(merchant)
        
        if mentioned:
            # 使用记忆系统记录商户
            for merchant in mentioned:
                self.memory_system.add_merchant_mention(user_id, merchant)


def handle_wechat_callback(request_data):
    """处理企业微信回调请求"""
    bot = WeChatWorkBot()
    
    # 验证URL（首次配置时）
    if 'signature' in request_data:
        signature = request_data.get('signature')
        timestamp = request_data.get('timestamp')
        nonce = request_data.get('nonce')
        echostr = request_data.get('echostr')
        
        if echostr:
            return bot.verify_callback(signature, timestamp, nonce, echostr)
    
    # 处理消息
    if 'xml' in request_data:
        xml_data = request_data['xml']
        msg = bot.parse_message(xml_data)
        
        if msg:
            user_id = msg['from_user']
            content = msg['content']
            
            response = bot.process_message(user_id, content)
            
            return bot.create_response(user_id, response)
    
    return "success"


if __name__ == '__main__':
    # 测试
    bot = WeChatWorkBot()
    print("企业微信机器人初始化完成")
    print(f"欢迎语长度: {len(bot.welcome_message)} 字符")
