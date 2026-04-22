# -*- coding: utf-8 -*-
"""
数据库连接与操作层
支持 MySQL，提供统一的 CRUD 接口
"""

import os
import sys
import json
import logging
from datetime import datetime, date
from contextlib import contextmanager

try:
    import pymysql
    from pymysql.cursors import DictCursor
except ImportError:
    pymysql = None

import yaml

logger = logging.getLogger(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_DIR = os.path.join(BASE_DIR, 'config')


def load_db_config():
    """加载数据库配置"""
    config_file = os.path.join(CONFIG_DIR, 'database.yaml')
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f).get('database', {})
    # 环境变量兜底
    return {
        'host': os.environ.get('DB_HOST', '127.0.0.1'),
        'port': int(os.environ.get('DB_PORT', 3306)),
        'user': os.environ.get('DB_USER', 'root'),
        'password': os.environ.get('DB_PASSWORD', ''),
        'database': os.environ.get('DB_NAME', 'park_ai'),
        'charset': 'utf8mb4',
    }


class Database:
    """数据库操作类"""

    def __init__(self):
        self.config = load_db_config()
        self._conn = None

    def get_connection(self):
        """获取数据库连接（自动重连）"""
        if pymysql is None:
            raise RuntimeError("pymysql 未安装，请运行: pip install pymysql")
        if self._conn is None or not self._conn.open:
            self._conn = pymysql.connect(
                host=self.config.get('host', '127.0.0.1'),
                port=self.config.get('port', 3306),
                user=self.config.get('user', 'root'),
                password=self.config.get('password', ''),
                database=self.config.get('database', 'park_ai'),
                charset='utf8mb4',
                cursorclass=DictCursor,
                autocommit=False,
            )
        return self._conn

    @contextmanager
    def cursor(self, auto_commit=True):
        """上下文管理器，自动提交/回滚"""
        conn = self.get_connection()
        cur = conn.cursor()
        try:
            yield cur
            if auto_commit:
                conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"DB error: {e}")
            raise
        finally:
            cur.close()

    def execute(self, sql, args=None):
        """执行单条 SQL"""
        with self.cursor() as cur:
            cur.execute(sql, args)
            return cur.lastrowid

    def query_one(self, sql, args=None):
        """查询单条记录"""
        with self.cursor(auto_commit=False) as cur:
            cur.execute(sql, args)
            return cur.fetchone()

    def query_all(self, sql, args=None):
        """查询多条记录"""
        with self.cursor(auto_commit=False) as cur:
            cur.execute(sql, args)
            return cur.fetchall()

    def close(self):
        if self._conn and self._conn.open:
            self._conn.close()


# 全局单例
_db_instance = None

def get_db() -> Database:
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance


# =============================================
# 会员相关操作
# =============================================

class MemberDAO:

    # 需要从 JSON 字符串解析为 Python 对象的字段
    _JSON_FIELDS = ['tags', 'coupons']

    def __init__(self):
        self.db = get_db()

    @staticmethod
    def _parse_member(member):
        """解析会员记录中的 JSON 字段，确保前端收到正确的数据类型"""
        if not member:
            return member
        for field in MemberDAO._JSON_FIELDS:
            val = member.get(field)
            if isinstance(val, str):
                try:
                    member[field] = json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    member[field] = []
            elif val is None:
                member[field] = []
        return member

    def get_or_create_by_openid(self, openid_mp=None, openid_wx=None, source='mp', **kwargs):
        """根据openid获取或创建会员"""
        if openid_mp:
            member = self.db.query_one(
                "SELECT * FROM members WHERE openid_mp = %s", (openid_mp,)
            )
        elif openid_wx:
            member = self.db.query_one(
                "SELECT * FROM members WHERE openid_wx = %s", (openid_wx,)
            )
        else:
            return None

        if member:
            return self._parse_member(member)

        # 创建新会员
        member_id = self.db.execute(
            """INSERT INTO members (openid_mp, openid_wx, source, nickname, avatar_url)
               VALUES (%s, %s, %s, %s, %s)""",
            (openid_mp, openid_wx, source,
             kwargs.get('nickname'), kwargs.get('avatar_url'))
        )
        # 记录入园
        self.add_visit_log(member_id, source)
        return self.get_by_id(member_id)

    def get_by_id(self, member_id):
        return self._parse_member(self.db.query_one("SELECT * FROM members WHERE id = %s", (member_id,)))

    def get_by_phone(self, phone):
        return self._parse_member(self.db.query_one("SELECT * FROM members WHERE phone = %s", (phone,)))

    def bind_phone(self, member_id, phone):
        """绑定手机号"""
        self.db.execute(
            "UPDATE members SET phone = %s WHERE id = %s",
            (phone, member_id)
        )

    def update_tags(self, member_id, tags: list):
        """更新标签"""
        self.db.execute(
            "UPDATE members SET tags = %s WHERE id = %s",
            (json.dumps(tags, ensure_ascii=False), member_id)
        )

    def add_visit_log(self, member_id, source=None):
        """记录入园"""
        today = date.today()
        # 今天已经入园过了就不重复记录
        existing = self.db.query_one(
            "SELECT id FROM visit_logs WHERE member_id = %s AND visit_date = %s",
            (member_id, today)
        )
        if not existing:
            self.db.execute(
                "INSERT INTO visit_logs (member_id, source, visit_date) VALUES (%s, %s, %s)",
                (member_id, source, today)
            )
            self.db.execute(
                "UPDATE members SET visit_count = visit_count + 1 WHERE id = %s",
                (member_id,)
            )

    def list_members(self, page=1, page_size=20, keyword=None, source=None, level=None):
        """分页查询会员列表"""
        conditions = []
        args = []
        if keyword:
            conditions.append("(nickname LIKE %s OR phone LIKE %s)")
            args.extend([f'%{keyword}%', f'%{keyword}%'])
        if source:
            conditions.append("source = %s")
            args.append(source)
        if level:
            conditions.append("level = %s")
            args.append(level)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        offset = (page - 1) * page_size

        total = self.db.query_one(
            f"SELECT COUNT(*) as cnt FROM members {where}", args
        )['cnt']

        items = self.db.query_all(
            f"SELECT * FROM members {where} ORDER BY created_at DESC LIMIT %s OFFSET %s",
            args + [page_size, offset]
        )
        # 解析每条记录的 JSON 字段
        items = [self._parse_member(m) for m in items]
        return {'total': total, 'items': items, 'page': page, 'page_size': page_size}

    def get_today_stats(self):
        """获取今日统计"""
        today = date.today()
        return {
            'today_visits': self.db.query_one(
                "SELECT COUNT(*) as cnt FROM visit_logs WHERE visit_date = %s", (today,)
            )['cnt'],
            'today_new_members': self.db.query_one(
                "SELECT COUNT(*) as cnt FROM members WHERE DATE(created_at) = %s", (today,)
            )['cnt'],
            'total_members': self.db.query_one(
                "SELECT COUNT(*) as cnt FROM members", ()
            )['cnt'],
        }

    def create(self, data: dict):
        """创建会员"""
        return self.db.execute(
            """INSERT INTO members (phone, nickname, level, source, status, created_at)
               VALUES (%s, %s, %s, %s, %s, NOW())""",
            (data.get('phone'), data.get('nickname'), data.get('level', 'normal'),
             data.get('source', 'mp'), data.get('status', 1))
        )

    # 更新会员时允许的字段白名单（防SQL注入）
    _ALLOWED_MEMBER_FIELDS = {'nickname', 'phone', 'level', 'source', 'status', 'note', 'tags', 'avatar_url', 'gender'}

    def update(self, member_id, data: dict):
        """更新会员"""
        safe_data = {k: v for k, v in data.items() if k in self._ALLOWED_MEMBER_FIELDS}
        if not safe_data:
            return
        sets = ', '.join([f"`{k}` = %s" for k in safe_data.keys()])
        args = list(safe_data.values()) + [member_id]
        self.db.execute(f"UPDATE members SET {sets} WHERE id = %s", args)

    def delete(self, member_id):
        """删除会员"""
        self.db.execute("DELETE FROM members WHERE id = %s", (member_id,))


# =============================================
# 商户相关操作
# =============================================

class MerchantDAO:

    def __init__(self):
        self.db = get_db()

    # 更新商户时允许的字段白名单
    _ALLOWED_MERCHANT_FIELDS = {'name', 'category', 'description', 'location', 'lat', 'lng',
                                 'floor', 'open_hours', 'phone', 'cover_img', 'purchase_url',
                                 'sort_order', 'status'}

    def list_all(self, category=None, status=1):
        conditions = ["status = %s"]
        args = [status]
        if category:
            conditions.append("category = %s")
            args.append(category)
        where = f"WHERE {' AND '.join(conditions)}"
        return self.db.query_all(
            f"SELECT * FROM merchants {where} ORDER BY sort_order, id", args
        )

    def get_by_id(self, merchant_id):
        return self.db.query_one(
            "SELECT * FROM merchants WHERE id = %s", (merchant_id,)
        )

    def create(self, data: dict):
        return self.db.execute(
            """INSERT INTO merchants
               (name, category, description, location, lat, lng, floor,
                open_hours, phone, cover_img, purchase_url, sort_order)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (data.get('name'), data.get('category'), data.get('description'),
             data.get('location'), data.get('lat'), data.get('lng'),
             data.get('floor'), data.get('open_hours'), data.get('phone'),
             data.get('cover_img'), data.get('purchase_url'), data.get('sort_order', 0))
        )

    def update(self, merchant_id, data: dict):
        """更新商户"""
        safe_data = {k: v for k, v in data.items() if k in self._ALLOWED_MERCHANT_FIELDS}
        if not safe_data:
            return
        sets = ', '.join([f"`{k}` = %s" for k in safe_data.keys()])
        args = list(safe_data.values()) + [merchant_id]
        self.db.execute(f"UPDATE merchants SET {sets} WHERE id = %s", args)

    def delete(self, merchant_id):
        self.db.execute("UPDATE merchants SET status = 0 WHERE id = %s", (merchant_id,))


# =============================================
# 活动相关操作
# =============================================

class ActivityDAO:

    def __init__(self):
        self.db = get_db()

    def list_active(self):
        """获取进行中的活动"""
        now = datetime.now()
        return self.db.query_all(
            "SELECT * FROM activities WHERE status = 'active' AND start_at <= %s AND end_at >= %s",
            (now, now)
        )

    def list_all(self, page=1, page_size=20, status=None):
        conditions = []
        args = []
        if status:
            conditions.append("status = %s")
            args.append(status)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        offset = (page - 1) * page_size
        total = self.db.query_one(f"SELECT COUNT(*) as cnt FROM activities {where}", args)['cnt']
        items = self.db.query_all(
            f"SELECT * FROM activities {where} ORDER BY start_at DESC LIMIT %s OFFSET %s",
            args + [page_size, offset]
        )
        return {'total': total, 'items': items}

    def create(self, data: dict):
        return self.db.execute(
            """INSERT INTO activities
               (title, subtitle, content, cover_img, start_at, end_at, location,
                merchant_id, max_people, status, push_enabled, push_channels, created_by)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (data['title'], data.get('subtitle'), data.get('content'),
             data.get('cover_img'), data['start_at'], data['end_at'],
             data.get('location'), data.get('merchant_id'), data.get('max_people', 0),
             data.get('status', 'draft'), data.get('push_enabled', 1),
             json.dumps(data.get('push_channels', ['mp', 'wxwork'])),
             data.get('created_by'))
        )

    # 更新活动时允许的字段白名单
    _ALLOWED_ACTIVITY_FIELDS = {'title', 'subtitle', 'content', 'cover_img', 'start_at',
                                  'end_at', 'location', 'merchant_id', 'max_people',
                                  'status', 'push_enabled', 'push_channels'}

    def update(self, activity_id, data: dict):
        """更新活动"""
        safe_data = {k: v for k, v in data.items() if k in self._ALLOWED_ACTIVITY_FIELDS}
        if not safe_data:
            return
        sets = ', '.join([f"`{k}` = %s" for k in safe_data.keys()])
        args = list(safe_data.values()) + [activity_id]
        self.db.execute(f"UPDATE activities SET {sets} WHERE id = %s", args)

    def get_by_id(self, activity_id):
        return self.db.query_one("SELECT * FROM activities WHERE id = %s", (activity_id,))

    def delete(self, activity_id):
        """删除活动"""
        self.db.execute("DELETE FROM activities WHERE id = %s", (activity_id,))


# =============================================
# 优惠券相关操作
# =============================================

class CouponDAO:

    def __init__(self):
        self.db = get_db()

    def issue_coupon(self, template_id, member_id):
        """发放优惠券"""
        import secrets
        template = self.db.query_one(
            "SELECT * FROM coupon_templates WHERE id = %s AND status = 1", (template_id,)
        )
        if not template:
            return None, "优惠券不存在或已停用"

        # 生成唯一券码
        code = secrets.token_hex(8).upper()
        # 计算过期时间
        from datetime import timedelta
        if template['expire_at']:
            expire_at = template['expire_at']
        else:
            expire_at = datetime.now() + timedelta(days=template['valid_days'])

        coupon_id = self.db.execute(
            """INSERT INTO coupons (code, template_id, member_id, expire_at)
               VALUES (%s, %s, %s, %s)""",
            (code, template_id, member_id, expire_at)
        )
        # 更新使用数量
        self.db.execute(
            "UPDATE coupon_templates SET used_count = used_count + 1 WHERE id = %s",
            (template_id,)
        )
        return coupon_id, code

    def verify_coupon(self, code, merchant_id=None):
        """核销优惠券"""
        coupon = self.db.query_one(
            """SELECT c.*, t.name, t.type, t.value, t.min_amount
               FROM coupons c JOIN coupon_templates t ON c.template_id = t.id
               WHERE c.code = %s""",
            (code,)
        )
        if not coupon:
            return False, "券码不存在"
        if coupon['status'] == 'used':
            return False, "优惠券已使用"
        if coupon['status'] == 'expired' or coupon['expire_at'] < datetime.now():
            return False, "优惠券已过期"

        self.db.execute(
            """UPDATE coupons SET status='used', used_at=%s, used_merchant_id=%s
               WHERE code=%s""",
            (datetime.now(), merchant_id, code)
        )
        return True, coupon

    def get_member_coupons(self, member_id, status=None):
        """获取会员优惠券列表"""
        sql = """SELECT c.*, t.name, t.type, t.value, t.description
                 FROM coupons c JOIN coupon_templates t ON c.template_id = t.id
                 WHERE c.member_id = %s"""
        args = [member_id]
        if status:
            sql += " AND c.status = %s"
            args.append(status)
        sql += " ORDER BY c.issued_at DESC"
        return self.db.query_all(sql, args)


# =============================================
# 推文相关操作
# =============================================

class ArticleDAO:

    def __init__(self):
        self.db = get_db()

    def create(self, data: dict):
        return self.db.execute(
            """INSERT INTO articles
               (title, content, summary, cover_img, source_type, source_id,
                status, platforms, publish_at, created_by)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (data['title'], data.get('content'), data.get('summary'),
             data.get('cover_img'), data.get('source_type'), data.get('source_id'),
             data.get('status', 'draft'),
             json.dumps(data.get('platforms', ['mp'])),
             data.get('publish_at'), data.get('created_by'))
        )

    def update_status(self, article_id, status, reviewed_by=None):
        self.db.execute(
            "UPDATE articles SET status=%s, reviewed_by=%s WHERE id=%s",
            (status, reviewed_by, article_id)
        )

    def list_all(self, page=1, page_size=20, status=None):
        conditions = []
        args = []
        if status:
            conditions.append("status = %s")
            args.append(status)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        offset = (page - 1) * page_size
        total = self.db.query_one(f"SELECT COUNT(*) as cnt FROM articles {where}", args)['cnt']
        items = self.db.query_all(
            f"SELECT * FROM articles {where} ORDER BY created_at DESC LIMIT %s OFFSET %s",
            args + [page_size, offset]
        )
        return {'total': total, 'items': items}


# =============================================
# 对话记录操作
# =============================================

class ChatLogDAO:

    def __init__(self):
        self.db = get_db()

    def save(self, session_id, role, content, member_id=None, channel=None,
             msg_type='text', open_kfid=None, is_human_reply=0, human_sender=None):
        """保存一条对话记录
        role: user / assistant / human
        is_human_reply: 1=人工回复, 0=AI回复
        human_sender: 人工回复者的企微 userid
        open_kfid: 企微客服账号ID
        """
        self.db.execute(
            """INSERT INTO chat_logs
               (member_id, session_id, channel, open_kfid, role, content,
                msg_type, is_human_reply, human_sender)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (member_id, session_id, channel, open_kfid, role, content,
             msg_type, is_human_reply, human_sender)
        )

    def get_session_history(self, session_id, limit=20):
        return self.db.query_all(
            """SELECT role, content, created_at FROM chat_logs
               WHERE session_id = %s ORDER BY created_at DESC LIMIT %s""",
            (session_id, limit)
        )

    def get_member_history(self, member_id, limit=50):
        return self.db.query_all(
            """SELECT * FROM chat_logs WHERE member_id = %s
               ORDER BY created_at DESC LIMIT %s""",
            (member_id, limit)
        )


# =============================================
# 系统配置操作
# =============================================

class ConfigDAO:

    def __init__(self):
        self.db = get_db()

    def get(self, key_name, default=None):
        """获取单个配置值"""
        row = self.db.query_one(
            "SELECT value FROM system_configs WHERE key_name = %s", (key_name,)
        )
        return row['value'] if row else default

    def set(self, key_name, value):
        """设置配置值"""
        self.db.execute(
            """INSERT INTO system_configs (key_name, value) VALUES (%s, %s)
               ON DUPLICATE KEY UPDATE value = %s""",
            (key_name, value, value)
        )

    def get_all(self):
        """获取所有配置"""
        rows = self.db.query_all("SELECT * FROM system_configs ORDER BY key_name")
        return {r['key_name']: r['value'] for r in rows}

    def get_by_prefix(self, prefix):
        """按前缀获取配置"""
        rows = self.db.query_all(
            "SELECT * FROM system_configs WHERE key_name LIKE %s ORDER BY key_name",
            (f'{prefix}%',)
        )
        return {r['key_name']: r['value'] for r in rows}


# =============================================
# 回复规则操作
# =============================================

class ReplyRuleDAO:

    def __init__(self):
        self.db = get_db()

    def list_all(self, is_active=None):
        """获取所有回复规则"""
        conditions = []
        args = []
        if is_active is not None:
            conditions.append("is_active = %s")
            args.append(is_active)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        return self.db.query_all(
            f"SELECT * FROM reply_rules {where} ORDER BY priority DESC, id ASC", args
        )

    def get_by_id(self, rule_id):
        return self.db.query_one("SELECT * FROM reply_rules WHERE id = %s", (rule_id,))

    def create(self, data: dict):
        return self.db.execute(
            """INSERT INTO reply_rules (keyword, reply, match_type, category, priority, is_active)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (data['keyword'], data['reply'], data.get('match_type', 'contains'),
             data.get('category', 'other'), data.get('priority', 0), data.get('is_active', 1))
        )

    def update(self, rule_id, data: dict):
        safe_data = {k: v for k, v in data.items() if k in ('keyword', 'reply', 'match_type', 'category', 'priority', 'is_active')}
        if not safe_data:
            return
        sets = ', '.join([f"`{k}` = %s" for k in safe_data.keys()])
        args = list(safe_data.values()) + [rule_id]
        self.db.execute(f"UPDATE reply_rules SET {sets} WHERE id = %s", args)

    def delete(self, rule_id):
        self.db.execute("DELETE FROM reply_rules WHERE id = %s", (rule_id,))

    def match(self, user_message):
        """匹配用户消息，返回回复内容（优先级高的优先）"""
        rules = self.list_all(is_active=1)
        for rule in rules:
            keyword = rule['keyword']
            match_type = rule['match_type']
            if match_type == 'exact' and user_message.strip() == keyword:
                return rule['reply']
            elif match_type == 'contains' and keyword in user_message:
                return rule['reply']
            elif match_type == 'regex':
                import re
                try:
                    if re.search(keyword, user_message):
                        return rule['reply']
                except re.error:
                    pass
        return None


# =============================================
# 标签规则操作
# =============================================

class TagRuleDAO:

    def __init__(self):
        self.db = get_db()

    def list_all(self, is_active=None):
        conditions = []
        args = []
        if is_active is not None:
            conditions.append("is_active = %s")
            args.append(is_active)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        return self.db.query_all(
            f"SELECT * FROM tag_rules {where} ORDER BY tag_name, id ASC", args
        )

    def get_by_id(self, rule_id):
        return self.db.query_one("SELECT * FROM tag_rules WHERE id = %s", (rule_id,))

    def create(self, data: dict):
        return self.db.execute(
            """INSERT INTO tag_rules (tag_name, keyword, match_type, is_active)
               VALUES (%s, %s, %s, %s)""",
            (data['tag_name'], data['keyword'], data.get('match_type', 'contains'),
             data.get('is_active', 1))
        )

    def update(self, rule_id, data: dict):
        safe_data = {k: v for k, v in data.items() if k in ('tag_name', 'keyword', 'match_type', 'is_active')}
        if not safe_data:
            return
        sets = ', '.join([f"`{k}` = %s" for k in safe_data.keys()])
        args = list(safe_data.values()) + [rule_id]
        self.db.execute(f"UPDATE tag_rules SET {sets} WHERE id = %s", args)

    def delete(self, rule_id):
        self.db.execute("DELETE FROM tag_rules WHERE id = %s", (rule_id,))

    def match_tags(self, user_message):
        """匹配用户消息，返回应打的标签列表"""
        rules = self.list_all(is_active=1)
        matched = []
        for rule in rules:
            keyword = rule['keyword']
            match_type = rule['match_type']
            hit = False
            if match_type == 'exact' and user_message.strip() == keyword:
                hit = True
            elif match_type == 'contains' and keyword in user_message:
                hit = True
            elif match_type == 'regex':
                import re
                try:
                    if re.search(keyword, user_message):
                        hit = True
                except re.error:
                    pass
            if hit and rule['tag_name'] not in matched:
                matched.append(rule['tag_name'])
        return matched
