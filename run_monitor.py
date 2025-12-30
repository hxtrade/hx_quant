#!/usr/bin/env python3
"""
启动股票异动告警监控界面
"""

import sys
import os
from pathlib import Path

def check_dependencies():
    """检查依赖"""
    required_packages = ['PySide6', 'pandas']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ 缺少依赖包: {', '.join(missing_packages)}")
        print("请安装: pip install PySide6 pandas")
        return False
    
    return True

def main():
    """主函数"""
    print("🚀 启动股票异动告警监控系统...")
    
    # 检查依赖
    if not check_dependencies():
        input("按回车键退出...")
        return
    
    # 设置环境
    project_root = Path(__file__).parent
    os.chdir(project_root)
    sys.path.insert(0, str(project_root))
    
    try:
        # 导入并启动界面
        from alert_monitor_gui import main as gui_main
        gui_main()
    except ImportError as e:
        print(f"❌ 导入界面失败: {e}")
        print("请确保在正确的目录下运行")
        input("按回车键退出...")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        input("按回车键退出...")

if __name__ == '__main__':
    main()