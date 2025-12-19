from datetime import datetime
import pandas as pd
import logging
from alerts.alerts_runner import AlertBase, AlertData
from vnpy.trader.object import HistoryRequest
from vnpy.trader.constant import Exchange, Interval
from vnpy_tdx.tdx_datafeed import TdxDatafeed

class TurnoverAlert(AlertBase):
    """成交额告警类"""
    
    def __init__(self):
        super().__init__()
        self.name = "TurnoverAlert"
        self.monitor_stocks = []
        self.datafeed = TdxDatafeed()
        self.stocks_cmv_map = {}
        
        # 配置日志系统
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.logger.setLevel(logging.INFO)
        
        # 如果没有handler，添加一个控制台handler
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        # 日志开关（可以通过配置控制）
        self.log_enabled = True
        self.log_level = logging.INFO
    
    def _log(self, level: int, message: str):
        """带开关的日志函数"""
        if not self.log_enabled:
            return
        if level >= self.log_level:
            self.logger.log(level, message)
    
    def configure_logging(self, enabled: bool = True, level: int = logging.INFO):
        """配置日志开关和级别
        
        Args:
            enabled: 是否启用日志
            level: 日志级别 (logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR)
        """
        self.log_enabled = enabled
        self.log_level = level
        if enabled:
            self.logger.setLevel(level)
            for handler in self.logger.handlers:
                handler.setLevel(level)
    
    def pre_run(self):
        """预处理阶段：加载监控股票列表和计算流通市值"""
        if "monitor_blks" not in self.config:
            self._log(logging.ERROR, "配置中缺少monitor_blks字段")
            return
        
        monitor_blks = self.config["monitor_blks"]
        self._log(logging.INFO, f"开始加载板块股票，板块列表: {monitor_blks}")
        
        # 加载板块股票
        for blk in monitor_blks:
            try:
                stocks = self.datafeed.get_block_stocks(blk)
                if stocks:
                    self.monitor_stocks.extend(stocks)
                    self._log(logging.INFO, f"从板块 {blk} 加载了 {len(stocks)} 只股票")
                else:
                    self._log(logging.WARNING, f"板块 {blk} 没有找到股票")
            except Exception as e:
                self._log(logging.ERROR, f"获取板块 {blk} 股票失败: {e}")
                continue
        
        # 去重
        self.monitor_stocks = list(set(self.monitor_stocks))
        self._log(logging.INFO, f"总共需要监控 {len(self.monitor_stocks)} 只股票")
        
        # 计算流通市值
        self._log(logging.INFO, "开始计算流通市值...")
        success_count = 0
        
        for stock in self.monitor_stocks:
            try:
                # 获取股票价格信息
                req = HistoryRequest(
                    symbol=stock,
                    exchange=Exchange.SZSE if stock.startswith(('000', '002', '300')) else Exchange.SSE,
                    interval=Interval.DAILY,
                    start=datetime.now(),
                    end=datetime.now(),
                )
                quote_data = self.datafeed.query_bar_history(req)
                if len(quote_data) == 0:
                    self._log(logging.WARNING, f"获取 {stock} 价格信息失败")
                    continue
                
                # 获取财务信息
                finance_data = self.datafeed.finance(stock)
                if finance_data is None or 'liutongguben' not in finance_data:
                    self._log(logging.WARNING, f"获取 {stock} 财务信息失败")
                    continue
                
                # 计算流通市值
                open_price = float(quote_data[0].open_price)
                circulating_shares = float(finance_data['liutongguben'].iloc[0])
                
                if open_price <= 0 or circulating_shares <= 0:
                    self._log(logging.WARNING, f"股票 {stock} 数据异常：价格={open_price}, 流通股数={circulating_shares}")
                    continue
                
                circulating_market_value = open_price * circulating_shares
                self.stocks_cmv_map[stock] = circulating_market_value
                
                success_count += 1
                self._log(logging.INFO, f"{stock}: 流通市值 {circulating_market_value/100000000:,.0f} 亿元")
                
            except Exception as e:
                self._log(logging.ERROR, f"计算 {stock} 流通市值时出错: {e}")
                continue
        
        self._log(logging.INFO, f"成功计算 {success_count}/{len(self.monitor_stocks)} 只股票的流通市值")
        
        if len(self.stocks_cmv_map) == 0:
            self._log(logging.WARNING, "没有成功计算任何股票的流通市值，告警功能可能无法正常工作")
        else:
            self._log(logging.INFO, f"流通市值计算完成，最小市值: {min(self.stocks_cmv_map.values())/100000000:,.0f} 亿元")
            self._log(logging.INFO, f"流通市值计算完成，最大市值: {max(self.stocks_cmv_map.values())/100000000:,.0f} 亿元")
    def run(self):
        alerts = []
        for stock in self.monitor_stocks:
            try:
                req = HistoryRequest(
                    symbol=stock,
                    exchange=Exchange.SZSE if stock.startswith(('000', '002', '300')) else Exchange.SSE,
                    interval=Interval.TICK,
                    start=datetime.now(),
                    end=datetime.now(),
                )
                transaction = self.datafeed.query_transaction_history(req)
                
                if transaction is None or transaction.empty:
                    continue
                
                # 检测连续买单
                continuous_buy_info = self._detect_continuous_buy_orders(transaction, stock)
                if continuous_buy_info:
                    # 创建告警
                    alert = AlertData()
                    alert.name = self.name
                    alert.code = stock
                    alert.descr = f"检测到连续买单：{continuous_buy_info['description']}"
                    alerts.append(alert)
                    
                    self._log(logging.WARNING, f"告警触发 - {stock}: {continuous_buy_info['description']}")
                    
            except Exception as e:
                self._log(logging.ERROR, f"处理股票 {stock} 时出错: {e}")
                continue
        
        return alerts
    
    def _detect_continuous_buy_orders(self, transaction_df: pd.DataFrame, stock: str) -> dict:
        """
        检测连续买单成交额大于流通市值1/500的情况
        
        Args:
            transaction_df: 交易数据DataFrame
            stock: 股票代码
            
        Returns:
            dict: 检测结果信息，如果没有触发条件返回None
        """
        if transaction_df.empty or stock not in self.stocks_cmv_map:
            return None
        
        circulating_market_value = self.stocks_cmv_map[stock]
        threshold = circulating_market_value / 5000 * 6  # 流通市值的1/500
        # print(transaction_df)
        # 检测连续买单
        continuous_buy_count = 0
        max_continuous_count = 0
        continuous_buy_amount = 0.0
        max_continuous_amount = 0.0
        
        # 记录最大的连续买单信息
        max_continuous_start_idx = None
        max_continuous_end_idx = None
        
        current_continuous_start_idx = None
        
        for idx, row in transaction_df.iterrows():
            # 判断是否为买单：买入量大于卖出量
            buy_or_sell = row.get('buyorsell', 0)
            turnover = row.get('volume', 0)
            
            if buy_or_sell == 0:
                # 这是买单
                if continuous_buy_count == 0:
                    current_continuous_start_idx = idx
                
                continuous_buy_count += 1
                continuous_buy_amount += turnover
                
                # 更新最大值
                if continuous_buy_count > max_continuous_count:
                    max_continuous_count = continuous_buy_count
                    max_continuous_amount = continuous_buy_amount
                    max_continuous_start_idx = current_continuous_start_idx
                    max_continuous_end_idx = idx
                elif continuous_buy_count == max_continuous_count:
                    # 如果次数相同，比较成交额
                    if continuous_buy_amount > max_continuous_amount:
                        max_continuous_amount = continuous_buy_amount
                        max_continuous_start_idx = current_continuous_start_idx
                        max_continuous_end_idx = idx
            else:
                # 不是买单，重置计数
                continuous_buy_count = 0
                continuous_buy_amount = 0.0
                current_continuous_start_idx = None
        
        # 检查是否满足条件
        if max_continuous_amount > threshold:
            # 获取时间范围
            start_time = transaction_df.loc[max_continuous_start_idx, 'time'] if max_continuous_start_idx in transaction_df.index else None
            end_time = transaction_df.loc[max_continuous_end_idx, 'time'] if max_continuous_end_idx in transaction_df.index else None
            
            # 计算占比
            percentage = (max_continuous_amount / circulating_market_value) * 100
            
            description = (
                f"连续{max_continuous_count}笔买单，"
                f"成交额{max_continuous_amount/10000:,.0f}万元，"
                f"占流通市值{percentage:.3f}%，"
                f"阈值{threshold/10000:,.0f}万元"
            )
            
            if start_time and end_time:
                description += f"，时间范围：{start_time} - {end_time}"
            
            return {
                'continuous_count': max_continuous_count,
                'continuous_amount': max_continuous_amount,
                'threshold': threshold,
                'percentage': percentage,
                'start_time': start_time,
                'end_time': end_time,
                'description': description
            }
        
        return None