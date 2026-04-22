# -*- coding: utf-8 -*-
"""
园区AI助手 - Web 服务统一入口（生产运行此文件）

路由分工：
  /wechat/callback        企业微信游客端（安全模式，支持消息加解密）
  /admin/wechat/callback  企业微信管理端（安全模式）
  /mp/callback            微信公众号
  /admin                  管理后台前端
  /api/*                  管理后台 API（通过 Blueprint 导入 admin_api）
  /health                 健康检查
"""

import os
import sys
import json
import yaml

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from flask import Flask, request, Response, send_from_directory

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(BASE_DIR), 'admin_frontend'))
# ⚠️ secret_key 必须在所有 Blueprint 注册之前设置
app.secret_key = os.environ.get('SECRET_KEY', 'park-ai-admin-secret-2026')

# ─────────────────────────────────────────────
# 注册管理后台 Blueprint（共享同一 app 的 session）
# ─────────────────────────────────────────────
try:
    from admin_api import admin_bp
    app.register_blueprint(admin_bp)
    print("[管理后台] Blueprint 注册成功")
except Exception as e:
    print(f"[警告] 管理后台 Blueprint 加载失败：{e}")

# ─────────────────────────────────────────────
# 加载微信公众号处理器
# ─────────────────────────────────────────────
try:
    from mp_wechat import mp_handler
    _mp_ok = True
except Exception as e:
    print(f"[警告] 公众号模块加载失败：{e}")
    _mp_ok = False

# ─────────────────────────────────────────────
# 企微机器人（懒加载，避免启动时配置不完整报错）
# ─────────────────────────────────────────────
_visitor_bot = None
_admin_bot = None

def get_visitor_bot():
    global _visitor_bot
    if _visitor_bot is None:
        from wechat_bot import WeChatWorkBot
        _visitor_bot = WeChatWorkBot()
    return _visitor_bot

def get_admin_bot():
    global _admin_bot
    if _admin_bot is None:
        from admin_bot import AdminBot
        _admin_bot = AdminBot()
    return _admin_bot

# ─────────────────────────────────────────────
# 加载企微加解密工具（安全模式）
# ─────────────────────────────────────────────
def _get_visitor_crypt():
    """从配置文件读取游客端企微的加密参数，返回 WXBizMsgCrypt 实例"""
    try:
        from wx_crypt import WXBizMsgCrypt
        config_path = os.path.join(os.path.dirname(BASE_DIR), 'config', 'wechat_work.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f) or {}
        ww = cfg.get('wechat_work', {})
        token = ww.get('callback', {}).get('token', '')
        aes_key = ww.get('callback', {}).get('encoding_aes_key', '')
        corp_id = ww.get('corp_id', '')
        if token and aes_key and corp_id and aes_key != 'YOUR_ENCODING_AES_KEY':
            return WXBizMsgCrypt(token, aes_key, corp_id)
    except Exception as e:
        print(f"[企微加密] 初始化失败：{e}")
    return None

def _get_admin_crypt():
    """从配置文件读取管理端企微的加密参数，返回 WXBizMsgCrypt 实例"""
    try:
        from wx_crypt import WXBizMsgCrypt
        config_path = os.path.join(os.path.dirname(BASE_DIR), 'config', 'admin_wechat.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f) or {}
        ww = cfg.get('wechat_work', {})
        token = ww.get('callback', {}).get('token', '')
        aes_key = ww.get('callback', {}).get('encoding_aes_key', '')
        corp_id = ww.get('corp_id', '')
        if token and aes_key and corp_id and aes_key != 'YOUR_ENCODING_AES_KEY':
            return WXBizMsgCrypt(token, aes_key, corp_id)
    except Exception as e:
        print(f"[管理端加密] 初始化失败：{e}")
    return None


# ─────────────────────────────────────────────
# 游客端企微回调
# ─────────────────────────────────────────────

@app.route('/wechat/callback', methods=['GET', 'POST'])
def visitor_callback():
    if request.method == 'GET':
        msg_sig   = request.args.get('msg_signature', '')
        timestamp = request.args.get('timestamp', '')
        nonce     = request.args.get('nonce', '')
        echostr   = request.args.get('echostr', '')

        crypt = _get_visitor_crypt()
        if crypt:
            # 安全模式：解密 echostr
            ok, result = crypt.verify_url(msg_sig, timestamp, nonce, echostr)
            if ok:
                return Response(result, mimetype='text/plain')
            return Response(f'sign error: {result}', status=403, mimetype='text/plain')
        else:
            # 明文模式（兜底）
            bot = get_visitor_bot()
            result = bot.verify_callback(msg_sig or request.args.get('signature', ''),
                                         timestamp, nonce, echostr)
            return Response(result or '', mimetype='text/plain')

    # POST：接收并处理消息
    import xml.etree.ElementTree as ET
    import time as _time

    xml_data = request.data.decode('utf-8')
    timestamp = request.args.get('timestamp', str(int(_time.time())))
    nonce     = request.args.get('nonce', 'nonce')

    crypt = _get_visitor_crypt()
    if crypt:
        # 安全模式：先解密消息
        try:
            root = ET.fromstring(xml_data)
            encrypt_text = root.find('Encrypt').text
            msg_sig = request.args.get('msg_signature', '')
            ok, plain_xml = crypt.decrypt_message(msg_sig, timestamp, nonce, encrypt_text)
            if not ok:
                print(f"[企微] 消息解密失败：{plain_xml}")
                return Response('success', mimetype='text/plain')
            xml_data = plain_xml
        except Exception as e:
            print(f"[企微] 消息解密异常：{e}")
            return Response('success', mimetype='text/plain')

    import sys
    def log_main(s):
        sys.stderr.write(f"[MAIN] {s}\n")
        sys.stderr.flush()
    
    bot = get_visitor_bot()
    msg = bot.parse_message(xml_data)
    
    log_main(f"PARSED_MSG: {msg}")
    
    if msg:
        msg_type = msg.get('msg_type', '')
        event    = msg.get('event', '')
        
        log_main(f"MSG_TYPE={msg_type}, EVENT={event}")

        # 处理客服消息 (kf_msg_or_event)
        is_kf_msg = (msg_type == 'event' and event == 'kf_msg_or_event')
        log_main(f"IS_KF_MSG={is_kf_msg}")

        if is_kf_msg:
            log_main("ENTER: handle_kf_message")
            return handle_kf_message(msg, bot, crypt, timestamp, nonce)
        else:
            log_main("ENTER: handle_app_message")
            return handle_app_message(msg, bot, crypt, timestamp, nonce)
    else:
        log_main("PARSE_FAILED: msg is None")

    return Response('success', mimetype='text/plain')


def _get_member_id(user_id, source='wxwork'):
    """获取或创建会员ID，失败返回 None（非阻塞）"""
    try:
        from db_manager import MemberDAO
        member = MemberDAO().get_or_create_by_openid(openid_wx=user_id, source=source)
        return member['id'] if member else None
    except Exception:
        return None


def _save_chat_log(user_id, user_content, bot_reply, channel='wxwork_kf', open_kfid=None):
    """保存AI对话记录到数据库（非阻塞）"""
    try:
        from db_manager import ChatLogDAO
        chat_dao = ChatLogDAO()
        member_id = _get_member_id(user_id)
        session_id = user_id
        chat_dao.save(session_id, 'user', user_content,
                      member_id=member_id, channel=channel, open_kfid=open_kfid)
        chat_dao.save(session_id, 'assistant', bot_reply,
                      member_id=member_id, channel=channel, open_kfid=open_kfid)
        print(f"[对话记录] AI记录已保存: user={user_id[:10]}...")
    except Exception as e:
        print(f"[对话记录] 保存失败（非阻塞）: {e}")


def _save_human_chat_log(session_id, sender_userid, content, open_kfid=None):
    """保存人工回复记录到数据库（非阻塞）"""
    try:
        from db_manager import ChatLogDAO
        chat_dao = ChatLogDAO()
        member_id = _get_member_id(session_id)
        chat_dao.save(session_id, 'human', content,
                      member_id=member_id, channel='wxwork_kf',
                      open_kfid=open_kfid, is_human_reply=1,
                      human_sender=sender_userid)
        print(f"[对话记录] 人工回复已保存: sender={sender_userid}, session={session_id[:10]}...")
    except Exception as e:
        print(f"[对话记录] 人工回复保存失败（非阻塞）: {e}")


def _is_session_taken_over(session_id):
    """检查某个游客会话是否处于人工接管状态"""
    try:
        from db_manager import get_db
        db = get_db()
        row = db.query_one(
            "SELECT id FROM kf_takeover WHERE session_id=%s AND status='active'",
            (session_id,))
        return row is not None
    except Exception:
        return False  # 数据库不可用时默认不接管（AI正常回复）


def handle_kf_message(msg, bot, crypt, timestamp, nonce):
    """处理客服消息：增量拉取新消息 -> 处理 -> 发送回复"""
    import requests
    import time as _t
    import sys
    
    # ★ 持久化文件路径
    _kf_state_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'kf_state.json')
    
    def _load_kf_state():
        """从文件加载客服状态（cursors + processed）"""
        try:
            if os.path.exists(_kf_state_file):
                with open(_kf_state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                return state.get('cursors', {}), set(state.get('processed', []))
        except Exception as e:
            log_main(f"[KF] 状态加载失败: {e}")
        return {}, set()
    
    def _save_kf_state(cursors, processed):
        """保存客服状态到文件"""
        try:
            os.makedirs(os.path.dirname(_kf_state_file), exist_ok=True)
            # 只保留最近500条 msgid
            proc_list = list(processed)[-500:]
            with open(_kf_state_file, 'w', encoding='utf-8') as f:
                json.dump({'cursors': cursors, 'processed': proc_list}, f, ensure_ascii=False)
        except Exception as e:
            log_main(f"[KF] 状态保存失败: {e}")
    
    # ★ 每个 open_kfid 维护独立的 cursor，实现增量拉取
    if not hasattr(handle_kf_message, 'cursors'):
        handle_kf_message.cursors, handle_kf_message.processed = _load_kf_state()
    if not hasattr(handle_kf_message, 'last_call_time'):
        handle_kf_message.last_call_time = 0  # 上次处理时间，防抖
    
    # ★ 防抖：3秒内不重复拉取（避免回调重试导致重复处理）
    now = _t.time()
    if now - handle_kf_message.last_call_time < 3:
        log_main(f"[KF] 防抖跳过，距上次调用仅 {now - handle_kf_message.last_call_time:.1f}s")
        return Response('success', mimetype='text/plain')
    handle_kf_message.last_call_time = now
    
    # 用 stderr 输出，确保不被缓冲
    def log(s):
        sys.stderr.write(f"[KF] {s}\n")
        sys.stderr.flush()
    
    try:
        corp_id = bot.config.get('wechat_work', {}).get('corp_id', '')
        secret = bot.config.get('wechat_work', {}).get('agent', {}).get('secret', '')
        cb_token = msg.get('token', '')  # 回调中的token（sync_msg需要）
        open_kfid = msg.get('open_kfid', '')  # 客服账号ID
        
        log(f"START: corp_id={corp_id[:10]}..., cb_token={'有' if cb_token else '无'}, open_kfid={open_kfid}")
        
        # 1. 获取 access_token
        token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corp_id}&corpsecret={secret}"
        token_res = requests.get(token_url, timeout=10).json()
        log(f"TOKEN_RES: errcode={token_res.get('errcode')}, has_token={bool(token_res.get('access_token'))}")
        access_token = token_res.get('access_token')
        
        if not access_token:
            log(f"FAIL: 获取 access_token 失败, res={token_res}")
            return Response('success', mimetype='text/plain')
        
        # 2. 增量拉取消息（用 cursor 只拉新消息）
        sync_url = f"https://qyapi.weixin.qq.com/cgi-bin/kf/sync_msg?access_token={access_token}"
        
        # ★ 循环拉取，直到没有更多新消息
        total_new = 0
        while True:
            sync_payload = {
                "open_kfid": open_kfid,
                "limit": 1000
            }
            # ★ 传入回调 token（企微要求必须有，但某些版本可不传）
            if cb_token:
                sync_payload["token"] = cb_token
            # ★ 传入上次保存的 cursor，只拉新消息
            saved_cursor = handle_kf_message.cursors.get(open_kfid)
            if saved_cursor:
                sync_payload["cursor"] = saved_cursor
            
            log(f"SYNC_MSG: cursor={'有' if saved_cursor else '无(首次)'}, cb_token={'有' if cb_token else '无'}")
            sync_res = requests.post(sync_url, json=sync_payload, timeout=10).json()
            log(f"SYNC_RES: errcode={sync_res.get('errcode')}, msg_count={len(sync_res.get('msg_list', []))}, has_next_cursor={bool(sync_res.get('next_cursor'))}")
            
            if sync_res.get('errcode') != 0:
                log(f"FAIL: 拉取消息失败, errcode={sync_res.get('errcode')}, errmsg={sync_res.get('errmsg')}")
                # ★ 关键修复：如果 cursor 导致失败，清掉旧 cursor 重试一次
                if saved_cursor and sync_res.get('errcode') in (40001, 40014, 42001):
                    log(f"RETRY: 清除旧 cursor 重试")
                    handle_kf_message.cursors.pop(open_kfid, None)
                    # 不 continue，直接 break 避免无限循环，下次回调会重新拉取
                break
            
            msg_list = sync_res.get('msg_list', [])
            next_cursor = sync_res.get('next_cursor', '')
            
            # ★ 更新 cursor（即使 msg_list 为空也要更新，下次从这里开始）
            if next_cursor:
                handle_kf_message.cursors[open_kfid] = next_cursor
                _save_kf_state(handle_kf_message.cursors, handle_kf_message.processed)
            
            # 3. 处理每条消息
            for kf_msg in msg_list:
                msg_id = kf_msg.get('msgid', '')
                origin = kf_msg.get('origin', '')  # 3=微信客户发的, 4=系统事件, 5=接待人员发的
                msg_type = kf_msg.get('msgtype', '')
                external_userid = kf_msg.get('external_userid', '')
                
                log(f"MSG_ITEM: origin={origin}, msgtype={msg_type}, msgid={msg_id}, userid={external_userid[:15] if external_userid else 'N/A'}")
                
                # ★ 企微客服消息 origin 定义：
                #   3 = 微信客户发送的消息
                #   4 = 系统事件（进入/离开会话等）
                #   5 = 接待人员（企微后台员工）发送的消息
                
                if str(origin) == '5':
                    # ★★ 接待人员（人工）发送了消息 —— 记录到 chat_logs 的 human 角色
                    # 同时不需要 AI 再回复
                    if msg_id and msg_id in handle_kf_message.processed:
                        continue
                    if msg_type == 'text':
                        human_content = kf_msg.get('text', {}).get('content', '')
                        servicer_userid = kf_msg.get('servicer_userid', '')  # 接待人员 userid
                        log(f"HUMAN_REPLY: servicer={servicer_userid}, content={human_content[:50]}")
                        _save_human_chat_log(external_userid, servicer_userid,
                                             human_content, open_kfid=open_kfid)
                    if msg_id:
                        handle_kf_message.processed.add(msg_id)
                        if len(handle_kf_message.processed) > 1000:
                            handle_kf_message.processed = set(list(handle_kf_message.processed)[-500:])
                        _save_kf_state(handle_kf_message.cursors, handle_kf_message.processed)
                    total_new += 1
                    continue

                # 只处理游客发的消息（origin=3）
                if str(origin) not in ('3', 'customer'):
                    continue
                
                if msg_id and msg_id in handle_kf_message.processed:
                    continue
                
                if msg_type != 'text':
                    log(f"SKIP: non-text msgtype={msg_type}")
                    continue
                
                content = kf_msg.get('text', {}).get('content', '')
                log(f"USER_MSG: external_userid={external_userid}, content={content[:50]}")

                # ★★ 检查该游客会话是否正处于人工接管状态
                taken_over = _is_session_taken_over(external_userid)
                log(f"TAKEOVER_STATUS: session={external_userid[:15]}, taken_over={taken_over}")

                if taken_over:
                    # 人工接管中：只记录游客消息，不发 AI 回复
                    # 但要通知管理员：游客发了新消息
                    try:
                        from db_manager import ChatLogDAO
                        member_id = _get_member_id(external_userid)
                        ChatLogDAO().save(external_userid, 'user', content,
                                         member_id=member_id, channel='wxwork_kf',
                                         open_kfid=open_kfid)
                    except Exception as e:
                        log(f"TAKEOVER: 保存游客消息失败: {e}")
                    log(f"TAKEOVER: AI 静默，等待人工回复")
                    # 通知管理员：人工接管的会话有新消息
                    bot._notify_admin(external_userid, content, event='human_takeover_new_msg')
                    if msg_id:
                        handle_kf_message.processed.add(msg_id)
                        if len(handle_kf_message.processed) > 1000:
                            handle_kf_message.processed = set(list(handle_kf_message.processed)[-500:])
                        _save_kf_state(handle_kf_message.cursors, handle_kf_message.processed)
                    total_new += 1
                    continue

                # 正常模式：AI 处理并回复
                response_text = bot.process_message(external_userid, content)
                log(f"AI_REPLY: {response_text[:80] if response_text else 'EMPTY'}")

                # ★ 保存对话记录到数据库（非阻塞）
                _save_chat_log(external_userid, content, response_text,
                               channel='wxwork_kf', open_kfid=open_kfid)
                
                # 4. 发送回复
                send_url = f"https://qyapi.weixin.qq.com/cgi-bin/kf/send_msg?access_token={access_token}"
                send_payload = {
                    "touser": external_userid,
                    "open_kfid": open_kfid,
                    "msgtype": "text",
                    "text": {"content": response_text}
                }
                log(f"SEND_MSG: touser={external_userid}, open_kfid={open_kfid}")
                send_res = requests.post(send_url, json=send_payload, timeout=10).json()
                log(f"SEND_RES: errcode={send_res.get('errcode')}, errmsg={send_res.get('errmsg')}")
                if send_res.get('errcode') != 0:
                    log(f"FAIL: 发送消息失败, errcode={send_res.get('errcode')}, errmsg={send_res.get('errmsg')}")
                
                # ★ 标记已处理
                if msg_id:
                    handle_kf_message.processed.add(msg_id)
                    # 防止集合无限增长，只保留最近 1000 条
                    if len(handle_kf_message.processed) > 1000:
                        handle_kf_message.processed = set(list(handle_kf_message.processed)[-500:])
                    _save_kf_state(handle_kf_message.cursors, handle_kf_message.processed)
                
                total_new += 1
            
            # ★ 如果本次拉取不足1000条，说明没有更多了，退出循环
            if len(msg_list) < 1000:
                break
        
        log(f"END: 处理完成, 本次新处理 {total_new} 条消息")
    
    except Exception as e:
        log(f"EXCEPTION: {e}")
        import traceback
        log(traceback.format_exc())
    
    # 客服消息返回 success
    return Response('success', mimetype='text/plain')


def handle_app_message(msg, bot, crypt, timestamp, nonce):
    """处理普通应用消息：直接返回 XML"""
    import time as _t
    
    user_id  = msg['from_user']
    content  = msg.get('content', '')
    
    print(f"[企微应用] 收到消息: user={user_id}, content={content[:50]}")
    
    # 获取 AI 回复
    response_text = bot.process_message(user_id, content)
    
    corp_id = bot.config.get('wechat_work', {}).get('corp_id', '')
    plain_reply = (
        '<xml>'
        f'<ToUserName><![CDATA[{user_id}]]></ToUserName>'
        f'<FromUserName><![CDATA[{corp_id}]]></FromUserName>'
        f'<CreateTime>{int(_t.time())}</CreateTime>'
        '<MsgType><![CDATA[text]]></MsgType>'
        f'<Content><![CDATA[{response_text}]]></Content>'
        '</xml>'
    )
    
    if crypt:
        # 安全模式：加密回复
        ok, enc_xml = crypt.encrypt_message(plain_reply, timestamp, nonce)
        if ok:
            return Response(enc_xml, mimetype='application/xml')
        else:
            print(f"[企微] 回复加密失败：{enc_xml}")
            return Response('success', mimetype='text/plain')
    else:
        return Response(plain_reply, mimetype='application/xml')


# ─────────────────────────────────────────────
# 管理端企微回调
# ─────────────────────────────────────────────

@app.route('/admin/wechat/callback', methods=['GET', 'POST'])
def admin_callback():
    if request.method == 'GET':
        msg_sig   = request.args.get('msg_signature', '')
        timestamp = request.args.get('timestamp', '')
        nonce     = request.args.get('nonce', '')
        echostr   = request.args.get('echostr', '')

        crypt = _get_admin_crypt()
        if crypt:
            ok, result = crypt.verify_url(msg_sig, timestamp, nonce, echostr)
            if ok:
                return Response(result, mimetype='text/plain')
            return Response(f'sign error: {result}', status=403, mimetype='text/plain')
        else:
            bot = get_admin_bot()
            result = bot.verify_callback(msg_sig or request.args.get('signature', ''),
                                         timestamp, nonce, echostr)
            return Response(result or '', mimetype='text/plain')

    xml_data = request.data.decode('utf-8')

    crypt = _get_admin_crypt()
    if crypt:
        import xml.etree.ElementTree as ET
        try:
            root = ET.fromstring(xml_data)
            encrypt_text = root.find('Encrypt').text
            msg_sig   = request.args.get('msg_signature', '')
            timestamp = request.args.get('timestamp', '')
            nonce     = request.args.get('nonce', '')
            ok, plain_xml = crypt.decrypt_message(msg_sig, timestamp, nonce, encrypt_text)
            if not ok:
                return Response('success', mimetype='text/plain')
            xml_data = plain_xml
        except Exception as e:
            print(f"[管理端企微] 消息解密失败：{e}")
            return Response('success', mimetype='text/plain')

    bot = get_admin_bot()
    msg = bot.parse_message(xml_data)
    if msg:
        user_id  = msg['from_user']
        content  = msg.get('content', '')
        response = bot.process_message(user_id, content)
        return Response(bot.create_response(user_id, response), mimetype='application/xml')

    return Response('success', mimetype='text/plain')


# ─────────────────────────────────────────────
# 微信公众号回调
# ─────────────────────────────────────────────

@app.route('/mp/callback', methods=['GET', 'POST'])
def mp_callback():
    if not _mp_ok:
        return Response('mp module not loaded', status=503)
    if request.method == 'GET':
        result = mp_handler.handle_verify(request.args)
        return Response(result, mimetype='text/plain')
    xml_data = request.data.decode('utf-8')
    reply = mp_handler.handle_message(xml_data)
    return Response(reply or 'success', mimetype='application/xml')


# ─────────────────────────────────────────────
# 游客端 H5 页面
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# 健康检查
# ─────────────────────────────────────────────

@app.route('/health', methods=['GET'])
def health():
    return {'status': 'ok', 'service': '园区AI助手'}, 200


# ─────────────────────────────────────────────
# 启动入口
# ─────────────────────────────────────────────

if __name__ == '__main__':
    import io
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    config_path = os.path.join(os.path.dirname(BASE_DIR), 'config', 'system.yaml')
    host = '0.0.0.0'
    port = 8080
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f) or {}
        host = cfg.get('server', {}).get('host', host)
        port = cfg.get('server', {}).get('port', port)

    print("=" * 60)
    print("  园区AI助手 - 统一入口 (app.py)")
    print(f"  游客端企微回调: http://0.0.0.0:{port}/wechat/callback")
    print(f"  管理端企微回调: http://0.0.0.0:{port}/admin/wechat/callback")
    print(f"  公众号回调:     http://0.0.0.0:{port}/mp/callback")
    print(f"  管理后台:       http://0.0.0.0:{port}/admin")
    print(f"  游客端H5:       http://0.0.0.0:{port}/h5")
    print(f"  健康检查:       http://0.0.0.0:{port}/health")
    print("=" * 60)
    app.run(host=host, port=port, debug=False)
