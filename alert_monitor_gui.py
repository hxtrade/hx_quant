"""
股票异动告警监控界面 - 简化单文件版本
"""

import sys
import os
from datetime import datetime
from typing import List, Dict, Any
from collections import defaultdict
import re

import pandas as pd
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QLabel, QSplitter,
    QTextEdit, QGroupBox, QPushButton, QHeaderView,
    QProgressBar, QStatusBar, QMessageBox, QFileDialog
)
from PySide6.QtCore import QTimer, Qt, QThread, Signal, QObject
from PySide6.QtGui import QFont, QColor

# 尝试导入告警模块
try:
    from alerts.alerts_runner import AlertsRunner
    ALERTS_AVAILABLE = True
except ImportError as e:
    print(f"警告: 无法导入告警模块 - {e}")
    ALERTS_AVAILABLE = False


class AlertWorker(QObject):
    """告警工作线程"""
    alert_updated = Signal(list)  # 发送告警列表更新信号
    error_occurred = Signal(str)  # 错误信号
    status_updated = Signal(str)  # 状态更新信号
    batch_complete = Signal()  # 批量更新完成信号
    
    def __init__(self):
        super().__init__()
        self.is_running = False
        self.initialized = False
        self.timer = None  # 工作线程内部的定时器
        
    def initialize_alerts(self):
        """初始化告警模块"""
        if not ALERTS_AVAILABLE:
            self.error_occurred.emit("告警模块不可用")
            return False
            
        try:
            self.status_updated.emit("正在初始化告警模块...")
            # 设置配置路径
            AlertsRunner.set_conf_path(".vntrader")
            # 查找并加载所有告警
            AlertsRunner.find_alerts("alerts")
            self.initialized = True
            self.status_updated.emit("告警模块初始化完成")
            return True
        except Exception as e:
            self.error_occurred.emit(f"初始化失败: {e}")
            return False
        
    def start_monitoring(self):
        """开始监控"""
        if not self.initialized and not self.initialize_alerts():
            return
            
        try:
            self.is_running = True
            self.status_updated.emit("监控已启动")
            
            # 创建工作线程内部的定时器
            self.timer = QTimer()
            self.timer.timeout.connect(self.run_once)
            self.timer.start(3000)  # 每3秒检查一次
            
        except Exception as e:
            self.error_occurred.emit(f"启动失败: {e}")
        
    def stop_monitoring(self):
        """停止监控"""
        self.is_running = False
        if self.timer:
            self.timer.stop()
            self.timer = None
        self.status_updated.emit("监控已停止")
        
    def run_once(self):
        """执行一次检测 - 在工作线程中执行"""
        if not self.is_running or not self.initialized:
            return
            
        try:
            self.status_updated.emit("正在检测告警...")
            # 使用新的run_alerts方法
            all_alerts = AlertsRunner.run_alerts()
            # 展平告警列表（因为每个alert.run()返回一个列表）
            alerts = []
            for alert_list in all_alerts:
                if alert_list:  # 确保不是None或空列表
                    alerts.extend(alert_list)
            
            # 逐个发送告警，实现实时更新
            if alerts:
                self.status_updated.emit(f"发现 {len(alerts)} 个告警")
                for alert in alerts:
                    self.alert_updated.emit([alert])  # 每次发送单个告警
                self.batch_complete.emit()  # 发送批量完成信号
            else:
                self.status_updated.emit("无新告警")
                
        except Exception as e:
            self.error_occurred.emit(f"检测出错: {e}")


class AlertMonitorWindow(QMainWindow):
    """告警监控主窗口"""
    
    def __init__(self):
        super().__init__()
        self.alerts_history = []  # 存储历史告警
        self.buy_alerts = []  # 当前买入告警列表
        self.sell_alerts = []  # 当前卖出告警列表
        self.buy_stats = defaultdict(lambda: {'count': 0, 'total_amount': 0, 'total_ratio': 0})  # 买入统计
        self.sell_stats = defaultdict(lambda: {'count': 0, 'total_amount': 0, 'total_ratio': 0})  # 卖出统计
        self.is_monitoring = False
        
        # 创建工作线程
        self.thread = QThread()
        self.worker = AlertWorker()
        self.worker.moveToThread(self.thread)
        
        # 连接信号
        self.thread.started.connect(self.worker.start_monitoring)
        self.worker.alert_updated.connect(self.update_alerts)
        self.worker.error_occurred.connect(self.show_error)
        self.worker.status_updated.connect(self.update_status)
        self.worker.batch_complete.connect(self.batch_update_complete)
        
        # 初始化界面
        self.init_ui()
        
        # 启动线程
        self.thread.start()
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("股票异动告警监控系统 v1.0")
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建控制按钮
        control_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("开始监控")
        self.start_btn.clicked.connect(self.start_monitoring)
        self.start_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; }")
        control_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("停止监控")
        self.stop_btn.clicked.connect(self.stop_monitoring)
        self.stop_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 8px; }")
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)
        
        self.clear_btn = QPushButton("清空记录")
        self.clear_btn.clicked.connect(self.clear_history)
        control_layout.addWidget(self.clear_btn)
        
        self.export_btn = QPushButton("导出数据")
        self.export_btn.clicked.connect(self.export_alerts)
        control_layout.addWidget(self.export_btn)
        
        control_layout.addStretch()
        
        main_layout.addLayout(control_layout)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 左侧：告警列表
        left_widget = self.create_alert_list_widget()
        splitter.addWidget(left_widget)
        
        # 右侧：详细信息
        right_widget = self.create_detail_widget()
        splitter.addWidget(right_widget)
        
        # 设置分割器比例
        splitter.setSizes([900, 500])
        
        # 创建状态栏
        self.create_status_bar()
        

        
    def create_alert_list_widget(self):
        """创建告警列表部件"""
        group_box = QGroupBox("📊 实时告警列表")
        layout = QVBoxLayout(group_box)
        
        # 创建统一的告警表格
        self.alert_table = QTableWidget()
        self.alert_table.setColumnCount(10)
        self.alert_table.setHorizontalHeaderLabels([
            "⏰ 时间", "📈 股票代码", "🏢 股票名称", "🔢 连续次数", 
            "📈 出现次数", "💰 累计成交额(万元)", "📊 累计占比(%)", 
            "💰 当前成交额(万元)", "📊 当前占比(%)", "📝 详细信息"
        ])
        
        # 设置表格属性
        self.alert_table.setAlternatingRowColors(True)
        self.alert_table.setSortingEnabled(True)
        self.alert_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        # 设置列宽
        header = self.alert_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 时间
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 代码
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 名称
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 连续次数
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 出现次数
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # 累计成交额
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # 累计占比
        header.setSectionResizeMode(7, QHeaderView.Stretch)  # 当前成交额
        header.setSectionResizeMode(8, QHeaderView.Stretch)  # 当前占比
        header.setSectionResizeMode(9, QHeaderView.Stretch)  # 详细信息
        
        # 设置字体
        self.alert_table.setFont(QFont("微软雅黑", 9))
        
        # 连接选择事件
        self.alert_table.itemSelectionChanged.connect(self.on_alert_selected)
        
        layout.addWidget(self.alert_table)
        
        return group_box
        
    def create_detail_widget(self):
        """创建详细信息部件"""
        group_box = QGroupBox("📋 详细信息与统计")
        layout = QVBoxLayout(group_box)
        
        # 统计信息
        self.stats_label = QLabel("📊 告警统计")
        self.stats_label.setFont(QFont("微软雅黑", 10, QFont.Bold))
        self.stats_label.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 10px; border: 1px solid #ccc; }")
        layout.addWidget(self.stats_label)
        
        # 详细信息文本框
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setFont(QFont("Consolas", 9))
        self.detail_text.setMaximumHeight(400)
        layout.addWidget(self.detail_text)
        
        return group_box
        
    def create_status_bar(self):
        """创建状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 状态标签
        self.status_label = QLabel("🟢 就绪")
        self.status_bar.addWidget(self.status_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        

            
    def start_monitoring(self):
        """开始监控"""
        if not ALERTS_AVAILABLE:
            QMessageBox.critical(self, '错误', '告警模块不可用，请检查依赖安装')
            return
            
        self.is_monitoring = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        # 工作线程内部会启动定时器
        self.status_label.setText("🟢 启动监控中...")
        
    def stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        # 通知工作线程停止监控
        self.worker.stop_monitoring()
        
    def update_alerts(self, alerts):
        """更新告警列表 - 支持实时单告警更新，区分买入卖出"""
        if not alerts:
            return
            
        current_time = datetime.now().strftime("%H:%M:%S")
        alert = alerts[0]  # 每次处理单个告警
        
        # 确保alert对象有必要的属性
        if not hasattr(alert, 'code') or not hasattr(alert, 'stock_name'):
            return
            
        # 解析描述信息确定是买入还是卖出
        description = getattr(alert, 'descr', '')
        is_buy = "买单" in description
        is_sell = "卖单" in description
        
        # 创建告警数据
        alert_data = {
            'time': current_time,
            'code': alert.code,
            'stock_name': alert.stock_name,
            'name': getattr(alert, 'name', '异动'),
            'description': description,
            'type': 'buy' if is_buy else 'sell' if is_sell else 'unknown'
        }
        
        # 解析成交额和占比信息
        continuous_count = self.extract_value(description, r"连续(\d+)笔")
        qualified_count = self.extract_value(description, r"共出现(\d+)次")
        current_amount = self.extract_value(description, r"成交额([\d,]+)万元")
        current_ratio = self.extract_value(description, r"占总成交额([\d.]+)%")
        market_ratio = self.extract_value(description, r"占流通市值([\d.]+)%")
        
        alert_data.update({
            'continuous_count': int(continuous_count) if continuous_count else 0,
            'qualified_count': int(qualified_count) if qualified_count else 0,
            'current_amount': float(current_amount.replace(',', '')) if current_amount else 0,
            'current_ratio': float(current_ratio) if current_ratio else 0,
            'market_ratio': float(market_ratio) if market_ratio else 0
        })
        
        # 添加到历史记录（保留所有历史）
        self.alerts_history.append(alert_data)
        
        # 统一处理所有告警
        self._update_alert(alert_data)
        
        # 更新统计
        if len(self.alerts_history) % 3 == 0:  # 减少更新频率
            self.update_statistics()
            
    def _update_alert(self, alert_data):
        """更新告警 - 统一处理买入和卖出"""
        # 合并告警列表，按股票代码去重（保留最新的）
        all_alerts = []
        seen_codes = set()
        
        # 先添加现有的其他股票告警
        for alert in self.buy_alerts + self.sell_alerts:
            if alert['code'] != alert_data['code']:
                all_alerts.append(alert)
                seen_codes.add(alert['code'])
        
        # 添加或更新当前告警
        existing_index = None
        for i, current_alert in enumerate(all_alerts):
            if current_alert['code'] == alert_data['code']:
                existing_index = i
                break
        
        if existing_index is not None:
            # 更新现有告警
            old_data = all_alerts[existing_index]
            # 累计成交额和占比
            alert_data['total_amount'] = old_data.get('total_amount', 0) + alert_data['current_amount']
            alert_data['total_ratio'] = old_data.get('total_ratio', 0) + alert_data['current_ratio']
            
            all_alerts[existing_index] = alert_data
            if self.is_monitoring:
                alert_type = "买入" if alert_data['type'] == 'buy' else "卖出"
                self.status_label.setText(f"🔄 更新{alert_type} {alert_data['stock_name']}({alert_data['code']})")
        else:
            # 新告警
            alert_data['total_amount'] = alert_data['current_amount']
            alert_data['total_ratio'] = alert_data['current_ratio']
            all_alerts.append(alert_data)
            if self.is_monitoring:
                alert_type = "买入异动" if alert_data['type'] == 'buy' else "卖出异动"
                self.status_label.setText(f"🆕 新{alert_type} {alert_data['stock_name']}({alert_data['code']})")
        
        # 分别更新买入和卖出告警列表
        self.buy_alerts = [a for a in all_alerts if a['type'] == 'buy']
        self.sell_alerts = [a for a in all_alerts if a['type'] == 'sell']
        
        # 更新统计
        if alert_data['type'] == 'buy':
            stats = self.buy_stats[alert_data['stock_name']]
        else:
            stats = self.sell_stats[alert_data['stock_name']]
        stats['count'] += 1
        stats['total_amount'] = alert_data.get('total_amount', alert_data['current_amount'])
        stats['total_ratio'] = alert_data.get('total_ratio', alert_data['current_ratio'])
        
        # 更新统一表格
        self.refresh_alert_table()
            
    def batch_update_complete(self):
        """批量更新完成后的最终状态更新"""
        if self.is_monitoring:
            self.update_statistics()
            self.status_label.setText("✅ 监控中 - 实时更新")
            
    def refresh_alert_table(self):
        """刷新统一告警表格"""
        # 清空表格
        self.alert_table.setRowCount(0)
        
        # 合并买入和卖出告警，按时间排序
        all_alerts = self.buy_alerts + self.sell_alerts
        all_alerts.sort(key=lambda x: x['time'], reverse=True)
        
        # 添加到表格
        for alert_data in all_alerts:
            self.add_alert_to_table(alert_data)
    
    def add_alert_to_table(self, alert_data):
        """添加告警到统一表格"""
        row = self.alert_table.rowCount()
        self.alert_table.insertRow(row)
        
        # 设置表格项
        self.alert_table.setItem(row, 0, QTableWidgetItem(alert_data['time']))
        self.alert_table.setItem(row, 1, QTableWidgetItem(alert_data['code']))
        self.alert_table.setItem(row, 2, QTableWidgetItem(alert_data['stock_name']))
        self.alert_table.setItem(row, 3, QTableWidgetItem(str(alert_data.get('continuous_count', 0))))
        self.alert_table.setItem(row, 4, QTableWidgetItem(str(alert_data.get('qualified_count', 0))))
        self.alert_table.setItem(row, 5, QTableWidgetItem(f"{alert_data.get('total_amount', 0):.2f}"))
        self.alert_table.setItem(row, 6, QTableWidgetItem(f"{alert_data.get('total_ratio', 0):.2f}%"))
        self.alert_table.setItem(row, 7, QTableWidgetItem(f"{alert_data.get('current_amount', 0):.2f}"))
        self.alert_table.setItem(row, 8, QTableWidgetItem(f"{alert_data.get('current_ratio', 0):.2f}%"))
        self.alert_table.setItem(row, 9, QTableWidgetItem(alert_data['description'][:50] + "..." if len(alert_data['description']) > 50 else alert_data['description']))
        
        # 根据买卖类型设置颜色
        is_buy = alert_data['type'] == 'buy'
        if is_buy:
            # 买入：绿色系
            bg_color = QColor(240, 255, 240)  # 浅绿背景
            text_color = QColor(0, 150, 0)     # 绿色文字
        else:
            # 卖出：红色系
            bg_color = QColor(255, 240, 240)  # 浅红背景
            text_color = QColor(200, 0, 0)     # 红色文字
        
        for col in range(10):
            item = self.alert_table.item(row, col)
            if item:
                item.setBackground(bg_color)
                if col == 3 or col == 4:  # 连续次数和出现次数列特殊颜色
                    item.setForeground(text_color)
        
        # 在股票代码列添加买卖标识
        if row < self.alert_table.rowCount():
            code_item = self.alert_table.item(row, 1)
            if code_item:
                code_item.setText(f"{'🟢' if is_buy else '🔴'} {alert_data['code']}")
        
    def extract_value(self, text, pattern):
        """从文本中提取数值"""
        match = re.search(pattern, text)
        return match.group(1) if match else None
        
    def on_alert_selected(self):
        """告警选择事件"""
        current_row = self.alert_table.currentRow()
        if current_row >= 0:
            # 获取选中的告警数据
            code_item = self.alert_table.item(current_row, 1)
            if code_item:
                # 移除买卖标识获取股票代码
                code = code_item.text().replace('🟢 ', '').replace('🔴 ', '')
                
                # 在买入告警中查找
                alert_data = None
                for alert in self.buy_alerts + self.sell_alerts:
                    if alert['code'] == code:
                        alert_data = alert
                        break
                
                if alert_data:
                    self.show_alert_detail(alert_data)
            
    def show_alert_detail(self, alert_data):
        """显示告警详情"""
        alert_type = "买入异动" if alert_data['type'] == 'buy' else "卖出异动" if alert_data['type'] == 'sell' else "未知异动"
        stats = self.buy_stats[alert_data['stock_name']] if alert_data['type'] == 'buy' else self.sell_stats[alert_data['stock_name']]
        
        detail_text = f"""
📈 股票代码: {alert_data['code']}
🏢 股票名称: {alert_data['stock_name']}
⏰ 告警时间: {alert_data['time']}
⚠️ 异动类型: {alert_type}

📊 当前异动:
• 连续次数: {alert_data.get('continuous_count', 0)} 笔
• 当前成交额: {alert_data.get('current_amount', 0):.2f} 万元
• 当前占比: {alert_data.get('current_ratio', 0):.2f}%
• 占流通市值: {alert_data.get('market_ratio', 0):.2f}%

📈 累计统计:
• 累计连续次数: {stats['count']} 次
• 累计成交额: {stats['total_amount']:.2f} 万元
• 累计占比: {stats['total_ratio']:.2f}%

📝 详细描述: {alert_data['description']}
        """.strip()
        
        self.detail_text.setPlainText(detail_text)
        
    def update_statistics(self):
        """更新统计信息 - 分别显示买入和卖出统计"""
        # 计算买入统计
        buy_unique = len(set([a['stock_name'] for a in self.alerts_history if a.get('type') == 'buy']))
        
        # 计算卖出统计
        sell_unique = len(set([a['stock_name'] for a in self.alerts_history if a.get('type') == 'sell']))
        
        
        stats_text = f"""
📊 今日异动统计:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🟢 买入异动:
  • 异动股票: {buy_unique} 只

🔴 卖出异动:
  • 异动股票: {sell_unique} 只

🏆 买入活跃度 Top 5:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{self.get_top_buy_stocks(5)}

🏆 卖出活跃度 Top 5:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{self.get_top_sell_stocks(5)}
        """.strip()
        
        self.stats_label.setText(stats_text)
        
    def is_recent_alert(self, time_str):
        """判断是否为最近5分钟的告警"""
        try:
            current = datetime.now()
            alert_time = datetime.strptime(time_str, "%H:%M:%S")
            alert_datetime = current.replace(
                hour=alert_time.hour, 
                minute=alert_time.minute, 
                second=alert_time.second
            )
            return (current - alert_datetime).total_seconds() < 300
        except:
            return False
            
    def get_top_buy_stocks(self, top_n=5):
        """获取买入次数最多的股票"""
        if not self.buy_stats:
            return "暂无买入数据"
            
        sorted_stocks = sorted(self.buy_stats.items(), 
                           key=lambda x: x[1]['count'], reverse=True)
        result = []
        for i, (stock, stats) in enumerate(sorted_stocks[:top_n]):
            result.append(f"  {i+1:2d}. {stock:8s}: {stats['count']:2d}次 ({stats['total_amount']:.1f}万元)")
        return "\n".join(result)
        
    def get_top_sell_stocks(self, top_n=5):
        """获取卖出次数最多的股票"""
        if not self.sell_stats:
            return "暂无卖出数据"
            
        sorted_stocks = sorted(self.sell_stats.items(), 
                           key=lambda x: x[1]['count'], reverse=True)
        result = []
        for i, (stock, stats) in enumerate(sorted_stocks[:top_n]):
            result.append(f"  {i+1:2d}. {stock:8s}: {stats['count']:2d}次 ({stats['total_amount']:.1f}万元)")
        return "\n".join(result)
        
    def clear_history(self):
        """清空历史记录"""
        reply = QMessageBox.question(
            self, '确认清空', '确定要清空所有历史记录吗？\n此操作不可撤销！',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.alerts_history.clear()
            self.buy_alerts.clear()
            self.sell_alerts.clear()
            self.buy_stats.clear()
            self.sell_stats.clear()
            self.alert_table.setRowCount(0)
            self.detail_text.clear()
            self.update_statistics()
            self.status_label.setText("🗑️ 历史记录已清空")
            
    def export_alerts(self):
        """导出告警数据"""
        if not self.alerts_history:
            QMessageBox.information(self, '提示', '没有告警数据可导出')
            return
            
        filename, _ = QFileDialog.getSaveFileName(
            self, '导出告警数据', f'alerts_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
            'CSV文件 (*.csv);;Excel文件 (*.xlsx)'
        )
        
        if filename:
            try:
                df = pd.DataFrame(self.alerts_history)
                if filename.endswith('.xlsx'):
                    df.to_excel(filename, index=False, engine='openpyxl')
                else:
                    df.to_csv(filename, index=False, encoding='utf-8-sig')
                QMessageBox.information(self, '✅ 成功', f'告警数据已导出到:\n{filename}')
            except Exception as e:
                QMessageBox.critical(self, '❌ 错误', f'导出失败:\n{str(e)}')
                
    def update_status(self, message):
        """更新状态信息"""
        if "检测中" in message:
            self.status_label.setText("🔄 " + message)
        elif "无新告警" in message:
            self.status_label.setText("✅ 监控中 - 无新告警")
        elif "监控已启动" in message:
            self.status_label.setText("🟢 监控已启动")
        elif "监控已停止" in message:
            self.status_label.setText("🔴 监控已停止")
        elif "初始化" in message:
            self.status_label.setText("⚙️ " + message)
        else:
            self.status_label.setText("📊 " + message)
        
    def show_error(self, message):
        """显示错误信息"""
        self.status_label.setText(f"❌ {message}")
        QMessageBox.warning(self, '错误', message)
                
    def closeEvent(self, event):
        """关闭事件"""
        self.is_monitoring = False
        self.worker.stop_monitoring()
        self.thread.quit()
        self.thread.wait(20000)
        event.accept()


def main():
    """主函数"""
    # 确保在正确的目录下运行
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    # 设置应用信息
    app.setApplicationName("股票异动告警监控系统")
    app.setApplicationVersion("1.0")
    
    # 创建主窗口
    window = AlertMonitorWindow()
    window.show()
    
    # 显示启动信息
    if not ALERTS_AVAILABLE:
        QMessageBox.warning(
            window, '警告', 
            '告警模块不可用，请确保已安装必要的依赖包。\n'
            '界面将以演示模式运行。'
        )
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()