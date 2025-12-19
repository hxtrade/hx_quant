# HX Quant

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**HX Quant** 是一个全面的量化交易框架，专为算法交易、回测和风险管理而设计。该框架提供了丰富的工具集，支持多种数据源、交易策略和回测引擎。

## 🚀 主要特性

### 📊 数据获取与处理
- 支持多种数据源（Tushare、AKShare、BaoStock、CCXT等）
- 实时和历史数据获取
- 数据清洗和预处理工具
- 多格式数据支持（CSV、Parquet、HDF5等）

### 📈 技术指标分析
- 内置丰富的技术指标库
- 基于TA-Lib的专业技术分析
- 自定义指标开发框架
- 指标性能优化

### 🎯 交易策略框架
- 灵活的策略基类
- 多种策略模板
- 策略组合和资金管理
- 风险控制模块

### 🔙 回测引擎
- 高性能向量化回测（VectorBT）
- 事件驱动回测（Backtrader）
- 详细的回测报告
- 多资产组合回测

### 🧠 机器学习集成
- 支持主流ML框架（TensorFlow、PyTorch、XGBoost）
- 特征工程工具
- 模型训练和验证
- 预测策略支持

### 📊 可视化工具
- 交互式图表（Plotly）
- 回测结果可视化
- 性能分析图表
- 实时监控面板

### 🔔 告警系统
- 灵活的告警配置
- 多种通知渠道
- 自定义告警逻辑
- 告警历史记录

## 📦 安装

### 基础安装
```bash
pip install hx-quant
```

### 开发环境安装
```bash
git clone https://github.com/hxquant/hx-quant.git
cd hx-quant
pip install -e ".[dev]"
```

### 完整功能安装
```bash
pip install "hx-quant[all]"
```

### 分模块安装
```bash
# 仅安装核心功能
pip install hx-quant

# 添加回测功能
pip install "hx-quant[backtest]"

# 添加数据获取功能
pip install "hx-quant[data]"

# 添加机器学习功能
pip install "hx-quant[ml]"

# 添加性能优化功能
pip install "hx-quant[performance]"
```

## 🚀 快速开始

### 基本使用示例

```python
from hx_quant import HXQuant
from hx_quant.strategies import MACDStrategy
from hx_quant.data import get_stock_data

# 初始化框架
quant = HXQuant()

# 获取数据
data = get_stock_data("000001.SZ", start="2023-01-01", end="2023-12-31")

# 创建策略
strategy = MACDStrategy()

# 运行回测
results = quant.backtest(strategy, data)

# 显示结果
print(results.summary())
```

### 策略开发示例

```python
from hx_quant.strategies import BaseStrategy
import pandas as pd

class MyStrategy(BaseStrategy):
    def __init__(self):
        super().__init__()
        self.name = "My Custom Strategy"
    
    def generate_signals(self, data):
        # 计算移动平均线
        data['ma_short'] = data['close'].rolling(window=10).mean()
        data['ma_long'] = data['close'].rolling(window=30).mean()
        
        # 生成信号
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0
        signals.loc[data['ma_short'] > data['ma_long'], 'signal'] = 1
        signals.loc[data['ma_short'] < data['ma_long'], 'signal'] = -1
        
        return signals
    
    def calculate_positions(self, signals):
        # 简单的持仓管理
        positions = signals.copy()
        positions['position'] = signals['signal']
        return positions
```

### 告警系统示例

```python
from hx_quant.alerts import PriceAlert, AlertRunner
from hx_quant.alerts_runner import AlertBase

class CustomAlert(AlertBase):
    def __init__(self):
        super().__init__()
        self.threshold = 100.0
    
    def run(self):
        current_price = self.get_current_price("000001.SZ")
        if current_price > self.threshold:
            self.send_alert(f"价格突破: {current_price}")

# 运行告警
AlertRunner.run_alerts("./alerts")
```

## 📁 项目结构

```
hx_quant/
├── hx_quant/                 # 主要代码包
│   ├── __init__.py
│   ├── core/                # 核心功能模块
│   ├── strategies/         # 策略实现
│   │   ├── base.py
│   │   ├── macd.py
│   │   └── rsi.py
│   ├── alerts/             # 告警系统
│   │   ├── alerts_runner.py
│   │   └── base.py
│   ├── utils/              # 工具函数
│   ├── viz/                # 可视化
│   └── cli.py              # 命令行接口
├── tests/                  # 测试文件
├── docs/                   # 文档
├── examples/               # 示例代码
└── config/                 # 配置文件
```

## 🔧 配置

HX Quant 支持多种配置方式：

### 环境变量配置
```bash
export HX_QUANT_DATA_DIR="/path/to/data"
export HX_QUANT_CONFIG_FILE="/path/to/config.yaml"
export HX_QUANT_LOG_LEVEL="INFO"
```

### 配置文件
```yaml
# config.yaml
data:
  cache_dir: "./cache"
  default_source: "tushare"
  
backtest:
  initial_capital: 1000000
  commission: 0.001
  
logging:
  level: "INFO"
  file: "./logs/hx_quant.log"
```

## 📊 性能特性

- **高性能数据处理**: 基于NumPy和Pandas的向量化操作
- **内存优化**: 支持大数据集的内存映射处理
- **并行计算**: 多进程和异步I/O支持
- **缓存机制**: 智能数据缓存提升重复计算性能

## 🤝 贡献指南

我们欢迎所有形式的贡献！

1. Fork 本仓库
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的修改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启一个 Pull Request

### 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/hxquant/hx-quant.git
cd hx-quant

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装开发依赖
pip install -e ".[dev]"

# 安装pre-commit钩子
pre-commit install

# 运行测试
pytest
```

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

## 📚 文档

- [完整文档](https://hx-quant.readthedocs.io/)
- [API参考](https://hx-quant.readthedocs.io/en/latest/api/)
- [示例教程](https://hx-quant.readthedocs.io/en/latest/examples/)
- [贡献指南](https://hx-quant.readthedocs.io/en/latest/contributing/)

## 🆘 支持

- 📧 邮箱: team@hxquant.com
- 🐛 问题反馈: [GitHub Issues](https://github.com/hxquant/hx-quant/issues)
- 💬 讨论: [GitHub Discussions](https://github.com/hxquant/hx-quant/discussions)

## 🌟 致谢

感谢以下开源项目的支持：

- [Pandas](https://pandas.pydata.org/) - 数据处理
- [NumPy](https://numpy.org/) - 数值计算
- [TA-Lib](https://ta-lib.org/) - 技术分析
- [VectorBT](https://vectorbt.dev/) - 向量化回测
- [Backtrader](https://www.backtrader.com/) - 事件驱动回测

## 📈 路线图

- [ ] 支持更多交易所和数据源
- [ ] 增强机器学习功能
- [ ] 实时交易接口
- [ ] Web界面和监控面板
- [ ] 分布式计算支持
- [ ] 更多策略模板和示例

---

**HX Quant** - 让量化交易更简单、更高效！ 🚀