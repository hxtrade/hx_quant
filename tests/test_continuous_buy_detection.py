"""
测试连续买单检测功能
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from alerts.turnover_alert import TurnoverAlert


class TestContinuousBuyDetection(unittest.TestCase):
    """测试连续买单检测功能"""
    
    def setUp(self):
        """测试前设置"""
        self.alert = TurnoverAlert()
        self.test_stock = "000001"
        
        # 模拟交易数据
        self.test_transaction_data = pd.DataFrame({
            'datetime': [
                datetime(2024, 1, 15, 9, 30, 0),
                datetime(2024, 1, 15, 9, 30, 1),
                datetime(2024, 1, 15, 9, 30, 2),
                datetime(2024, 1, 15, 9, 30, 3),
                datetime(2024, 1, 15, 9, 30, 4),
                datetime(2024, 1, 15, 9, 30, 5),
                datetime(2024, 1, 15, 9, 30, 6),
                datetime(2024, 1, 15, 9, 30, 7),
                datetime(2024, 1, 15, 9, 30, 8),
            ],
            'buy_vol': [100, 150, 80, 50, 30, 200, 180, 70, 60],  # 买入量
            'sell_vol': [50, 100, 40, 80, 60, 50, 40, 90, 70],   # 卖出量
            'volume': [10000, 15000, 8000, 5000, 3000, 20000, 18000, 7000, 6000]  # 成交额
        })
        
        # 设置流通市值 (1000万元)
        self.alert.stocks_cmv_map[self.test_stock] = 10000000
    
    def test_detect_continuous_buy_orders_basic(self):
        """测试基本的连续买单检测"""
        result = self.alert._detect_continuous_buy_orders(self.test_transaction_data, self.test_stock)
        
        # 应该检测到连续买单
        self.assertIsNotNone(result)
        self.assertGreater(result['continuous_count'], 0)
        self.assertGreater(result['continuous_amount'], 0)
        self.assertGreater(result['percentage'], 0)
    
    def test_detect_continuous_buy_orders_threshold_check(self):
        """测试阈值检查"""
        # 设置很低的流通市值，确保触发阈值
        self.alert.stocks_cmv_map[self.test_stock] = 10000  # 1万元
        
        result = self.alert._detect_continuous_buy_orders(self.test_transaction_data, self.test_stock)
        
        # 应该触发告警
        self.assertIsNotNone(result)
        self.assertGreater(result['continuous_amount'], 10000 / 500)  # 大于阈值
    
    def test_detect_continuous_buy_orders_no_trigger(self):
        """测试不触发告警的情况"""
        # 设置很高的流通市值，确保不触发阈值
        self.alert.stocks_cmv_map[self.test_stock] = 1000000000  # 10亿元
        
        result = self.alert._detect_continuous_buy_orders(self.test_transaction_data, self.test_stock)
        
        # 可能不触发告警
        if result:
            # 如果触发，检查比例应该很小
            self.assertLess(result['percentage'], 0.1)
    
    def test_detect_continuous_buy_orders_empty_data(self):
        """测试空数据的情况"""
        empty_df = pd.DataFrame()
        
        result = self.alert._detect_continuous_buy_orders(empty_df, self.test_stock)
        
        # 应该返回None
        self.assertIsNone(result)
    
    def test_detect_continuous_buy_orders_no_cmv(self):
        """测试没有流通市值数据的情况"""
        # 移除流通市值数据
        self.alert.stocks_cmv_map = {}
        
        result = self.alert._detect_continuous_buy_orders(self.test_transaction_data, self.test_stock)
        
        # 应该返回None
        self.assertIsNone(result)
    
    def test_detect_continuous_buy_orders_all_buy_orders(self):
        """测试全是买单的情况"""
        all_buy_data = pd.DataFrame({
            'datetime': [datetime(2024, 1, 15, 9, 30, i) for i in range(5)],
            'buy_vol': [100, 150, 120, 180, 90],
            'sell_vol': [10, 20, 15, 25, 10],  # 都小于buy_vol
            'volume': [10000, 15000, 12000, 18000, 9000]
        })
        
        result = self.alert._detect_continuous_buy_orders(all_buy_data, self.test_stock)
        
        # 应该检测到连续5笔买单
        self.assertIsNotNone(result)
        self.assertEqual(result['continuous_count'], 5)
        self.assertEqual(result['continuous_amount'], 10000 + 15000 + 12000 + 18000 + 9000)
    
    def test_detect_continuous_buy_orders_all_sell_orders(self):
        """测试全是卖单的情况"""
        all_sell_data = pd.DataFrame({
            'datetime': [datetime(2024, 1, 15, 9, 30, i) for i in range(5)],
            'buy_vol': [10, 20, 15, 25, 10],    # 都小于sell_vol
            'sell_vol': [100, 150, 120, 180, 90],
            'volume': [10000, 15000, 12000, 18000, 9000]
        })
        
        result = self.alert._detect_continuous_buy_orders(all_sell_data, self.test_stock)
        
        # 应该不触发告警
        self.assertIsNone(result)
    
    def test_detect_continuous_buy_orders_mixed_pattern(self):
        """测试混合买卖模式"""
        mixed_data = pd.DataFrame({
            'datetime': [datetime(2024, 1, 15, 9, 30, i) for i in range(10)],
            'buy_vol': [100, 20, 150, 30, 180, 40, 200, 50, 220, 60],
            'sell_vol': [50, 100, 75, 150, 90, 180, 100, 200, 110, 220],
            'volume': [10000, 2000, 15000, 3000, 18000, 4000, 20000, 5000, 22000, 6000]
        })
        
        result = self.alert._detect_continuous_buy_orders(mixed_data, self.test_stock)
        
        # 应该检测到多个连续买单段，选择最大的
        self.assertIsNotNone(result)
        # 最大连续买单应该是第7-9笔（3笔）
        self.assertEqual(result['continuous_count'], 3)
    
    def test_detect_continuous_buy_orders_description_format(self):
        """测试描述格式"""
        result = self.alert._detect_continuous_buy_orders(self.test_transaction_data, self.test_stock)
        
        if result:
            description = result['description']
            
            # 检查描述包含关键信息
            self.assertIn("连续", description)
            self.assertIn("买单", description)
            self.assertIn("成交额", description)
            self.assertIn("占流通市值", description)
            self.assertIn("%", description)
            self.assertIn("阈值", description)
    
    @patch.object(TurnoverAlert, 'query_transaction_history')
    @patch.object(TurnoverAlert, '_detect_continuous_buy_orders')
    def test_run_integration(self, mock_detect, mock_query):
        """测试run方法的集成"""
        # 模拟返回的交易数据
        mock_query.return_value = self.test_transaction_data
        
        # 模拟检测结果
        mock_detect.return_value = {
            'continuous_count': 3,
            'continuous_amount': 33000,
            'threshold': 20000,
            'percentage': 0.33,
            'description': '连续3笔买单，成交额33,000元，占流通市值0.330%'
        }
        
        # 设置监控股票
        self.alert.monitor_stocks = [self.test_stock]
        self.alert.stocks_cmv_map[self.test_stock] = 10000000
        
        # 执行run方法
        alerts = self.alert.run()
        
        # 验证结果
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].code, self.test_stock)
        self.assertEqual(alerts[0].name, "TurnoverAlert")
        self.assertIn("连续3笔买单", alerts[0].descr)
        
        # 验证调用
        mock_query.assert_called_once()
        mock_detect.assert_called_once()
    
    @patch.object(TurnoverAlert, 'query_transaction_history')
    @patch.object(TurnoverAlert, '_detect_continuous_buy_orders')
    def test_run_no_alerts(self, mock_detect, mock_query):
        """测试没有告警的情况"""
        # 模拟返回的交易数据
        mock_query.return_value = self.test_transaction_data
        
        # 模拟没有检测结果
        mock_detect.return_value = None
        
        # 设置监控股票
        self.alert.monitor_stocks = [self.test_stock]
        self.alert.stocks_cmv_map[self.test_stock] = 10000000
        
        # 执行run方法
        alerts = self.alert.run()
        
        # 验证结果
        self.assertEqual(len(alerts), 0)
    
    @patch.object(TurnoverAlert, 'query_transaction_history')
    def test_run_exception_handling(self, mock_query):
        """测试异常处理"""
        # 模拟抛出异常
        mock_query.side_effect = Exception("数据获取失败")
        
        # 设置监控股票
        self.alert.monitor_stocks = [self.test_stock]
        
        # 执行run方法，应该不抛出异常
        alerts = self.alert.run()
        
        # 验证结果
        self.assertEqual(len(alerts), 0)


class TestPreRunIntegration(unittest.TestCase):
    """测试pre_run方法的集成"""
    
    def setUp(self):
        """测试前设置"""
        self.alert = TurnoverAlert()
        self.alert.config = {
            "monitor_blks": ["自选股", "银行"]
        }
    
    @patch.object(TurnoverAlert, 'get_block_stocks')
    @patch.object(TurnoverAlert, 'quotes')
    @patch.object(TurnoverAlert, 'finance')
    def test_pre_run_success(self, mock_finance, mock_quotes, mock_block_stocks):
        """测试pre_run成功执行"""
        # 模拟返回数据
        mock_block_stocks.side_effect = [
            ["000001", "000002"],  # 自选股
            ["600000", "600001"]   # 银行
        ]
        
        mock_quotes.side_effect = [
            {"open": 10.5},
            {"open": 8.8},
            {"open": 5.2},
            {"open": 12.3}
        ]
        
        mock_finance.side_effect = [
            {"liutongguben": 1000000},
            {"liutongguben": 800000},
            {"liutongguben": 2000000},
            {"liutongguben": 1500000}
        ]
        
        # 执行pre_run
        self.alert.pre_run()
        
        # 验证结果
        self.assertEqual(len(self.alert.monitor_stocks), 4)
        self.assertIn("000001", self.alert.monitor_stocks)
        self.assertIn("000002", self.alert.monitor_stocks)
        self.assertIn("600000", self.alert.monitor_stocks)
        self.assertIn("600001", self.alert.monitor_stocks)
        
        # 验证流通市值计算
        self.assertEqual(self.alert.stocks_cmv_map["000001"], 10500000)  # 10.5 * 1000000
        self.assertEqual(self.alert.stocks_cmv_map["000002"], 7040000)   # 8.8 * 800000
        self.assertEqual(self.alert.stocks_cmv_map["600000"], 10400000)  # 5.2 * 2000000
        self.assertEqual(self.alert.stocks_cmv_map["600001"], 18450000)  # 12.3 * 1500000
    
    def test_pre_run_no_config(self):
        """测试没有配置的情况"""
        self.alert.config = {}
        
        # 应该不抛出异常
        self.alert.pre_run()
        
        # 验证结果
        self.assertEqual(len(self.alert.monitor_stocks), 0)
        self.assertEqual(len(self.alert.stocks_cmv_map), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)