import os
import importlib.util
import inspect
import json

class AlertData(object):
    def __init__(self):
        self.name = ""
        self.code = ""
        self.descr = ""

class AlertBase(object):

    def __init__(self):
        self.config = {}
        return
    def load_config(self, config_path):
        """加载指定路径的JSON配置文件并赋值给config
        
        Args:
            config_path (str, optional)
            
        Returns:
            bool: 加载成功返回True，失败返回False
        """
        
        if not os.path.exists(config_path):
            print(f"配置文件不存在: {config_path}")
            return False
        
        if not config_path.endswith('.json'):
            print(f"配置文件格式错误，请提供JSON文件: {config_path}")
            return False
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 验证配置是否为字典类型
            if not isinstance(config_data, dict):
                print(f"配置文件格式错误，内容应为JSON对象: {config_path}")
                return False
            
            self.config = config_data
            print(f"成功加载配置文件: {config_path}")
            return True
            
        except json.JSONDecodeError as e:
            print(f"JSON解析错误 {config_path}: {e}")
            return False
        except Exception as e:
            print(f"加载配置文件失败 {config_path}: {e}")
            return False
    

    def pre_run(self):
        pass
    def run(self)->list[AlertData]:
        return []
    
class AlertsRunner(object):
    @staticmethod
    def run_alerts(alerts_path):
        """扫描指定目录，查找alert.py文件并执行继承AlertBase的类"""
        if not os.path.exists(alerts_path):
            print(f"目录不存在: {alerts_path}")
            return
        
        print(f"扫描目录: {alerts_path}")
        
        # 遍历目录，查找以alert.py结尾的文件
        for filename in os.listdir(alerts_path):
            if filename.endswith('alert.py'):
                file_path = os.path.join(alerts_path, filename)
                print(f"找到alert文件: {file_path}")
                
                # 动态导入模块
                module_name = filename[:-3]  # 移除.py扩展名
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                
                if spec is None:
                    print(f"无法创建模块规范: {file_path}")
                    continue
                
                module = importlib.util.module_from_spec(spec)
                
                try:
                    spec.loader.exec_module(module)
                except Exception as e:
                    print(f"导入模块失败 {file_path}: {e}")
                    continue
                
                # 查找继承自AlertBase的类
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    # 检查是否是当前模块定义的类，并且继承自AlertBase
                    if (obj.__module__ == module_name and 
                        issubclass(obj, AlertBase) and 
                        obj != AlertBase):
                        
                        print(f"找到Alert类: {name}")
                        
                        try:
                            # 创建实例并执行run方法
                            alert_instance = obj()
                            alert_instance.load_config(os.path.join(".vntrader", module_name +"_setting.json"))
                            alert_instance.pre_run()
                            alert_instance.run()
                        except Exception as e:
                            print(f"执行 {name}.run() 失败: {e}")

    def __init__(self):
        pass

if __name__ == "__main__":
    AlertsRunner.run_alerts("./alerts")