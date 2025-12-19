"""
连续买单告警功能使用示例
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from alerts.turnover_alert import TurnoverAlert


def demo_continuous_buy_detection():
    """演示连续买单检测功能"""
    print("=== 连续买单检测功能演示 ===\n")
    
    # 创建告警实例
    alert = TurnoverAlert()
    
    # 设置配置
    alert.config = {
        "monitor_blks": ["自选股"]
    }
    
    print("1. 初始化告警系统...")
    print(f"告警名称: {alert.name}")
    print(f"监控板块: {alert.config['monitor_blks']}")
    print()
    
    # 模拟pre_run过程
    print("2. 模拟股票加载和市值计算...")
    
    # 模拟一些测试股票
    alert.monitor_stocks = ["000001", "000002", "600000"]
    
    # 模拟流通市值（单位：元）
    alert.stocks_cmv_map = {
        "000001": 500000000,    # 平安银行：5亿
        "000002": 300000000,    # 万科A：3亿
        "600000": 1000000000,   # 浦发银行：10亿
    }
    
    print(f"加载股票数量: {len(alert.monitor_stocks)}")
    for stock, cmv in alert.stocks_cmv_map.items():
        print(f"  {stock}: 流通市值 {cmv:,} 元")
    print()
    
    # 模拟交易数据
    print("3. 模拟交易数据分析...")
    
    # 示例1：触发告警的连续买单
    print("示例1：触发告警的连续买单")
    transaction_data_1 = pd.DataFrame({
        'datetime': [
            datetime(2024, 1, 15, 9, 30, 0),
            datetime(2024, 1, 15, 9, 30, 1),
            datetime(2024, 1, 15, 9, 30, 2),
            datetime(2024, 1, 15, 9, 30, 3),
            datetime(2024, 1, 15, 9, 30, 4),
        ],
        'buy_vol': [1000, 800, 1200, 900, 1500],
        'sell_vol': [500, 300, 600, 400, 700],
        'volume': [2000000, 1600000, 2400000, 1800000, 3000000]  # 成交额
    })
    
    result_1 = alert._detect_continuous_buy_orders(transaction_data_1, "000001")
    if result_1:
        print(f"  ✓ 检测到告警: {result_1['description']}")
        print(f"  - 连续买单数量: {result_1['continuous_count']}")
        print(f"  - 连续买单成交额: {result_1['continuous_amount']:,} 元")
        print(f"  - 占流通市值比例: {result_1['percentage']:.3f}%")
        print(f"  - 告警阈值: {result_1['threshold']:,} 元")
    else:
        print("  ✗ 未检测到告警")
    
    print()
    
    # 示例2：不触发告警的交易数据
    print("示例2：不触发告警的交易数据")
    transaction_data_2 = pd.DataFrame({
        'datetime': [
            datetime(2024, 1, 15, 9, 30, 0),
            datetime(2024, 1, 15, 9, 30, 1),
            datetime(2024, 1, 15, 9, 30, 2),
        ],
        'buy_vol': [100, 200, 80],
        'sell_vol': [150, 100, 120],  # 卖量大于买量
        'volume': [10000, 20000, 8000]
    })
    
    result_2 = alert._detect_continuous_buy_orders(transaction_data_2, "000002")
    if result_2:
        print(f"  ✓ 检测到告警: {result_2['description']}")
    else:
        print("  ✗ 未检测到告警（符合预期）")
    
    print()
    
    # 示例3：大市值股票的测试
    print("示例3：大市值股票的测试（600000 - 浦发银行）")
    transaction_data_3 = pd.DataFrame({
        'datetime': [
            datetime(2024, 1, 15, 9, 30, 0),
            datetime(2024, 1, 15, 9, 30, 1),
            datetime(2024, 1, 15, 9, 30, 2),
            datetime(2024, 1, 15, 9, 30, 3),
            datetime(2024, 1, 15, 9, 30, 4),
            datetime(2024, 1, 15, 9, 30, 5),
        ],
        'buy_vol': [5000, 8000, 6000, 7000, 9000, 10000],
        'sell_vol': [2000, 3000, 2500, 2800, 3200, 3500],
        'volume': [5000000, 8000000, 6000000, 7000000, 9000000, 10000000]  # 成交额
    })
    
    result_3 = alert._detect_continuous_buy_orders(transaction_data_3, "600000")
    if result_3:
        print(f"  ✓ 检测到告警: {result_3['description']}")
    else:
        print("  ✗ 未检测到告警")
    
    print()
    
    # 显示阈值信息
    print("4. 告警阈值信息:")
    for stock, cmv in alert.stocks_cmv_map.items():
        threshold = cmv / 500
        print(f"  {stock}: 流通市值 {cmv:,} 元, 告警阈值 {threshold:,} 元")
    
    print()
    print("=== 演示完成 ===")


def demo_edge_cases():
    """演示边界情况"""
    print("\n=== 边界情况演示 ===\n")
    
    alert = TurnoverAlert()
    
    # 边界情况1：空数据
    print("边界情况1：空交易数据")
    empty_df = pd.DataFrame()
    result = alert._detect_continuous_buy_orders(empty_df, "000001")
    print(f"结果: {'有告警' if result else '无告警（符合预期）'}")
    
    # 边界情况2：没有流通市值数据
    print("\n边界情况2：没有流通市值数据")
    test_data = pd.DataFrame({
        'datetime': [datetime.now()],
        'buy_vol': [100],
        'sell_vol': [50],
        'volume': [10000]
    })
    result = alert._detect_continuous_buy_orders(test_data, "000001")
    print(f"结果: {'有告警' if result else '无告警（符合预期）'}")
    
    # 边界情况3：单个买单
    print("\n边界情况3：单个买单")
    single_buy_data = pd.DataFrame({
        'datetime': [datetime.now()],
        'buy_vol': [1000],
        'sell_vol': [500],
        'volume': [100000]
    })
    alert.stocks_cmv_map["000001"] = 1000000  # 100万流通市值
    result = alert._detect_continuous_buy_orders(single_buy_data, "000001")
    if result:
        print(f"检测到告警: {result['description']}")
        print(f"是否触发阈值: {'是' if result['continuous_amount'] > result['threshold'] else '否'}")
    else:
        print("无告警")
    
    # 边界情况4：刚好达到阈值
    print("\n边界情况4：刚好达到阈值")
    exact_threshold_data = pd.DataFrame({
        'datetime': [datetime.now(), datetime.now() + timedelta(seconds=1)],
        'buy_vol': [1000, 1000],
        'sell_vol': [500, 500],
        'volume': [1000000, 1000000]  # 总成交额200万
    })
    alert.stocks_cmv_map["000002"] = 1000000000  # 10亿流通市值，阈值=200万
    result = alert._detect_continuous_buy_orders(exact_threshold_data, "000002")
    if result:
        print(f"检测到告警: {result['description']}")
        print(f"成交额: {result['continuous_amount']:,}, 阈值: {result['threshold']:,}")
        print(f"触发条件: {'是' if result['continuous_amount'] > result['threshold'] else '否'}")
    else:
        print("无告警")


def demo_performance_analysis():
    """演示性能分析"""
    print("\n=== 性能分析演示 ===\n")
    
    import time
    
    alert = TurnoverAlert()
    alert.stocks_cmv_map = {
        "000001": 500000000,
        "000002": 300000000,
        "600000": 1000000000,
    }
    
    # 生成大量测试数据
    print("生成大量测试数据进行性能测试...")
    large_data = pd.DataFrame({
        'datetime': [datetime.now() + timedelta(seconds=i) for i in range(1000)],
        'buy_vol': [1000 + i % 500 for i in range(1000)],
        'sell_vol': [500 + i % 300 for i in range(1000)],
        'volume': [1000000 + i * 1000 for i in range(1000)]
    })
    
    print(f"测试数据量: {len(large_data)} 条记录")
    
    # 性能测试
    start_time = time.time()
    result = alert._detect_continuous_buy_orders(large_data, "000001")
    end_time = time.time()
    
    print(f"处理时间: {(end_time - start_time) * 1000:.2f} 毫秒")
    print(f"处理速度: {len(large_data) / (end_time - start_time):.0f} 条/秒")
    
    if result:
        print(f"检测结果: {result['description']}")
    else:
        print("未检测到告警")


if __name__ == "__main__":
    try:
        # 运行主要演示
        demo_continuous_buy_detection()
        
        # 运行边界情况演示
        demo_edge_cases()
        
        # 运行性能分析
        demo_performance_analysis()
        
        print("\n=== 所有演示完成 ===")
        
    except KeyboardInterrupt:
        print("\n演示被用户中断")
    except Exception as e:
        print(f"\n演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()