-- 园区AI助手 数据库设计
-- 数据库：MySQL 8.0+
-- 字符集：utf8mb4

CREATE DATABASE IF NOT EXISTS park_ai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE park_ai;

-- =============================================
-- 1. 会员表
-- =============================================
CREATE TABLE IF NOT EXISTS members (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    openid_mp   VARCHAR(64)  DEFAULT NULL COMMENT '公众号openid',
    openid_wx   VARCHAR(64)  DEFAULT NULL COMMENT '企微userid',
    phone       VARCHAR(20)  DEFAULT NULL COMMENT '手机号（绑定后填写）',
    nickname    VARCHAR(64)  DEFAULT NULL COMMENT '昵称',
    avatar_url  VARCHAR(512) DEFAULT NULL COMMENT '头像URL',
    gender      TINYINT      DEFAULT 0    COMMENT '性别 0未知 1男 2女',
    source      VARCHAR(20)  DEFAULT NULL COMMENT '来源渠道 mp/wxwork',
    level       VARCHAR(20)  DEFAULT 'normal' COMMENT '会员等级 normal/vip/svip',
    tags        JSON         DEFAULT NULL COMMENT '标签列表 ["餐饮","亲子"]',
    note        TEXT         DEFAULT NULL COMMENT '管理员备注',
    visit_count INT          DEFAULT 0    COMMENT '累计入园次数',
    created_at  DATETIME     DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_openid_mp (openid_mp),
    UNIQUE KEY uq_openid_wx (openid_wx),
    UNIQUE KEY uq_phone (phone),
    KEY idx_source (source),
    KEY idx_level (level)
) COMMENT='会员表';

-- =============================================
-- 2. 入园记录表
-- =============================================
CREATE TABLE IF NOT EXISTS visit_logs (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    member_id   BIGINT UNSIGNED NOT NULL COMMENT '会员ID',
    source      VARCHAR(20)  DEFAULT NULL COMMENT '入园渠道',
    visit_date  DATE         NOT NULL     COMMENT '入园日期',
    entered_at  DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '入园时间',
    remark      VARCHAR(256) DEFAULT NULL,
    KEY idx_member (member_id),
    KEY idx_date (visit_date)
) COMMENT='入园记录';

-- =============================================
-- 3. 商户表
-- =============================================
CREATE TABLE IF NOT EXISTS merchants (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(64)  NOT NULL     COMMENT '商户名称',
    category    VARCHAR(32)  DEFAULT NULL COMMENT '分类 餐饮/购物/娱乐/亲子',
    description TEXT         DEFAULT NULL COMMENT '简介',
    location    VARCHAR(128) DEFAULT NULL COMMENT '位置描述',
    lat         DECIMAL(10,7) DEFAULT NULL COMMENT '纬度',
    lng         DECIMAL(10,7) DEFAULT NULL COMMENT '经度',
    floor       VARCHAR(16)  DEFAULT NULL COMMENT '楼层',
    open_hours  VARCHAR(64)  DEFAULT NULL COMMENT '营业时间',
    phone       VARCHAR(32)  DEFAULT NULL COMMENT '联系电话',
    cover_img   VARCHAR(512) DEFAULT NULL COMMENT '封面图URL',
    purchase_url VARCHAR(512) DEFAULT NULL COMMENT '购买链接',
    status      TINYINT      DEFAULT 1    COMMENT '状态 1正常 0下架',
    sort_order  INT          DEFAULT 0    COMMENT '排序',
    created_at  DATETIME     DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_category (category),
    KEY idx_status (status)
) COMMENT='商户表';

-- =============================================
-- 4. 优惠券模板表
-- =============================================
CREATE TABLE IF NOT EXISTS coupon_templates (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(64)  NOT NULL     COMMENT '优惠券名称',
    type        VARCHAR(20)  NOT NULL     COMMENT '类型 discount/cash/gift',
    value       DECIMAL(10,2) DEFAULT 0  COMMENT '优惠金额/折扣',
    min_amount  DECIMAL(10,2) DEFAULT 0  COMMENT '最低消费',
    merchant_id BIGINT UNSIGNED DEFAULT NULL COMMENT '关联商户，NULL=通用',
    total_count INT          DEFAULT 0    COMMENT '总发放数量，0=无限',
    used_count  INT          DEFAULT 0    COMMENT '已使用数量',
    valid_days  INT          DEFAULT 30   COMMENT '有效天数',
    expire_at   DATETIME     DEFAULT NULL COMMENT '固定过期时间',
    description TEXT         DEFAULT NULL,
    status      TINYINT      DEFAULT 1    COMMENT '1启用 0停用',
    created_at  DATETIME     DEFAULT CURRENT_TIMESTAMP,
    KEY idx_merchant (merchant_id),
    KEY idx_status (status)
) COMMENT='优惠券模板';

-- =============================================
-- 5. 优惠券发放记录表
-- =============================================
CREATE TABLE IF NOT EXISTS coupons (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    code         VARCHAR(32)  NOT NULL UNIQUE COMMENT '券码',
    template_id  BIGINT UNSIGNED NOT NULL COMMENT '模板ID',
    member_id    BIGINT UNSIGNED NOT NULL COMMENT '会员ID',
    status       VARCHAR(20)  DEFAULT 'unused' COMMENT 'unused/used/expired',
    issued_at    DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '发放时间',
    expire_at    DATETIME     DEFAULT NULL COMMENT '过期时间',
    used_at      DATETIME     DEFAULT NULL COMMENT '使用时间',
    used_merchant_id BIGINT UNSIGNED DEFAULT NULL COMMENT '核销商户',
    KEY idx_member (member_id),
    KEY idx_code (code),
    KEY idx_status (status)
) COMMENT='优惠券发放记录';

-- =============================================
-- 6. 活动表
-- =============================================
CREATE TABLE IF NOT EXISTS activities (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    title        VARCHAR(128) NOT NULL     COMMENT '活动标题',
    subtitle     VARCHAR(256) DEFAULT NULL COMMENT '副标题',
    content      TEXT         DEFAULT NULL COMMENT '活动详情（富文本）',
    cover_img    VARCHAR(512) DEFAULT NULL COMMENT '封面图',
    start_at     DATETIME     NOT NULL     COMMENT '开始时间',
    end_at       DATETIME     NOT NULL     COMMENT '结束时间',
    location     VARCHAR(128) DEFAULT NULL COMMENT '活动地点',
    merchant_id  BIGINT UNSIGNED DEFAULT NULL COMMENT '关联商户',
    max_people   INT          DEFAULT 0    COMMENT '限制人数，0=不限',
    signup_count INT          DEFAULT 0    COMMENT '报名人数',
    status       VARCHAR(20)  DEFAULT 'draft' COMMENT 'draft/active/ended',
    push_enabled TINYINT      DEFAULT 1    COMMENT '是否推送给入园游客',
    push_channels JSON        DEFAULT NULL COMMENT '推送渠道 ["mp","wxwork"]',
    created_by   BIGINT UNSIGNED DEFAULT NULL COMMENT '创建人管理员ID',
    created_at   DATETIME     DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_status (status),
    KEY idx_time (start_at, end_at)
) COMMENT='活动表';

-- =============================================
-- 7. 活动报名表
-- =============================================
CREATE TABLE IF NOT EXISTS activity_signups (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    activity_id BIGINT UNSIGNED NOT NULL,
    member_id   BIGINT UNSIGNED NOT NULL,
    signed_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_signup (activity_id, member_id),
    KEY idx_activity (activity_id),
    KEY idx_member (member_id)
) COMMENT='活动报名记录';

-- =============================================
-- 8. 推文表
-- =============================================
CREATE TABLE IF NOT EXISTS articles (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    title        VARCHAR(256) NOT NULL     COMMENT '标题',
    content      TEXT         DEFAULT NULL COMMENT '正文',
    summary      VARCHAR(512) DEFAULT NULL COMMENT '摘要',
    cover_img    VARCHAR(512) DEFAULT NULL COMMENT '封面图',
    source_type  VARCHAR(20)  DEFAULT NULL COMMENT '来源类型 activity/merchant/holiday/manual',
    source_id    BIGINT UNSIGNED DEFAULT NULL COMMENT '来源ID',
    status       VARCHAR(20)  DEFAULT 'draft' COMMENT 'draft/reviewing/approved/published',
    platforms    JSON         DEFAULT NULL COMMENT '发布平台 ["mp","douyin","xiaohongshu"]',
    publish_at   DATETIME     DEFAULT NULL COMMENT '定时发布时间',
    published_at DATETIME     DEFAULT NULL COMMENT '实际发布时间',
    mp_article_id VARCHAR(64) DEFAULT NULL COMMENT '公众号文章ID',
    created_by   BIGINT UNSIGNED DEFAULT NULL,
    reviewed_by  BIGINT UNSIGNED DEFAULT NULL,
    created_at   DATETIME     DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_status (status),
    KEY idx_source (source_type, source_id)
) COMMENT='推文内容表';

-- =============================================
-- 9. 对话记录表
-- =============================================
CREATE TABLE IF NOT EXISTS chat_logs (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    member_id    BIGINT UNSIGNED DEFAULT NULL COMMENT '会员ID',
    session_id   VARCHAR(64)  NOT NULL     COMMENT '会话ID（通常是external_userid）',
    channel      VARCHAR(20)  DEFAULT NULL COMMENT '渠道 mp/wxwork_kf/wxwork_app',
    open_kfid    VARCHAR(64)  DEFAULT NULL COMMENT '客服账号ID（企微客服专用）',
    role         VARCHAR(10)  NOT NULL     COMMENT 'user/assistant/human',
    content      TEXT         NOT NULL     COMMENT '消息内容',
    msg_type     VARCHAR(20)  DEFAULT 'text' COMMENT 'text/image/event',
    is_human_reply TINYINT   DEFAULT 0    COMMENT '是否人工回复 1=是 0=AI',
    human_sender VARCHAR(64)  DEFAULT NULL COMMENT '人工回复者userid（企微userid）',
    created_at   DATETIME     DEFAULT CURRENT_TIMESTAMP,
    KEY idx_session (session_id),
    KEY idx_member (member_id),
    KEY idx_time (created_at),
    KEY idx_channel (channel)
) COMMENT='对话记录（AI+人工统一）';

-- =============================================
-- 15. 人工接管会话表
-- =============================================
CREATE TABLE IF NOT EXISTS kf_takeover (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    session_id   VARCHAR(64)  NOT NULL UNIQUE COMMENT '会话ID（external_userid）',
    open_kfid    VARCHAR(64)  NOT NULL COMMENT '客服账号ID',
    takeover_by  VARCHAR(64)  DEFAULT NULL COMMENT '接管人userid',
    takeover_at  DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '接管时间',
    released_at  DATETIME     DEFAULT NULL COMMENT '释放时间',
    status       VARCHAR(16)  DEFAULT 'active' COMMENT 'active=接管中 released=已释放',
    KEY idx_session (session_id),
    KEY idx_status (status)
) COMMENT='人工接管会话记录（记录哪些session当前被人工接管，AI暂停回复）';

-- =============================================
-- 10. 管理员表
-- =============================================
CREATE TABLE IF NOT EXISTS admins (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    username    VARCHAR(32)  NOT NULL UNIQUE COMMENT '用户名',
    password    VARCHAR(128) NOT NULL        COMMENT '密码（bcrypt）',
    name        VARCHAR(32)  DEFAULT NULL    COMMENT '姓名',
    role        VARCHAR(20)  DEFAULT 'admin' COMMENT 'superadmin/admin/merchant',
    merchant_id BIGINT UNSIGNED DEFAULT NULL COMMENT '关联商户（merchant角色）',
    last_login  DATETIME     DEFAULT NULL,
    status      TINYINT      DEFAULT 1       COMMENT '1启用 0禁用',
    created_at  DATETIME     DEFAULT CURRENT_TIMESTAMP,
    KEY idx_role (role)
) COMMENT='管理员账号';

-- =============================================
-- 11. 系统配置表
-- =============================================
CREATE TABLE IF NOT EXISTS system_configs (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    key_name    VARCHAR(64)  NOT NULL UNIQUE COMMENT '配置键',
    value       TEXT         DEFAULT NULL    COMMENT '配置值',
    description VARCHAR(256) DEFAULT NULL,
    updated_at  DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) COMMENT='系统配置';

-- 初始化系统配置
INSERT INTO system_configs (key_name, value, description) VALUES
('park_name', 'XX园区', '园区名称'),
('park_address', '', '园区地址'),
('welcome_msg', '欢迎来到园区！', '欢迎语'),
('mp_appid', '', '公众号AppID'),
('mp_appsecret', '', '公众号AppSecret'),
('wxwork_corpid', 'ww78829c0c975fb148', '企业微信企业ID'),
('wxwork_agentid', '1000016', '企微游客端AgentID'),
('admin_email', '', '管理员邮件收件人'),
('daily_report_time', '00:00', '每日报告发送时间')
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

-- =============================================
-- 12. 初始管理员账号（密码：admin123，请上线后修改）
-- =============================================
INSERT INTO admins (username, password, name, role) VALUES
('admin', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', '超级管理员', 'superadmin')
ON DUPLICATE KEY UPDATE username = username;

-- =============================================
-- 13. 回复规则表
-- =============================================
CREATE TABLE IF NOT EXISTS reply_rules (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    keyword     VARCHAR(128) NOT NULL COMMENT '匹配关键词',
    reply       TEXT         NOT NULL COMMENT '回复内容',
    match_type  VARCHAR(20)  DEFAULT 'contains' COMMENT '匹配方式: contains/exact/regex',
    category    VARCHAR(20)  DEFAULT 'other' COMMENT '分类: greeting/info/nav/other',
    priority    INT          DEFAULT 0    COMMENT '优先级，数字越大越优先',
    is_active   TINYINT      DEFAULT 1    COMMENT '是否启用 1/0',
    created_at  DATETIME     DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_active (is_active),
    KEY idx_keyword (keyword)
) COMMENT='自动回复规则';

-- 增量：先确保已有表加上 category 列（CREATE TABLE IF NOT EXISTS 不会改已有表）
SET @dbname = DATABASE();
SET @tablename = 'reply_rules';
SET @columnname = 'category';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = @tablename AND COLUMN_NAME = @columnname) > 0,
  'SELECT 1',
  'ALTER TABLE reply_rules ADD COLUMN category VARCHAR(20) DEFAULT ''other'' COMMENT ''分类: greeting/info/nav/other'' AFTER match_type'
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 给已有数据补上分类
UPDATE reply_rules SET category = 'greeting' WHERE keyword IN ('你好', 'hi', 'hello', '嗨', '早上好', '下午好') AND (category = 'other' OR category IS NULL);
UPDATE reply_rules SET category = 'info' WHERE (keyword LIKE '%WiFi%' OR keyword LIKE '%营业%' OR keyword LIKE '%时间%') AND (category = 'other' OR category IS NULL);
UPDATE reply_rules SET category = 'nav' WHERE (keyword LIKE '%停车%' OR keyword LIKE '%地址%' OR keyword LIKE '%怎么走%') AND (category = 'other' OR category IS NULL);

-- 初始回复规则
INSERT INTO reply_rules (keyword, reply, match_type, category, priority) VALUES
('你好', '您好！欢迎来到星汇广场，请问有什么可以帮您的？😊', 'exact', 'greeting', 10),
('停车', '🅿️ 星汇广场停车场信息：\n• B1-B2层地下车库，入口在东门\n• 首小时免费，之后5元/小时\n• 每天封顶40元\n• VIP会员享8折优惠', 'contains', 'nav', 5),
('WiFi|wifi|网络', '📶 星汇广场免费WiFi：\n• 网络名：XingHui-Free\n• 无需密码，连接即可使用\n• 覆盖全部公共区域', 'contains', 'info', 5),
('营业时间|几点开门|几点关门', '🕐 星汇广场营业时间：\n• 商场：10:00-22:00\n• 餐饮：10:00-22:00（部分至23:00）\n• 超市：08:00-22:00', 'contains', 'info', 5),
('地址|怎么走|在哪', '📍 星汇广场地址：\n上海市浦东新区张江路1234号\n• 地铁2号线张江站3号口步行5分钟\n• 公交：张江路/祖冲之路站', 'contains', 'nav', 5)
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

-- =============================================
-- 14. 标签规则表
-- =============================================
CREATE TABLE IF NOT EXISTS tag_rules (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tag_name    VARCHAR(64)  NOT NULL COMMENT '标签名称',
    keyword     VARCHAR(128) NOT NULL COMMENT '触发关键词',
    match_type  VARCHAR(20)  DEFAULT 'contains' COMMENT '匹配方式: contains/exact/regex',
    is_active   TINYINT      DEFAULT 1    COMMENT '是否启用',
    created_at  DATETIME     DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_active (is_active),
    KEY idx_tag (tag_name)
) COMMENT='自动标签规则';

-- 初始标签规则
INSERT INTO tag_rules (tag_name, keyword, match_type) VALUES
('餐饮', '吃饭|美食|餐厅|饿了|午饭|晚饭|咖啡|奶茶', 'regex'),
('购物', '买|购物|逛街|打折|优惠|促销', 'regex'),
('停车', '停车|车位|车库', 'contains'),
('娱乐', '电影|KTV|游戏|玩', 'contains'),
('亲子', '儿童|孩子|小孩|亲子|宝宝', 'contains')
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

-- =============================================
-- 16. 广告/轮播图表
-- =============================================
CREATE TABLE IF NOT EXISTS banners (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    title       VARCHAR(128) NOT NULL     COMMENT '广告标题',
    image_url   VARCHAR(512) DEFAULT NULL COMMENT '图片URL（为空则渐变色占位）',
    link_type   VARCHAR(20)  DEFAULT 'none' COMMENT '跳转类型: none/activity/coupon/merchant/url',
    link_id     BIGINT UNSIGNED DEFAULT NULL COMMENT '跳转目标ID',
    link_url    VARCHAR(512) DEFAULT NULL COMMENT '外部跳转URL',
    sort_order  INT          DEFAULT 0    COMMENT '排序（越小越前）',
    position    VARCHAR(32)  DEFAULT 'home_top' COMMENT '位置: home_top/home_mid/coupon_top',
    status      TINYINT      DEFAULT 1    COMMENT '1启用 0停用',
    created_at  DATETIME     DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_status (status),
    KEY idx_position (position)
) COMMENT='广告/轮播图';

-- =============================================
-- 17. 公告/通知表
-- =============================================
CREATE TABLE IF NOT EXISTS notices (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    title       VARCHAR(128) NOT NULL     COMMENT '公告标题',
    content     TEXT         NOT NULL     COMMENT '公告内容',
    type        VARCHAR(20)  DEFAULT 'info' COMMENT '类型: info/warning/urgent',
    is_popup    TINYINT      DEFAULT 0    COMMENT '是否自动弹窗 1=是 0=否',
    is_top      TINYINT      DEFAULT 0    COMMENT '是否置顶 1=是 0=否',
    status      TINYINT      DEFAULT 1    COMMENT '1启用 0停用',
    created_at  DATETIME     DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_status (status),
    KEY idx_top (is_top)
) COMMENT='公告/通知';


-- =============================================
-- 增量迁移：旧 chat_logs 表补列（兼容旧库）
-- =============================================
SET @db2 = DATABASE();
SET @col1 = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=@db2 AND TABLE_NAME='chat_logs' AND COLUMN_NAME='is_human_reply') > 0,
  'SELECT 1',
  'ALTER TABLE chat_logs ADD COLUMN is_human_reply TINYINT DEFAULT 0 COMMENT ''是否人工回复'' AFTER msg_type'
));
PREPARE s1 FROM @col1; EXECUTE s1; DEALLOCATE PREPARE s1;

SET @col2 = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=@db2 AND TABLE_NAME='chat_logs' AND COLUMN_NAME='human_sender') > 0,
  'SELECT 1',
  'ALTER TABLE chat_logs ADD COLUMN human_sender VARCHAR(64) DEFAULT NULL COMMENT ''人工回复者userid'' AFTER is_human_reply'
));
PREPARE s2 FROM @col2; EXECUTE s2; DEALLOCATE PREPARE s2;

SET @col3 = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=@db2 AND TABLE_NAME='chat_logs' AND COLUMN_NAME='open_kfid') > 0,
  'SELECT 1',
  'ALTER TABLE chat_logs ADD COLUMN open_kfid VARCHAR(64) DEFAULT NULL COMMENT ''客服账号ID'' AFTER channel'
));
PREPARE s3 FROM @col3; EXECUTE s3; DEALLOCATE PREPARE s3;

-- =============================================
-- 增量迁移：确保 kf_takeover 表存在（兼容旧库）
-- =============================================
SET @tbl_kf = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'kf_takeover');
SET @create_kf = IF(@tbl_kf = 0,
  'CREATE TABLE kf_takeover (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    session_id   VARCHAR(64)  NOT NULL UNIQUE COMMENT ''会话ID（external_userid）'',
    open_kfid    VARCHAR(64)  NOT NULL COMMENT ''客服账号ID'',
    takeover_by  VARCHAR(64)  DEFAULT NULL COMMENT ''接管人userid'',
    takeover_at  DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT ''接管时间'',
    released_at  DATETIME     DEFAULT NULL COMMENT ''释放时间'',
    status       VARCHAR(16)  DEFAULT ''active'' COMMENT ''active=接管中 released=已释放'',
    KEY idx_session (session_id),
    KEY idx_status (status)
  ) COMMENT=''人工接管会话记录''',
  'SELECT 1');
PREPARE s_kf FROM @create_kf; EXECUTE s_kf; DEALLOCATE PREPARE s_kf;

-- =============================================
-- 增量迁移：确保 banners 和 notices 表存在（兼容旧库）
-- =============================================
SET @tbl_bn = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'banners');
SET @create_bn = IF(@tbl_bn = 0,
  'CREATE TABLE banners (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    title       VARCHAR(128) NOT NULL COMMENT ''广告标题'',
    image_url   VARCHAR(512) DEFAULT NULL COMMENT ''图片URL（为空则渐变色占位）'',
    link_type   VARCHAR(20)  DEFAULT ''none'' COMMENT ''跳转类型: none/activity/coupon/merchant/url'',
    link_id     BIGINT UNSIGNED DEFAULT NULL COMMENT ''跳转目标ID'',
    link_url    VARCHAR(512) DEFAULT NULL COMMENT ''外部跳转URL'',
    sort_order  INT          DEFAULT 0 COMMENT ''排序（越小越前）'',
    position    VARCHAR(32)  DEFAULT ''home_top'' COMMENT ''位置: home_top/home_mid/coupon_top'',
    status      TINYINT      DEFAULT 1 COMMENT ''1启用 0停用'',
    created_at  DATETIME     DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_status (status),
    KEY idx_position (position)
  ) COMMENT=''广告/轮播图''',
  'SELECT 1');
PREPARE s_bn FROM @create_bn; EXECUTE s_bn; DEALLOCATE PREPARE s_bn;

SET @tbl_nc = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'notices');
SET @create_nc = IF(@tbl_nc = 0,
  'CREATE TABLE notices (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    title       VARCHAR(128) NOT NULL COMMENT ''公告标题'',
    content     TEXT         NOT NULL COMMENT ''公告内容'',
    type        VARCHAR(20)  DEFAULT ''info'' COMMENT ''类型: info/warning/urgent'',
    is_popup    TINYINT      DEFAULT 0 COMMENT ''是否自动弹窗 1=是 0=否'',
    is_top      TINYINT      DEFAULT 0 COMMENT ''是否置顶 1=是 0=否'',
    status      TINYINT      DEFAULT 1 COMMENT ''1启用 0停用'',
    created_at  DATETIME     DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_status (status),
    KEY idx_top (is_top)
  ) COMMENT=''公告/通知''',
  'SELECT 1');
PREPARE s_nc FROM @create_nc; EXECUTE s_nc; DEALLOCATE PREPARE s_nc;




