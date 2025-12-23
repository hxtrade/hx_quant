from datetime import datetime
import pandas as pd
import logging
from collections import defaultdict
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
        self.hold_stocks = []
        self.datafeed = TdxDatafeed()
        self.stocks_cmv_map = {}
        self.stocks_basic_info = {}
        
        
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
        self._log(logging.INFO, f"开始加载买板块股票，板块列表: {monitor_blks}")
        
        # 加载买检测板块股票
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
        try:
            stocks = self.datafeed.get_block_stocks(self.config["monitor_hold_blk"])
            if stocks:
                self.hold_stocks.extend(stocks)
                self._log(logging.INFO, f"从板块 {blk} 加载了 {len(stocks)} 只股票")
            else:
                self._log(logging.WARNING, f"板块 {blk} 没有找到股票")
        except Exception as e:
            self._log(logging.ERROR, f"获取板块 {blk} 股票失败: {e}")
        # 去重
        self.monitor_stocks = list(set(self.monitor_stocks))
        self.hold_stocks = list(set(self.hold_stocks))
        self._log(logging.INFO, f"买单总共需要监控 {len(self.monitor_stocks)} 只股票")
        self._log(logging.INFO, f"持仓总共需要监控 {len(self.hold_stocks)} 只股票")
        
        # 计算流通市值
        self._log(logging.INFO, "开始计算流通市值...")
        success_count = 0

        stocks = self.monitor_stocks + self.hold_stocks
        
        for stock in stocks:
            try:
                # 获取股票价格信息
                quote_data = self.datafeed.get_stock_basic_info(stock)
                if len(quote_data) == 0:
                    self._log(logging.WARNING, f"获取 {stock} 价格信息失败")
                    continue
                self.stocks_basic_info[stock] = quote_data
                # 获取财务信息
                finance_data = self.datafeed.finance(stock)
                if finance_data is None or 'liutongguben' not in finance_data:
                    self._log(logging.WARNING, f"获取 {stock} 财务信息失败")
                    continue
                
                # 计算流通市值
                open_price = quote_data['open']
                circulating_shares = float(finance_data['liutongguben'].iloc[0])
                
                if open_price <= 0 or circulating_shares <= 0:
                    self._log(logging.WARNING, f"股票 {stock} 数据异常：价格={open_price}, 流通股数={circulating_shares}")
                    continue
                
                circulating_market_value = open_price * circulating_shares
                self.stocks_cmv_map[stock] = circulating_market_value
                
                success_count += 1
                self._log(logging.INFO, f"{stock}:{self.stocks_basic_info[stock]['name']}: 流通市值 {circulating_market_value/100000000:,.0f} 亿元")
                
            except Exception as e:
                self._log(logging.ERROR, f"计算 {stock} 流通市值时出错: {e}")
                continue
        
        self._log(logging.INFO, f"成功计算 {success_count}/{len(self.monitor_stocks)+len(self.hold_stocks)} 只股票的流通市值")
        
        if len(self.stocks_cmv_map) == 0:
            self._log(logging.WARNING, "没有成功计算任何股票的流通市值，告警功能可能无法正常工作")
        else:
            self._log(logging.INFO, f"流通市值计算完成，最小市值: {min(self.stocks_cmv_map.values())/100000000:,.0f} 亿元")
            self._log(logging.INFO, f"流通市值计算完成，最大市值: {max(self.stocks_cmv_map.values())/100000000:,.0f} 亿元")
    def run(self):
        alerts = []
        self._log(logging.INFO, f"开始检测连续单...")
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
                continuous_buy_info = self._detect_continuous_orders(transaction, stock, 0)
                if continuous_buy_info:
                    # 创建告警
                    alert = AlertData()
                    alert.name = self.name
                    alert.code = stock
                    alert.stock_name = self.stocks_basic_info[stock]['name']
                    alert.descr = f"检测到连续买单：{continuous_buy_info['description']}"
                    alerts.append(alert)
                    
                    self._log(logging.WARNING, f"告警触发 - {stock}:{alert.stock_name}: {continuous_buy_info['description']}")
                    
            except Exception as e:
                self._log(logging.ERROR, f"处理股票 {stock} 时出错: {e}")
                continue
        
        for stock in self.hold_stocks:
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
                
                # 检测连续卖单
                continuous_sell_info = self._detect_continuous_orders(transaction, stock, 1)
                if continuous_sell_info:
                    # 创建告警
                    alert = AlertData()
                    alert.name = self.name
                    alert.code = stock
                    alert.stock_name = self.stocks_basic_info[stock]['name']
                    alert.descr = f"检测到连续卖单：{continuous_sell_info['description']}"
                    alerts.append(alert)
                    
                    self._log(logging.WARNING, f"告警触发 - {stock}:{alert.stock_name}: {continuous_sell_info['description']}")
                    
            except Exception as e:
                self._log(logging.ERROR, f"处理股票 {stock} 时出错: {e}")
                continue

        return alerts
    
    def _detect_continuous_orders(self, transaction_df: pd.DataFrame, stock: str, buyorsell: int) -> dict:
        """
        检测连续买单或卖单成交额大于流通市值1/500的情况
        每次都重新扫描所有数据，只检测指定类型
        
        Args:
            transaction_df: 交易数据DataFrame
            stock: 股票代码
            buyorsell: 检测类型 (0=买单, 1=卖单)
            
        Returns:
            dict: 检测结果信息，如果没有触发条件返回None
        """
        if transaction_df.empty or stock not in self.stocks_cmv_map:
            return None
        
        circulating_market_value = self.stocks_cmv_map[stock]
        threshold = circulating_market_value / 5000 * 6  # 流通市值的1/500
        
        # 临时变量记录本次扫描的最大连续序列
        max_continuous_count = 0
        max_continuous_amount = 0.0
        max_continuous_start_idx = None
        max_continuous_end_idx = None
        
        # 统计满足阈值的连续序列信息
        qualified_count = 0
        qualified_total_amount = 0.0  # 所有满足条件的连续序列的总成交额
        
        # 当前连续序列的临时状态
        current_count = 0
        current_amount = 0.0
        current_start_idx = None
        

        
        # 遍历所有交易数据
        for i, (_, row) in enumerate(transaction_df.iterrows()):
            buy_or_sell = row.get('buyorsell', 0)
            turnover = row.get('volume', 0)
            
            # 只检测指定类型的连续序列
            if buy_or_sell == buyorsell:
                # 这是目标类型的订单
                if current_count == 0:
                    current_start_idx = i
                
                current_count += 1
                current_amount += turnover
                
                # 更新最大连续序列信息
                if current_count > max_continuous_count:
                    max_continuous_count = current_count
                    max_continuous_amount = current_amount
                    max_continuous_start_idx = current_start_idx
                    max_continuous_end_idx = i
                elif current_count == max_continuous_count:
                    # 如果次数相同，比较成交额
                    if current_amount > max_continuous_amount:
                        max_continuous_amount = current_amount
                        max_continuous_start_idx = current_start_idx
                        max_continuous_end_idx = i
                        
            else:
                # 不是目标类型，重置当前计数
                if current_amount > threshold:
                    qualified_count += 1
                    qualified_total_amount += current_amount  # 累加满足条件的序列成交额
                
                current_count = 0
                current_amount = 0.0
                current_start_idx = None
        
        # 检查最后一个序列是否满足条件
        if current_amount > threshold:
            qualified_count += 1
            qualified_total_amount += current_amount  # 累加满足条件的序列成交额
        
        # 设置结果变量
        order_type = "买" if buyorsell == 0 else "卖"
        qualified_sequences_count = qualified_count
        
        # 检查是否满足条件
        if max_continuous_amount > threshold:
            # 获取时间范围
            start_time = None
            end_time = None
            
            if max_continuous_start_idx is not None:
                start_time = transaction_df.iloc[max_continuous_start_idx].get('time', '')
            
            if max_continuous_end_idx is not None:
                end_time = transaction_df.iloc[max_continuous_end_idx].get('time', '')
            
            # 计算占总成交额的比值
            total_turnover = transaction_df['volume'].sum()
            # 使用所有满足条件的连续序列总成交额计算比值
            qualified_total_ratio = (qualified_total_amount / total_turnover) * 100 if total_turnover > 0 else 0
            # 最大连续序列占总成交额的比值（保留原有逻辑）
            max_continuous_ratio = (max_continuous_amount / total_turnover) * 100 if total_turnover > 0 else 0
            
            # 计算占流通市值的比值
            percentage = (max_continuous_amount / circulating_market_value) * 100
            
            description = (
                f"连续{max_continuous_count}笔{order_type}单，"
                f"成交额{max_continuous_amount/10000:,.0f}万元，"
                f"占总成交额{max_continuous_ratio:.2f}%，"
                f"占流通市值{percentage:.3f}%，"
                f"阈值{threshold/10000:,.0f}万元，"
                f"共出现{qualified_count}次符合条件的连续{order_type}单，"
                f"累计成交额{qualified_total_amount/10000:,.0f}万元，"
                f"占总成交额{qualified_total_ratio:.2f}%"
            )
            
            if start_time and end_time:
                description += f"，时间范围：{start_time} - {end_time}"
            
            return {
                'continuous_count': max_continuous_count,
                'continuous_amount': max_continuous_amount,
                'threshold': threshold,
                'percentage': percentage,
                'total_turnover_ratio': max_continuous_ratio,
                'qualified_count': qualified_count,
                'qualified_total_amount': qualified_total_amount,
                'qualified_total_ratio': qualified_total_ratio,
                'start_time': start_time,
                'end_time': end_time,
                'description': description
            }
        

        
        return None
    

    
