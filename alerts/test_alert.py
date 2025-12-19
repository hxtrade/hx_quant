import time
import sys
import os
from alerts.alerts_runner import AlertBase

class TestAlert(AlertBase):
    """测试告警类"""
    
    def __init__(self):
        super().__init__()
        self.name = "TestAlert"
    
    def run(self):
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {self.name} 正在运行...")
        # 模拟告警逻
        print("检查价格条件...")
        time.sleep(1)
        print("告警检查完成")

class PriceAlert(AlertBase):
    """价格告警类"""
    
    def __init__(self):
        super().__init__()
        self.name = "PriceAlert"
        self.price_threshold = 100.0
    
    def run(self):
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {self.name} 检查价格阈值: {self.price_threshold}")
        # 模拟价格检查逻辑
        current_price = 95.5
        if current_price < self.price_threshold:
            print(f"告警: 当前价格 {current_price} 低于阈值 {self.price_threshold}")
        else:
            print(f"价格正常: {current_price}")