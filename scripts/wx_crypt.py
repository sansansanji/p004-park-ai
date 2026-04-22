# -*- coding: utf-8 -*-
"""
企业微信消息加解密工具
支持安全模式的回调URL验证和消息加解密
"""

import base64
import hashlib
import struct
import os
from Crypto.Cipher import AES


class WXBizMsgCrypt:
    """企业微信消息加解密"""

    def __init__(self, token, encoding_aes_key, corp_id):
        self.token = token
        self.corp_id = corp_id
        # EncodingAESKey 补一个 = 后 base64 解码，得到 32 字节 AES key
        self.aes_key = base64.b64decode(encoding_aes_key + '=')

    # ──────────────────────────────────────────
    # 验签
    # ──────────────────────────────────────────

    def _sign(self, *args):
        """sha1 对多个字符串排序后拼接计算签名"""
        tmp = sorted(args)
        return hashlib.sha1(''.join(tmp).encode('utf-8')).hexdigest()

    def verify_url(self, msg_signature, timestamp, nonce, echostr):
        """
        验证回调 URL（GET 请求）
        :return: (ok, decrypted_echostr_or_error_msg)
        """
        # 1. 验签
        sign = self._sign(self.token, timestamp, nonce, echostr)
        if sign != msg_signature:
            return False, '签名验证失败'

        # 2. 解密 echostr
        try:
            plain = self._decrypt(echostr)
            return True, plain
        except Exception as e:
            return False, f'解密失败: {e}'

    # ──────────────────────────────────────────
    # AES 解密
    # ──────────────────────────────────────────

    def _decrypt(self, encrypted_text):
        """解密密文，返回明文字符串"""
        cipher = AES.new(self.aes_key, AES.MODE_CBC, self.aes_key[:16])
        plain = cipher.decrypt(base64.b64decode(encrypted_text))

        # 去掉 PKCS#7 padding
        pad = plain[-1]
        plain = plain[:-pad]

        # 格式：random(16B) + msg_len(4B) + msg + corp_id
        msg_len = struct.unpack('>I', plain[16:20])[0]
        msg = plain[20: 20 + msg_len]
        return msg.decode('utf-8')

    # ──────────────────────────────────────────
    # 消息解密（POST 请求）
    # ──────────────────────────────────────────

    def decrypt_message(self, msg_signature, timestamp, nonce, encrypt_text):
        """
        解密收到的消息体中的 Encrypt 字段
        :return: (ok, plain_text_or_error)
        """
        sign = self._sign(self.token, timestamp, nonce, encrypt_text)
        if sign != msg_signature:
            return False, '签名验证失败'
        try:
            return True, self._decrypt(encrypt_text)
        except Exception as e:
            return False, f'解密失败: {e}'

    # ──────────────────────────────────────────
    # AES 加密（回复消息用）
    # ──────────────────────────────────────────

    def _encrypt(self, plain_text):
        """加密明文，返回 base64 密文"""
        # 格式：random(16B) + msg_len(4B) + msg + corp_id
        random_str = os.urandom(16)
        msg_bytes = plain_text.encode('utf-8')
        corp_id_bytes = self.corp_id.encode('utf-8')
        msg_len = struct.pack('>I', len(msg_bytes))
        content = random_str + msg_len + msg_bytes + corp_id_bytes

        # PKCS#7 padding 到 32 字节倍数
        block_size = 32
        pad_len = block_size - len(content) % block_size
        content += bytes([pad_len] * pad_len)

        cipher = AES.new(self.aes_key, AES.MODE_CBC, self.aes_key[:16])
        return base64.b64encode(cipher.encrypt(content)).decode('utf-8')

    def encrypt_message(self, plain_xml, timestamp, nonce):
        """
        加密回复消息，返回完整的加密 XML 字符串
        :return: (ok, encrypted_xml_or_error)
        """
        try:
            encrypt_text = self._encrypt(plain_xml)
            sign = self._sign(self.token, timestamp, nonce, encrypt_text)
            xml = (
                '<xml>'
                f'<Encrypt><![CDATA[{encrypt_text}]]></Encrypt>'
                f'<MsgSignature><![CDATA[{sign}]]></MsgSignature>'
                f'<TimeStamp>{timestamp}</TimeStamp>'
                f'<Nonce><![CDATA[{nonce}]]></Nonce>'
                '</xml>'
            )
            return True, xml
        except Exception as e:
            return False, f'加密失败: {e}'
