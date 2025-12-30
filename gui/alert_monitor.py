"""
告警监控界面
显示出现异动告警的股票列表
"""

import sys
import time
from datetime import datetime
from typing import List, Dict, Any
from collections import defaultdict

import pandas as pd
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QLabel, QSplitter,
    QTextEdit, QGroupBox, QPushButton, QHeaderView,
    QProgressBar, QStatusBar, QMessageBox, QFileDialog
)
from PySide6.QtCore import QTimer, Qt, QThread, Signal, QObject
from PySide6.QtGui import QFont, QColor

from alerts.alerts_runner import AlertsRunner
from alerts.turnover_alert import TurnoverAlert


class AlertWorker(QObject):
    """告警工作线程"""
    alert_updated = Signal(list)  # 发送告警列表更新信号
    
    def __init__(self):
        super().__init__()
        self.alerts_runner = AlertsRunner()
        self.alert = TurnoverAlert()
        self.is_running = False
        
    def start_monitoring(self):
        """开始监控"""
        self.is_running = True
        self.alert.load_config(".vntrader/turnover_alert_setting.json")
        self.alert.pre_run()
        
    def stop_monitoring(self):
        """停止监控"""
        self.is_running = False
        
    def run_once(self):
        """执行一次检测"""
        if not self.is_running:
            return
            
        try:
            alerts = self.alert.run()
            self.alert_updated.emit(alerts)
        except Exception as e:
            print(f"检测过程中出错: {e}")


class AlertMonitorWindow(QMainWindow):
    """告警监控主窗口"""
    
    def __init__(self):
        super().__init__()
        self.alerts_history = []  # 存储历史告警
        self.current_alerts = []  # 当前告警列表
        self.alert_stats = defaultdict(int)  # 告警统计
        
        # 创建工作线程
        self.thread = QThread()
        self.worker = AlertWorker()
        self.worker.moveToThread(self.thread)
        
        # 连接信号
        self.thread.started.connect(self.worker.start_monitoring)
        self.worker.alert_updated.connect(self.update_alerts)
        
        # 初始化界面
        self.init_ui()
        
        # 启动线程
        self.thread.start()
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("股票异动告警监控")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout(central_widget)
        
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
        splitter.setSizes([800, 400])
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建状态栏
        self.create_status_bar()
        
        # 设置定时器
        self.setup_timer()
        
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        export_action = QAction('导出告警', self)
        export_action.triggered.connect(self.export_alerts)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('退出', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 视图菜单
        view_menu = menubar.addMenu('视图')
        
        clear_action = QAction('清空历史', self)
        clear_action.triggered.connect(self.clear_history)
        view_menu.addAction(clear_action)
        
    def create_status_bar(self):
        """创建状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_bar.addWidget(self.status_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
    def create_alert_list_widget(self):
        """创建告警列表部件"""
        group_box = QGroupBox("实时告警")
        layout = QVBoxLayout(group_box)
        
        # 创建表格
        self.alert_table = QTableWidget()
        self.alert_table.setColumnCount(7)
        self.alert_table.setHorizontalHeaderLabels([
            "时间", "股票代码", "股票名称", "类型", "连续次数", 
            "成交额(万元)", "占流通市值(%)"
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
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 类型
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 次数
        header.setSectionResizeMode(5, QHeaderView.Stretch)  # 成交额
        header.setSectionResizeMode(6, QHeaderView.Stretch)  # 占比
        
        # 连接选择事件
        self.alert_table.itemSelectionChanged.connect(self.on_alert_selected)
        
        layout.addWidget(self.alert_table)
        
        return group_box
        
    def create_detail_widget(self):
        """创建详细信息部件"""
        group_box = QGroupBox("详细信息")
        layout = QVBoxLayout(group_box)
        
        # 统计信息
        stats_layout = QVBoxLayout()
        
        self.stats_label = QLabel("告警统计")
        self.stats_label.setFont(QFont("Arial", 10, QFont.Bold))
        stats_layout.addWidget(self.stats_label)
        
        # 详细信息文本框
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self.detail_text)
        
        return group_box
        
    def setup_timer(self):
        """设置定时器"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_alerts)
        self.timer.start(5000)  # 每5秒检查一次
        
    def check_alerts(self):
        """检查告警"""
        if not hasattr(self, 'is_monitoring') or self.is_monitoring:
            self.worker.run_once()
            
    def update_alerts(self, alerts):
        """更新告警列表"""
        current_time = datetime.now().strftime("%H:%M:%S")
        
        for alert in alerts:
            # 添加到历史记录
            alert_data = {
                'time': current_time,
                'code': alert.code,
                'stock_name': alert.stock_name,
                'name': alert.name,
                'description': alert.descr
            }
            self.alerts_history.append(alert_data)
            self.current_alerts.append(alert_data)
            
            # 更新统计
            self.alert_stats[alert.stock_name] += 1
            
            # 添加到表格
            self.add_alert_to_table(alert_data)
            
        # 更新状态
        if alerts:
            self.status_label.setText(f"发现 {len(alerts)} 个新告警")
            self.update_statistics()
        else:
            self.status_label.setText("监控中...")
            
    def add_alert_to_table(self, alert_data):
        """添加告警到表格"""
        row = self.alert_table.rowCount()
        self.alert_table.insertRow(row)
        
        # 解析描述信息获取关键数据
        description = alert_data['description']
        continuous_count = self.extract_value(description, r"连续(\d+)笔")
        amount = self.extract_value(description, r"成交额([\d,]+)万元")
        percentage = self.extract_value(description, r"占流通市值([\d.]+)%")
        
        # 设置表格项
        self.alert_table.setItem(row, 0, QTableWidgetItem(alert_data['time']))
        self.alert_table.setItem(row, 1, QTableWidgetItem(alert_data['code']))
        self.alert_table.setItem(row, 2, QTableWidgetItem(alert_data['stock_name']))
        self.alert_table.setItem(row, 3, QTableWidgetItem("异动"))
        self.alert_table.setItem(row, 4, QTableWidgetItem(str(continuous_count) if continuous_count else "N/A"))
        self.alert_table.setItem(row, 5, QTableWidgetItem(amount if amount else "N/A"))
        self.alert_table.setItem(row, 6, QTableWidgetItem(f"{percentage}%" if percentage else "N/A"))
        
        # 设置行颜色
        for col in range(7):
            item = self.alert_table.item(row, col)
            if item:
                item.setBackground(QColor(255, 240, 240))  # 浅红色背景
        
        # 滚动到最新
        self.alert_table.scrollToBottom()
        
    def extract_value(self, text, pattern):
        """从文本中提取数值"""
        import re
        match = re.search(pattern, text)
        return match.group(1) if match else None
        
    def on_alert_selected(self):
        """告警选择事件"""
        current_row = self.alert_table.currentRow()
        if current_row >= 0 and current_row < len(self.current_alerts):
            alert_data = self.current_alerts[current_row]
            self.show_alert_detail(alert_data)
            
    def show_alert_detail(self, alert_data):
        """显示告警详情"""
        detail_text = f"""
股票代码: {alert_data['code']}
股票名称: {alert_data['stock_name']}
告警时间: {alert_data['time']}
告警类型: {alert_data['name']}
详细描述: {alert_data['description']}

历史告警次数: {self.alert_stats.get(alert_data['stock_name'], 0)}
        """.strip()
        
        self.detail_text.setPlainText(detail_text)
        
    def update_statistics(self):
        """更新统计信息"""
        total_alerts = len(self.alerts_history)
        unique_stocks = len(set([alert['stock_name'] for alert in self.alerts_history]))
        recent_alerts = len([a for a in self.alerts_history 
                           if self.is_recent_alert(a['time'])])
        
        stats_text = f"""
今日告警总数: {total_alerts}
异动股票数量: {unique_stocks}
最近5分钟告警: {recent_alerts}

活跃度Top5:
{self.get_top_stocks(5)}
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
            
    def get_top_stocks(self, top_n=5):
        """获取告警次数最多的股票"""
        sorted_stocks = sorted(self.alert_stats.items(), 
                           key=lambda x: x[1], reverse=True)
        result = []
        for i, (stock, count) in enumerate(sorted_stocks[:top_n]):
            result.append(f"{i+1}. {stock}: {count}次")
        return "\n".join(result)
        
    def clear_history(self):
        """清空历史记录"""
        reply = QMessageBox.question(
            self, '确认', '确定要清空所有历史记录吗？',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.alerts_history.clear()
            self.current_alerts.clear()
            self.alert_stats.clear()
            self.alert_table.setRowCount(0)
            self.detail_text.clear()
            self.update_statistics()
            
    def export_alerts(self):
        """导出告警数据"""
        if not self.alerts_history:
            QMessageBox.information(self, '提示', '没有告警数据可导出')
            return
            
        filename, _ = QFileDialog.getSaveFileName(
            self, '导出告警', f'alerts_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
            'CSV文件 (*.csv)'
        )
        
        if filename:
            try:
                df = pd.DataFrame(self.alerts_history)
                df.to_csv(filename, index=False, encoding='utf-8-sig')
                QMessageBox.information(self, '成功', f'告警数据已导出到:\n{filename}')
            except Exception as e:
                QMessageBox.critical(self, '错误', f'导出失败:\n{str(e)}')
                
    def closeEvent(self, event):
        """关闭事件"""
        self.is_monitoring = False
        self.thread.quit()
        self.thread.wait(3000)
        event.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    # 创建主窗口
    window = AlertMonitorWindow()
    window.show()
    
    # 设置监控状态
    window.is_monitoring = True
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()