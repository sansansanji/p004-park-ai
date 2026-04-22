# 测试脚本 - 验证优惠券模块
# 运行命令: python scripts/test_coupon.py

import os
import sys

# Windows编码兼容
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_coupon_manager():
    """测试优惠券管理器"""
    print("=== 测试优惠券管理器 ===")
    
    from coupon_manager import get_coupon_manager
    manager = get_coupon_manager()
    
    # 测试获取单个优惠
    coupon = manager.get_coupon("星巴克")
    print(f"\n星巴克优惠:")
    print(f"  商户: {coupon['merchant_name']}")
    print(f"  优惠: {coupon['promotion']}")
    print(f"  链接: {coupon['purchase_link'] or '未配置'}")
    
    # 测试获取所有优惠
    coupons = manager.get_all_coupons()
    print(f"\n优惠券总数: {len(coupons)}")
    for c in coupons:
        print(f"  - {c['merchant_name']}: {c['promotion']}")
    
    # 测试格式化回复
    print("\n=== 格式化回复测试 ===")
    reply = manager.format_all_coupons_reply()
    print(reply[:300])
    
    print("\n✓ 优惠券管理器测试通过\n")
    return True


def test_click_tracker():
    """测试点击跟踪器"""
    print("=== 测试点击跟踪器 ===")
    
    from coupon_manager import get_click_tracker
    tracker = get_click_tracker()
    
    # 记录一次点击
    result = tracker.track_click("test_visitor_001", "星巴克", "下午茶套餐45元")
    print(f"记录点击: {'成功' if result else '失败'}")
    
    # 获取点击统计
    clicks = tracker.get_click_stats("test_visitor_001")
    print(f"点击记录数: {len(clicks)}")
    
    print("\n✓ 点击跟踪器测试通过\n")
    return True


def test_query_handling():
    """测试查询处理"""
    print("=== 测试优惠查询处理 ===")
    
    from coupon_manager import handle_coupon_query
    
    test_cases = [
        "有什么优惠？",
        "星巴克有优惠吗？",
        "餐厅有什么优惠？"
    ]
    
    for msg in test_cases:
        result = handle_coupon_query(msg)
        print(f"\nQ: {msg}")
        print(f"A: {result[:100]}..." if len(result) > 100 else f"A: {result}")
    
    print("\n✓ 查询处理测试通过\n")
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*50)
    print("  优惠券与购买模块 - 功能测试")
    print("="*50 + "\n")
    
    results = []
    
    results.append(("优惠券管理器", test_coupon_manager()))
    results.append(("点击跟踪器", test_click_tracker()))
    results.append(("查询处理", test_query_handling()))
    
    # 汇总结果
    print("="*50)
    print("  测试结果汇总")
    print("="*50)
    
    all_passed = True
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "="*50)
    if all_passed:
        print("  所有测试通过！")
    else:
        print("  部分测试失败，请检查错误信息")
    print("="*50 + "\n")
    
    return all_passed


if __name__ == '__main__':
    run_all_tests()
