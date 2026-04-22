# 智慧园区AI助手 - OpenClaw P004 Demo

基于 Flask + 企业微信 + 公众号的智慧园区管理平台。

## 技术栈
- 后端: Flask + MySQL (TiDB Cloud)
- 前端: H5 (Vue/HTML)
- 部署: Cloudflare Pages + Render

## 功能模块
- 企微机器人 (wechat_bot)
- 标签系统 (tagging_system)  
- AI记忆 (memory_system)
- 地图服务 (map_service)
- 优惠券 (coupon_manager)
- 活动管理 (activities)
- 数据导出 (data_exporter)

## 数据库
- TiDB Cloud Serverless (免费5GB)
- 16张表覆盖：会员/商户/优惠券/活动/内容/对话等
