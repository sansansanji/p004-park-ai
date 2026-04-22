# 初始化脚本
# 创建必要的目录结构

import os
import sys

# 基础目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 需要创建的目录
DIRS_TO_CREATE = [
    'data/visitors',
    'data/exports',
    'scripts/export',
    'logs'
]

def init_directories():
    """初始化目录结构"""
    print("正在初始化目录结构...")
    
    for dir_path in DIRS_TO_CREATE:
        full_path = os.path.join(BASE_DIR, dir_path)
        os.makedirs(full_path, exist_ok=True)
        print(f"  ✓ 创建目录: {dir_path}")
    
    print("\n目录结构初始化完成！")


def print_structure():
    """打印项目结构"""
    print("\n=== 园区AI助手项目结构 ===")
    print("Claw/")
    print("├── config/")
    print("│   ├── system.yaml         # 系统配置")
    print("│   ├── welcome.md          # 欢迎语配置")
    print("│   ├── memory.yaml         # 记忆系统配置")
    print("│   ├── wechat_work.example.yaml  # 企业微信配置示例")
    print("│   └── h5.example.yaml    # H5配置示例")
    print("├── skills/")
    print("│   └── visitor-entry/")
    print("│       ├── skill.yaml      # 技能配置")
    print("│       └── prompts/")
    print("│           └── welcome.txt  # 欢迎语")
    print("├── data/")
    print("│   ├── visitors/          # 游客档案")
    print("│   └── exports/           # 导出的数据")
    print("├── scripts/")
    print("│   ├── wechat_bot.py       # 企业微信机器人")
    print("│   ├── welcome_handler.py  # 欢迎语处理")
    print("│   ├── memory_system.py    # 记忆系统")
    print("│   └── init.py             # 本脚本")
    print("└── README.md              # 项目说明")


if __name__ == '__main__':
    init_directories()
    print_structure()
    
    print("\n=== 游客入口模块已完成 ===")
    print("下一步：")
    print("1. 配置企业微信（复制并修改 wechat_work.example.yaml）")
    print("2. 启动服务: python scripts/wechat_bot.py")
    print("3. 在企业微信后台配置回调URL")
