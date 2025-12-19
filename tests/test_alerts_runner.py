import unittest
import os
import tempfile
import shutil
import sys
import importlib.util


from alerts.alerts_runner import AlertBase, AlertsRunner


class TestAlertsRunner(unittest.TestCase):
    """AlertsRunner单元测试类"""
    
    def setUp(self):
        """测试前准备：创建临时目录和测试文件"""
        self.test_dir = tempfile.mkdtemp()
        self.alerts_dir = os.path.join(self.test_dir, "alerts")
        os.makedirs(self.alerts_dir, exist_ok=True)
        
    def tearDown(self):
        """测试后清理：删除临时目录"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def create_alert_file(self, filename, content):
        """创建测试用的alert文件"""
        file_path = os.path.join(self.alerts_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return file_path
    
    def test_run_alerts_nonexistent_directory(self):
        """测试不存在的目录"""
        nonexistent_path = os.path.join(self.test_dir, "nonexistent")
        
        with self.assertPrints(f"目录不存在: {nonexistent_path}"):
            AlertsRunner.run_alerts(nonexistent_path)
    
    def test_run_alerts_empty_directory(self):
        """测试空目录"""
        with self.assertPrints(f"扫描目录: {self.alerts_dir}"):
            AlertsRunner.run_alerts(self.alerts_dir)
    
    def test_run_alerts_with_valid_alert_file(self):
        """测试包含有效alert文件的目录"""
        # 创建测试alert文件
        alert_content = f'''import sys
import os
# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
from alerts.alerts_runner import AlertBase

class TestAlert(AlertBase):
    def __init__(self):
        super().__init__()
        self.run_called = False
    
    def run(self):
        self.run_called = True
        return "test_run"
'''
        self.create_alert_file("test_alert.py", alert_content)
        
        # 执行并验证输出
        expected_outputs = [
            f"扫描目录: {self.alerts_dir}",
            f"找到alert文件: {os.path.join(self.alerts_dir, 'test_alert.py')}",
            "找到Alert类: TestAlert",
            "执行 TestAlert.run()",
            "TestAlert.run() 执行完成"
        ]
        
        with self.assertPrints(expected_outputs):
            AlertsRunner.run_alerts(self.alerts_dir)
    
    def test_run_alerts_with_multiple_alert_classes(self):
        """测试包含多个Alert类的文件"""
        alert_content = f'''import sys
import os
# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
from alerts.alerts_runner import AlertBase

class FirstAlert(AlertBase):
    def run(self):
        return "first"

class SecondAlert(AlertBase):
    def run(self):
        return "second"

class NotInheritAlert:
    def run(self):
        pass
'''
        self.create_alert_file("multiple_alert.py", alert_content)
        
        with self.assertPrints(["找到Alert类: FirstAlert", "找到Alert类: SecondAlert"]):
            AlertsRunner.run_alerts(self.alerts_dir)
    
    def test_run_alerts_ignores_non_alert_files(self):
        """测试忽略非alert.py文件"""
        # 创建非alert.py文件（应该被忽略）
        other_content = '''from alerts.alerts_runner import AlertBase

class SomeAlert(AlertBase):
    def run(self):
        pass
'''
        self.create_alert_file("other_file.py", other_content)
        
        # 创建alert.py文件（应该被处理）
        alert_content = '''from alerts.alerts_runner import AlertBase

class ValidAlert(AlertBase):
    def run(self):
        pass
'''
        self.create_alert_file("valid_alert.py", alert_content)
        
        # 验证有效文件被找到和类被处理
        with self.assertPrints(["找到Alert类: ValidAlert"]):
            AlertsRunner.run_alerts(self.alerts_dir)
    
    def test_run_alerts_handles_import_errors(self):
        """测试处理导入错误的情况"""
        # 创建有导入错误的文件
        invalid_content = '''import nonexistent_module
from alerts.alerts_runner import AlertBase

class BrokenAlert(AlertBase):
    def run(self):
        pass
'''
        self.create_alert_file("broken_alert.py", invalid_content)
        
        with self.assertPrints(["导入模块失败"]):
            AlertsRunner.run_alerts(self.alerts_dir)
    
    def test_run_alerts_handles_runtime_errors(self):
        """测试处理运行时错误的情况"""
        alert_content = f'''import sys
import os
# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
from alerts.alerts_runner import AlertBase

class ErrorAlert(AlertBase):
    def run(self):
        raise Exception("测试运行时错误")
'''
        self.create_alert_file("error_alert.py", alert_content)
        
        with self.assertPrints(["执行 ErrorAlert.run() 失败"]):
            AlertsRunner.run_alerts(self.alerts_dir)
    
    def test_alert_base_initialization(self):
        """测试AlertBase基类初始化"""
        alert = AlertBase()
        self.assertIsNotNone(alert)
    
    def test_alert_base_run_method(self):
        """测试AlertBase基类的run方法"""
        alert = AlertBase()
        # 默认的run方法应该什么都不做，但不应该报错
        result = alert.run()
        self.assertIsNone(result)


class AssertPrintsContext:
    """辅助类，用于断言打印输出"""
    
    def __init__(self, test_case, expected_outputs=None, not_expected_outputs=None):
        self.test_case = test_case
        self.expected_outputs = expected_outputs or []
        self.not_expected_outputs = not_expected_outputs or []
        self.captured_output = []
    
    def __enter__(self):
        import builtins
        self.original_print = builtins.print
        builtins.print = self._mock_print
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        import builtins
        builtins.print = self.original_print
        
        # 验证期望的输出
        for expected in self.expected_outputs:
            self.test_case.assertTrue(
                any(expected in output for output in self.captured_output),
                f"期望输出中包含: {expected}\n实际输出: {self.captured_output}"
            )
        
        # 验证不期望的输出
        for not_expected in self.not_expected_outputs:
            self.test_case.assertFalse(
                any(not_expected in output for output in self.captured_output),
                f"不期望输出中包含: {not_expected}\n实际输出: {self.captured_output}"
            )
    
    def _mock_print(self, *args, **kwargs):
        output = ' '.join(str(arg) for arg in args)
        self.captured_output.append(output)


# 为unittest.TestCase添加辅助方法
def assertPrints(self, expected_outputs=None):
    return AssertPrintsContext(self, expected_outputs)

def assertNotPrints(self, not_expected_outputs):
    return AssertPrintsContext(self, not_expected_outputs=not_expected_outputs)

# 动态添加方法到TestCase
unittest.TestCase.assertPrints = assertPrints
unittest.TestCase.assertNotPrints = assertNotPrints


if __name__ == '__main__':
    # 运行所有测试
    unittest.main(verbosity=2)