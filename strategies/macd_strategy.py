from vnpy_ctastrategy import (
    CtaTemplate,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData,
    BarGenerator,
    ArrayManager,
)
import talib


class MacdStrategy(CtaTemplate):
    """MACD金叉买入、死叉卖出策略"""

    author = "Your Name"

    # 策略参数
    fast_period = 12  # 快速EMA周期
    slow_period = 26  # 慢速EMA周期
    signal_period = 9  # 信号线周期
    fixed_size = 1  # 每次交易数量

    # 策略变量
    dif = 0.0
    dea = 0.0
    macd = 0.0
    dif_history = []  # 保存 dif 历史值
    dea_history = []  # 保存 dea 历史值

    parameters = ["fast_period", "slow_period", "signal_period", "fixed_size"]
    variables = ["dif", "dea", "macd"]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """初始化策略"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.bg = BarGenerator(self.on_bar)
        self.am = ArrayManager()

    def on_init(self):
        """初始化回调"""
        self.write_log("策略初始化")
        self.load_bar(10)

    def on_start(self):
        """启动回调"""
        self.write_log("策略启动")
        self.put_event()

    def on_stop(self):
        """停止回调"""
        self.write_log("策略停止")
        self.put_event()

    def on_tick(self, tick: TickData):
        """Tick更新回调"""
        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData):
        """K线更新回调"""
        self.cancel_all()

        # 更新K线数据
        self.am.update_bar(bar)
        if not self.am.inited:
            return

        # 计算MACD指标
        close = self.am.close_array
        dif, dea, macd = talib.MACD(
            close,
            fastperiod=self.fast_period,
            slowperiod=self.slow_period,
            signalperiod=self.signal_period,
        )
        self.dif = dif[-1]
        self.dea = dea[-1]
        self.macd = macd[-1]

        # 保存历史值（保留最近 10 个值）
        self.dif_history.append(self.dif)
        self.dea_history.append(self.dea)
        if len(self.dif_history) > 10:
            self.dif_history.pop(0)
            self.dea_history.pop(0)

        # 检查金叉和死叉
        if len(self.dif_history) >= 2:
            if self.dif > self.dea and self.dif_history[-2] <= self.dea_history[-2]:
                # 金叉逻辑
                if self.pos == 0:
                    self.buy(bar.close_price, self.fixed_size)
                elif self.pos < 0:
                    self.cover(bar.close_price, self.fixed_size)
                    self.buy(bar.close_price, self.fixed_size)
            elif self.dif < self.dea and self.dif_history[-2] >= self.dea_history[-2]:
                # 死叉逻辑
                if self.pos == 0:
                    self.short(bar.close_price, self.fixed_size)
                elif self.pos > 0:
                    self.sell(bar.close_price, self.fixed_size)
                    self.short(bar.close_price, self.fixed_size)

        self.put_event()

    def on_order(self, order: OrderData):
        """订单更新回调"""
        pass

    def on_trade(self, trade: TradeData):
        """成交更新回调"""
        self.put_event()

    def on_stop_order(self, stop_order: StopOrder):
        """停止单更新回调"""
        pass