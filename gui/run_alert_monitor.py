"""
启动告警监控界面
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from alert_monitor import main

if __name__ == '__main__':
    # 确保在正确的目录下运行
    os.chdir(project_root)
    
    # 启动告警监控界面
    main()