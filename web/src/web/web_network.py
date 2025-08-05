import json
import time
import functools
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QApplication,
    QTableWidget, QTableWidgetItem, QTabWidget, QSplitter, QHeaderView,
    QComboBox, QLineEdit, QCheckBox, QMessageBox, QMenu, QAction, QToolButton
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt5.QtGui import QIcon, QCursor
import requests
import websocket

# 导入性能监控器
from mod_profiler import PerformanceMonitor

profiler = PerformanceMonitor(output_file="network_monitor_performance.txt", print_interval=10000)

@profiler.profile()
class NetworkMonitor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("网络请求监控")
        self.resize(1000, 800)
        self.requests = []
        self.ws = None
        self.monitoring = False
        self.status_filters = {}  # 初始化状态码过滤字典
        self.type_filters = {}  # 改为空字典，动态添加类型
        self.method_filters = {}  # 添加方法过滤字典
        self.initiator_filters = {}  # 添加发起者过滤字典
        self.MAX_REQUESTS = 1000  # 限制最大请求数量，防止内存占用过大
        self.pending_updates = []  # 存储待更新的请求
        self.update_timer = QTimer()  # 创建定时器用于批量更新
        self.update_timer.timeout.connect(self.process_pending_updates)
        self.update_timer.start(300)  # 每300毫秒批量更新一次
        self.auto_refresh = True  # 添加自动刷新控制变量
        self.pinned_requests = []  # 存储置顶的请求ID
        self.last_selected_rows = []  # 存储上次选中的行
        self.last_selected_request_ids = []  # 存储上次选中的请求ID
        self.visible_requests = []  # 存储当前可见的请求ID，用于优化性能
        
        # 初始化默认方法过滤器
        self.default_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"]
        for method in self.default_methods:
            self.method_filters[method] = True
        
        # 初始化默认类型过滤器，所有类型默认勾选，除了Ping
        self.default_types = ["XHR", "Fetch", "Document", "Stylesheet", "Script", "Image", "Media", "Font", "Ping", "Other"]
        for type_name in self.default_types:
            self.type_filters[type_name] = (type_name != "Ping")  # Ping默认不勾选，其他都勾选
            
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 顶部控制区域
        control_layout = QHBoxLayout()
        
        # 端口设置
        control_layout.addWidget(QLabel("调试端口:"))
        self.port_edit = QLineEdit("9222")
        control_layout.addWidget(self.port_edit)
        
        # 监控按钮
        self.start_btn = QPushButton("开始监控")
        self.start_btn.clicked.connect(self.toggle_monitoring)
        control_layout.addWidget(self.start_btn)
        
        # 清除按钮
        self.clear_btn = QPushButton("清除记录")
        self.clear_btn.clicked.connect(self.clear_requests)
        control_layout.addWidget(self.clear_btn)
        
        # 添加保留置顶复选框
        self.keep_pinned_cb = QCheckBox("保留置顶")
        self.keep_pinned_cb.setChecked(True)  # 默认勾选
        control_layout.addWidget(self.keep_pinned_cb)
        
        # 添加手动刷新按钮
        self.refresh_btn = QPushButton("手动刷新")
        self.refresh_btn.clicked.connect(self.manual_refresh)
        control_layout.addWidget(self.refresh_btn)
        
        # 添加导出功能下拉菜单
        self.export_btn = QToolButton()
        self.export_btn.setText("导出")
        self.export_btn.setPopupMode(QToolButton.InstantPopup)
        
        export_menu = QMenu()
        export_pinned_action = QAction("导出置顶内容", self)
        export_pinned_action.triggered.connect(lambda: self.export_requests("pinned"))
        export_menu.addAction(export_pinned_action)
        
        export_displayed_action = QAction("导出显示内容", self)
        export_displayed_action.triggered.connect(lambda: self.export_requests("displayed"))
        export_menu.addAction(export_displayed_action)
        
        export_all_action = QAction("导出所有内容", self)
        export_all_action.triggered.connect(lambda: self.export_requests("all"))
        export_menu.addAction(export_all_action)
        
        self.export_btn.setMenu(export_menu)
        control_layout.addWidget(self.export_btn)
        
        # 添加自动刷新切换
        self.auto_refresh_cb = QCheckBox("自动刷新")
        self.auto_refresh_cb.setChecked(self.auto_refresh)
        self.auto_refresh_cb.stateChanged.connect(self.toggle_auto_refresh)
        control_layout.addWidget(self.auto_refresh_cb)
        
        self.profiler_cb = QCheckBox("性能监控")
        self.profiler_cb.setChecked(True)
        self.profiler_cb.stateChanged.connect(self.toggle_profiler)
        control_layout.addWidget(self.profiler_cb)
        
        # 最大请求数量设置
        control_layout.addWidget(QLabel("最大请求数:"))
        self.max_requests_edit = QLineEdit(str(self.MAX_REQUESTS))
        self.max_requests_edit.setMaximumWidth(80)
        self.max_requests_edit.editingFinished.connect(self.update_max_requests)
        control_layout.addWidget(self.max_requests_edit)
        
        layout.addLayout(control_layout)
        
        # 添加过滤控制行
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("过滤:"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("输入URL关键词过滤，多个关键词用分号(;)分隔")
        self.filter_edit.textChanged.connect(self.delayed_filter)
        filter_layout.addWidget(self.filter_edit)
        
        layout.addLayout(filter_layout)
        
        # 创建分割器，用于调整上下两部分的比例
        main_splitter = QSplitter(Qt.Vertical)
        
        # 请求表格
        self.requests_table = QTableWidget(0, 8)  # 增加一列用于显示时间
        self.requests_table.setHorizontalHeaderLabels(["方法▼", "状态 ▼", "URL", "类型 ▼", "大小", "时间", "发起者▼", "请求时间"])
        
        # 设置表格列宽可调整
        self.requests_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.requests_table.horizontalHeader().setStretchLastSection(False)
        
        # 设置默认列宽
        self.requests_table.setColumnWidth(0, 80)  # 方法列
        self.requests_table.setColumnWidth(1, 60)  # 状态列
        # URL列默认获得最大宽度
        self.requests_table.setColumnWidth(3, 80)  # 类型列
        self.requests_table.setColumnWidth(4, 60)  # 大小列
        self.requests_table.setColumnWidth(5, 80)  # 时间列
        self.requests_table.setColumnWidth(6, 80)  # 发起者列
        self.requests_table.setColumnWidth(7, 120)  # 请求时间列
        
        # 优化表格性能设置
        self.requests_table.setWordWrap(False)  # 禁用自动换行
        self.requests_table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)  # 像素级滚动
        self.requests_table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)  # 像素级滚动
        self.requests_table.setShowGrid(False)  # 隐藏网格线以提高渲染性能
        self.requests_table.setAlternatingRowColors(True)  # 交替行颜色，提高可读性
        
        # 设置表格不自动换行，允许水平滚动
        self.requests_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 设置URL列的文本显示模式
        self.requests_table.setTextElideMode(Qt.ElideNone)  # 不使用省略号
        
        # 表格显示后调整URL列宽度
        QTimer.singleShot(100, self.adjust_url_column_width)
        
        self.requests_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.requests_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.requests_table.cellClicked.connect(self.show_request_details)
        
        # 监听选择变化，保存多选状态
        self.requests_table.itemSelectionChanged.connect(self.save_selection)
        
        # 设置表格标头右键菜单
        self.setup_header_context_menus()
        
        # 设置表格行右键菜单
        self.requests_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.requests_table.customContextMenuRequested.connect(self.show_table_context_menu)
        
        main_splitter.addWidget(self.requests_table)
        
        # 详情区域
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)
        details_layout.setContentsMargins(0, 0, 0, 0)
        
        self.detail_tabs = QTabWidget()
        
        # Headers标签
        self.headers_text = QTextEdit()
        self.headers_text.setReadOnly(True)
        self.detail_tabs.addTab(self.headers_text, "Headers")
        
        # Request标签
        self.request_text = QTextEdit()
        self.request_text.setReadOnly(True)
        self.detail_tabs.addTab(self.request_text, "Request")
        
        # Response标签
        self.response_text = QTextEdit()
        self.response_text.setReadOnly(True)
        self.detail_tabs.addTab(self.response_text, "Response")
        
        # Cookies标签
        self.cookies_text = QTextEdit()
        self.cookies_text.setReadOnly(True)
        self.detail_tabs.addTab(self.cookies_text, "Cookies")
        
        details_layout.addWidget(self.detail_tabs)
        main_splitter.addWidget(details_widget)
        
        # 设置初始分割比例，让请求表格占更多空间
        main_splitter.setSizes([600, 200])
        
        layout.addWidget(main_splitter)
        
        # 状态栏
        status_layout = QHBoxLayout()
        # 将状态标签改为文本框，使其可复制
        self.status_label = QTextEdit()
        self.status_label.setReadOnly(True)
        self.status_label.setMaximumHeight(30)  # 减小高度
        self.status_label.setText("就绪")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        self.request_count_label = QLabel("请求数: 0")
        status_layout.addWidget(self.request_count_label)
        layout.addLayout(status_layout)
        
        self.setLayout(layout)
    
    def setup_header_context_menus(self):
        """设置表格标头右键菜单"""
        header = self.requests_table.horizontalHeader()
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self.show_header_menu)
        
    def show_header_menu(self, pos):
        """显示标头右键菜单"""
        header = self.requests_table.horizontalHeader()
        logical_index = header.logicalIndexAt(pos)
        
        # 方法列菜单
        if logical_index == 0:  # 方法列
            menu = QMenu(self)
            
            # 添加全选/取消全选选项
            select_all = QAction("全选", self)
            select_all.triggered.connect(lambda: self.toggle_all_methods(True))
            menu.addAction(select_all)
            
            deselect_all = QAction("取消全选", self)
            deselect_all.triggered.connect(lambda: self.toggle_all_methods(False))
            menu.addAction(deselect_all)
            
            menu.addSeparator()
            
            # 动态添加已知的方法
            methods = set(request.get("method", "") for request in self.requests)
            # 确保默认方法总是存在
            for default_method in self.default_methods:
                methods.add(default_method)
                
            methods = sorted(methods)
            for method in methods:
                if method:  # 确保方法不为空
                    action = QAction(method, self)
                    action.setCheckable(True)
                    action.setChecked(self.method_filters.get(method, True))  # 默认全部勾选
                    action.toggled.connect(functools.partial(self.toggle_method_filter, method))
                    menu.addAction(action)
            
            menu.exec_(header.mapToGlobal(pos))
        
        # 状态列菜单
        elif logical_index == 1:  # 状态列
            menu = QMenu(self)
            
            # 添加全选/取消全选选项
            select_all = QAction("全选", self)
            select_all.triggered.connect(lambda: self.toggle_all_status(True))
            menu.addAction(select_all)
            
            deselect_all = QAction("取消全选", self)
            deselect_all.triggered.connect(lambda: self.toggle_all_status(False))
            menu.addAction(deselect_all)
            
            menu.addSeparator()
            
            # 动态添加已知的状态码
            status_codes = sorted(set(str(request.get("status", "")) for request in self.requests))
            # 如果还没有请求或状态码，添加一些常见状态码
            common_status_codes = ["200", "201", "204", "301", "302", "304", "400", "401", "403", "404", "500", "502", "503", "504"]
            if not status_codes:
                status_codes = common_status_codes
            else:
                # 确保常见状态码也在列表中
                for code in common_status_codes:
                    if code not in status_codes:
                        status_codes.append(code)
                status_codes.sort()
                
            for code in status_codes:
                if code:  # 确保状态码不为空
                    action = QAction(code, self)
                    action.setCheckable(True)
                    action.setChecked(self.status_filters.get(code, True))  # 默认全部勾选
                    action.toggled.connect(functools.partial(self.toggle_status_filter, code))
                    menu.addAction(action)
            
            menu.exec_(header.mapToGlobal(pos))
            
        # 类型列菜单
        elif logical_index == 3:  # 类型列
            menu = QMenu(self)
            
            # 添加全选/取消全选选项
            select_all = QAction("全选", self)
            select_all.triggered.connect(lambda: self.toggle_all_types(True))
            menu.addAction(select_all)
            
            deselect_all = QAction("取消全选", self)
            deselect_all.triggered.connect(lambda: self.toggle_all_types(False))
            menu.addAction(deselect_all)
            
            menu.addSeparator()
            
            # 动态添加已知的类型
            types = set(request.get("type", "") for request in self.requests)
            # 确保默认类型总是存在
            for default_type in self.default_types:
                types.add(default_type)
                
            types = sorted(types)
            for type_name in types:
                if type_name:  # 确保类型不为空
                    action = QAction(type_name, self)
                    action.setCheckable(True)
                    action.setChecked(self.type_filters.get(type_name, type_name != "Ping"))
                    action.toggled.connect(functools.partial(self.toggle_type_filter, type_name))
                    menu.addAction(action)
            
            menu.exec_(header.mapToGlobal(pos))
            
        # 发起者列菜单
        elif logical_index == 6:  # 发起者列
            menu = QMenu(self)
            
            # 添加全选/取消全选选项
            select_all = QAction("全选", self)
            select_all.triggered.connect(lambda: self.toggle_all_initiators(True))
            menu.addAction(select_all)
            
            deselect_all = QAction("取消全选", self)
            deselect_all.triggered.connect(lambda: self.toggle_all_initiators(False))
            menu.addAction(deselect_all)
            
            menu.addSeparator()
            
            # 动态添加已知的发起者
            initiators = sorted(set(request.get("initiator", {}).get("type", "") for request in self.requests))
            if not initiators:  # 如果还没有请求，添加一些常见发起者
                initiators = ["parser", "script", "other", ""]
                
            for initiator in initiators:
                if initiator is not None:  # 确保发起者不为None
                    display_name = initiator if initiator else "(空)"
                    action = QAction(display_name, self)
                    action.setCheckable(True)
                    action.setChecked(self.initiator_filters.get(initiator, True))  # 默认全部勾选
                    action.toggled.connect(functools.partial(self.toggle_initiator_filter, initiator))
                    menu.addAction(action)
            
            menu.exec_(header.mapToGlobal(pos))
    
    def toggle_all_methods(self, checked):
        """切换所有方法过滤器"""
        methods = set(request.get("method", "") for request in self.requests)
        # 确保默认方法总是存在
        for default_method in self.default_methods:
            methods.add(default_method)
            
        for method in methods:
            if method:  # 确保方法不为空
                self.method_filters[method] = checked
        self.apply_filter()
        
    def toggle_all_status(self, checked):
        """切换所有状态码过滤器"""
        status_codes = set(str(request.get("status", "")) for request in self.requests)
        if not status_codes:
            status_codes = ["200", "201", "204", "301", "302", "304", "400", "401", "403", "404", "500", "502", "503", "504"]
        
        for code in status_codes:
            if code:  # 确保状态码不为空
                self.status_filters[code] = checked
        self.apply_filter()
    
    def toggle_all_types(self, checked):
        """切换所有类型过滤器"""
        types = set(request.get("type", "") for request in self.requests)
        # 确保默认类型总是存在
        for default_type in self.default_types:
            types.add(default_type)
            
        for type_name in types:
            if type_name:  # 确保类型不为空
                self.type_filters[type_name] = checked
        self.apply_filter()
    
    def toggle_all_initiators(self, checked):
        """切换所有发起者过滤器"""
        initiators = set(request.get("initiator", {}).get("type", "") for request in self.requests)
        if not initiators:
            initiators = ["parser", "script", "other", ""]
        
        for initiator in initiators:
            if initiator is not None:  # 确保发起者不为None
                self.initiator_filters[initiator] = checked
        self.apply_filter()
    
    def toggle_method_filter(self, method, checked=None):
        """切换方法过滤器的状态"""
        # 如果是通过partial调用，checked会是第一个参数，method是预设的
        if checked is None:
            # 这种情况是通过信号直接调用，第一个参数是checked状态
            checked = method
            method = self.sender().text()
        
        self.method_filters[method] = checked
        self.apply_filter()
    
    def toggle_initiator_filter(self, initiator, checked=None):
        """切换发起者过滤器的状态"""
        # 如果是通过partial调用，checked会是第一个参数，initiator是预设的
        if checked is None:
            # 这种情况是通过信号直接调用，第一个参数是checked状态
            checked = initiator
            initiator = self.sender().text()
            if initiator == "(空)":
                initiator = ""
        
        self.initiator_filters[initiator] = checked
        self.apply_filter()
    
    def update_max_requests(self):
        """更新最大请求数量"""
        try:
            new_max = int(self.max_requests_edit.text())
            if new_max > 0:
                self.MAX_REQUESTS = new_max
                # 如果当前请求数超过新的最大值，则裁剪请求列表
                if len(self.requests) > self.MAX_REQUESTS:
                    self.requests = self.requests[-self.MAX_REQUESTS:]
                    self.apply_filter()
        except ValueError:
            # 如果输入不是有效的整数，恢复原值
            self.max_requests_edit.setText(str(self.MAX_REQUESTS))
    
    def toggle_type_filter(self, type_name, checked=None):
        """切换类型过滤器的状态"""
        # 如果是通过partial调用，checked会是第一个参数，type_name是预设的
        if checked is None:
            # 这种情况是通过信号直接调用，第一个参数是checked状态
            checked = type_name
            type_name = self.sender().text()
        
        self.type_filters[type_name] = checked
        self.apply_filter()
    
    def toggle_status_filter(self, status_code, checked=None):
        """切换状态码过滤器的状态"""
        # 如果是通过partial调用，checked会是第一个参数，status_code是预设的
        if checked is None:
            # 这种情况是通过信号直接调用，第一个参数是checked状态
            checked = status_code
            status_code = self.sender().text()
        
        self.status_filters[status_code] = checked
        self.apply_filter()
    
    def delayed_filter(self):
        """延迟过滤，避免频繁更新导致的卡顿"""
        # 使用单次定时器延迟执行过滤
        QTimer.singleShot(300, self.apply_filter)
    
    def toggle_auto_refresh(self, state):
        """切换自动刷新状态"""
        self.auto_refresh = (state == Qt.Checked)
        if self.auto_refresh:
            self.update_timer.start(300)
        else:
            self.update_timer.stop()
    
    def manual_refresh(self):
        """手动刷新请求列表"""
        self.process_pending_updates()
    
    def process_pending_updates(self):
        """处理待更新的请求"""
        if not self.pending_updates:
            return
        
        # 保存当前选中状态
        self.save_selection()
        
        # 批处理更新，一次最多处理100条记录，避免UI卡顿
        batch_size = min(100, len(self.pending_updates))
        batch_updates = self.pending_updates[:batch_size]
        self.pending_updates = self.pending_updates[batch_size:]
            
        # 添加新请求到请求列表
        self.requests.extend(batch_updates)
        
        # 限制请求数量
        if len(self.requests) > self.MAX_REQUESTS:
            self.requests = self.requests[-self.MAX_REQUESTS:]
        
        # 应用过滤器更新表格
        self.apply_filter()
        
        # 如果还有待处理的更新且自动刷新开启，安排下一次更新
        if self.pending_updates and self.auto_refresh:
            QTimer.singleShot(100, self.process_pending_updates)
    
    def toggle_monitoring(self):
        if not self.monitoring:
            self.start_monitoring()
        else:
            self.stop_monitoring()
    
    def start_monitoring(self):
        try:
            port = int(self.port_edit.text())
            self.status_label.setText(f"正在连接到端口 {port}...")
            
            # 获取可用的标签页
            try:
                response = requests.get(f"http://localhost:{port}/json")
                tabs = response.json()
                
                # 找到第一个有websocket URL的标签页
                ws_url = None
                for tab in tabs:
                    if "webSocketDebuggerUrl" in tab:
                        ws_url = tab["webSocketDebuggerUrl"]
                        break
                
                if not ws_url:
                    self.status_label.setText("错误: 未找到可用的调试标签页")
                    return
                
                # 创建监控线程
                self.monitor_thread = NetworkMonitorThread(ws_url)
                self.monitor_thread.request_received.connect(self.add_request)
                self.monitor_thread.connection_status.connect(self.update_status)
                self.monitor_thread.start()
                
                self.monitoring = True
                self.start_btn.setText("停止监控")
                self.status_label.setText(f"已连接到 {ws_url}")
                
            except Exception as e:
                self.status_label.setText(f"连接错误: {str(e)}")
                
        except ValueError:
            self.status_label.setText("错误: 端口号必须是整数")
    
    def stop_monitoring(self):
        if hasattr(self, "monitor_thread"):
            self.monitor_thread.stop()
            self.monitor_thread.wait()
        
        self.monitoring = False
        self.start_btn.setText("开始监控")
        self.status_label.setText("监控已停止")
        
        # 停止自动刷新
        if not self.auto_refresh_cb.isChecked():
            self.update_timer.stop()
        
        # 强制垃圾回收，减少内存占用
        import gc
        gc.collect()
    
    def add_request(self, request_data):
        # 不直接添加到请求列表，而是添加到待更新列表
        self.pending_updates.append(request_data)
    
    def update_status(self, status):
        self.status_label.setText(status)
    
    def show_table_context_menu(self, pos):
        """显示表格右键菜单"""
        menu = QMenu(self)
        
        # 保存当前选中状态
        self.save_selection()
        
        # 检查是否有选中的行
        if self.last_selected_request_ids:
            # 检查选中的请求是否都已置顶
            all_pinned = all(req_id in self.pinned_requests for req_id in self.last_selected_request_ids)
            # 检查选中的请求是否都未置顶
            none_pinned = all(req_id not in self.pinned_requests for req_id in self.last_selected_request_ids)
            
            if all_pinned:
                # 如果全部已置顶，则显示取消置顶选项
                unpin_action = QAction(f"取消置顶 ({len(self.last_selected_request_ids)}项)", self)
                unpin_action.triggered.connect(lambda: self.toggle_pin_selected_requests(False))
                menu.addAction(unpin_action)
            elif none_pinned:
                # 如果全部未置顶，则显示置顶选项
                pin_action = QAction(f"置顶 ({len(self.last_selected_request_ids)}项)", self)
                pin_action.triggered.connect(lambda: self.toggle_pin_selected_requests(True))
                menu.addAction(pin_action)
            else:
                # 如果部分已置顶，则同时显示置顶和取消置顶选项
                pin_action = QAction("置顶选中", self)
                pin_action.triggered.connect(lambda: self.toggle_pin_selected_requests(True))
                menu.addAction(pin_action)
                
                unpin_action = QAction("取消置顶选中", self)
                unpin_action.triggered.connect(lambda: self.toggle_pin_selected_requests(False))
                menu.addAction(unpin_action)
            
            # 添加隐藏类型选项
            hide_types_action = QAction("隐藏此类型", self)
            hide_types_action.triggered.connect(self.hide_selected_types)
            menu.addAction(hide_types_action)
            
            # 添加复制URL选项
            copy_url_action = QAction("复制URL", self)
            copy_url_action.triggered.connect(self.copy_selected_urls)
            menu.addAction(copy_url_action)
            
            # 添加删除选项
            delete_action = QAction(f"删除选中 ({len(self.last_selected_request_ids)}项)", self)
            delete_action.triggered.connect(self.delete_selected_requests)
            menu.addAction(delete_action)
            
            menu.exec_(self.requests_table.mapToGlobal(pos))
    
    def hide_selected_types(self):
        """隐藏选中请求的类型"""
        if not self.last_selected_request_ids:
            return
            
        # 收集选中请求的类型
        types_to_hide = set()
        for row in range(self.requests_table.rowCount()):
            request_data = self.requests_table.item(row, 0).data(Qt.UserRole)
            if request_data and request_data.get("requestId") in self.last_selected_request_ids:
                resource_type = request_data.get("type", "")
                if resource_type:
                    types_to_hide.add(resource_type)
        
        # 将这些类型在过滤器中设置为不可见
        for type_name in types_to_hide:
            self.type_filters[type_name] = False
        
        # 更新表格
        self.apply_filter()
    
    def toggle_pin_selected_requests(self, pin=True):
        """切换选中请求的置顶状态"""
        if not self.last_selected_request_ids:
            return
            
        for request_id in self.last_selected_request_ids:
            if pin and request_id not in self.pinned_requests:
                self.pinned_requests.append(request_id)
            elif not pin and request_id in self.pinned_requests:
                self.pinned_requests.remove(request_id)
        
        # 重新应用过滤器以更新显示
        self.apply_filter()
    
    def copy_selected_urls(self):
        """复制选中行的URL到剪贴板"""
        if not self.last_selected_request_ids:
            return
            
        urls = []
        for row in range(self.requests_table.rowCount()):
            request_data = self.requests_table.item(row, 0).data(Qt.UserRole)
            if request_data and request_data.get("requestId") in self.last_selected_request_ids:
                url = request_data.get("url", "")
                if url:
                    urls.append(url)
        
        if urls:
            clipboard = QApplication.clipboard()
            clipboard.setText("\n".join(urls))
    
    def delete_selected_requests(self):
        """删除选中的请求"""
        # 保存当前选中的请求ID
        self.save_selection()
        
        if not self.last_selected_request_ids:
            return
            
        # 从请求列表中删除选中的请求
        self.requests = [req for req in self.requests if req.get("requestId") not in self.last_selected_request_ids]
        
        # 从置顶列表中删除选中的请求
        for request_id in self.last_selected_request_ids:
            if request_id in self.pinned_requests:
                self.pinned_requests.remove(request_id)
        
        # 清空选中列表
        self.last_selected_rows = []
        self.last_selected_request_ids = []
        
        # 更新表格
        self.apply_filter()
    
    def toggle_pin_request(self, request_id, pin=True):
        """切换请求的置顶状态"""
        if pin and request_id not in self.pinned_requests:
            self.pinned_requests.append(request_id)
        elif not pin and request_id in self.pinned_requests:
            self.pinned_requests.remove(request_id)
        
        # 重新应用过滤器以更新显示
        self.apply_filter()
    
    def copy_url(self, row):
        """复制指定行的URL到剪贴板"""
        if row >= 0:
            url_item = self.requests_table.item(row, 2)
            if url_item:
                clipboard = QApplication.clipboard()
                clipboard.setText(url_item.text())

    def apply_filter(self):
        """应用过滤器并更新表格，优化性能"""
        # 保存当前选中行的信息
        self.save_selection()
        
        # 使用setUpdatesEnabled暂时禁用更新，提高性能
        self.requests_table.setUpdatesEnabled(False)
        # 禁用信号，避免在更新表格时触发选择变化事件
        self.requests_table.blockSignals(True)
        
        # 清空表格
        self.requests_table.setRowCount(0)
        
        # 获取过滤条件
        url_filter = self.filter_edit.text()
        status_filter = ""  # 状态过滤已移除
        
        # 限制每次显示的最大行数，提高性能
        max_display_rows = 500
        displayed_count = 0
        
        # 重置可见请求列表
        self.visible_requests = []
        
        # 先处理置顶的请求
        pinned_count = 0
        for request in self.requests:
            request_id = request.get("requestId")
            if request_id not in self.pinned_requests:
                continue
                
            # 应用过滤条件
            if not self.request_passes_filters(request, url_filter, status_filter):
                continue
            
            # 添加到可见请求列表
            self.visible_requests.append(request)
            
            # 添加到表格
            row = self.requests_table.rowCount()
            self.requests_table.insertRow(row)
            self.populate_table_row(row, request, is_pinned=True)
            pinned_count += 1
            displayed_count += 1
            
            # 限制显示行数
            if displayed_count >= max_display_rows:
                break
        
        # 如果已达到最大显示行数，不再显示非置顶请求
        if displayed_count < max_display_rows:
            # 处理非置顶的请求，新请求在上方
            filtered_count = pinned_count
            
            # 优化：只处理最近的MAX_REQUESTS*2个请求，避免处理太多旧请求
            recent_requests = self.requests[-min(len(self.requests), self.MAX_REQUESTS*2):]
            
            for request in reversed(recent_requests):  # 反转列表，使新请求在上方
                request_id = request.get("requestId")
                if request_id in self.pinned_requests:
                    continue  # 跳过已处理的置顶请求
                    
                # 应用过滤条件
                if not self.request_passes_filters(request, url_filter, status_filter):
                    continue
                
                # 添加到可见请求列表
                self.visible_requests.append(request)
                
                # 添加到表格
                row = self.requests_table.rowCount()
                self.requests_table.insertRow(row)
                self.populate_table_row(row, request, is_pinned=False)
                
                filtered_count += 1
                displayed_count += 1
                
                # 限制显示的行数，避免UI卡顿
                if displayed_count >= max_display_rows:
                    break
        
        # 重新启用信号
        self.requests_table.blockSignals(False)
        
        # 如果之前有选中的行，尝试恢复选中状态
        if self.last_selected_request_ids:
            self.restore_selection()
        
        # 重新启用更新
        self.requests_table.setUpdatesEnabled(True)
        
        # 更新请求计数
        total_requests = len(self.requests) + len(self.pending_updates)
        self.request_count_label.setText(f"请求数: {displayed_count}/{total_requests} (置顶: {pinned_count}, 待处理: {len(self.pending_updates)})")
        
        # 强制垃圾回收，减少内存占用
        import gc
        gc.collect()
    
    def request_passes_filters(self, request, url_filter, status_filter):
        """检查请求是否通过所有过滤条件"""
        # 应用URL过滤
        if url_filter:
            # 支持分号分隔的多个过滤条件（OR关系）
            filter_terms = [term.strip().lower() for term in url_filter.split(";") if term.strip()]
            if filter_terms:
                url = request.get("url", "").lower()
                if not any(term in url for term in filter_terms):
                    return False
        
        # 应用方法菜单过滤
        method = request.get("method", "")
        if method in self.method_filters and not self.method_filters[method]:
            return False
        
        # 应用类型菜单过滤
        resource_type = request.get("type", "")
        # 特殊处理Ping类型，如果没有明确设置为True，则过滤掉
        if resource_type == "Ping" and not self.type_filters.get("Ping", False):
            return False
        # 其他类型正常处理
        elif resource_type in self.type_filters and not self.type_filters[resource_type]:
            return False
        
        # 应用状态过滤
        if status_filter:
            status_codes = [s.strip() for s in status_filter.split(",")]
            request_status = str(request.get("status", ""))
            if not any(request_status == code for code in status_codes):
                return False
        
        # 应用状态码菜单过滤
        request_status = str(request.get("status", ""))
        if request_status in self.status_filters and not self.status_filters[request_status]:
            return False
            
        # 应用发起者菜单过滤
        initiator = request.get("initiator", {}).get("type", "")
        if initiator in self.initiator_filters and not self.initiator_filters[initiator]:
            return False
            
        return True
    
    def populate_table_row(self, row, request, is_pinned=False):
        """填充表格行的数据，优化性能"""
        # 设置表格项，减少创建QTableWidgetItem的次数
        method = request.get("method", "")
        method_item = QTableWidgetItem(method)
        method_item.setTextAlignment(Qt.AlignCenter)  # 居中显示
        self.requests_table.setItem(row, 0, method_item)
        
        status = str(request.get("status", ""))
        status_item = QTableWidgetItem(status)
        status_item.setTextAlignment(Qt.AlignCenter)  # 居中显示
        self.requests_table.setItem(row, 1, status_item)
        
        url = request.get("url", "")
        url_item = QTableWidgetItem(url)
        self.requests_table.setItem(row, 2, url_item)
        
        type_name = request.get("type", "")
        type_item = QTableWidgetItem(type_name)
        type_item.setTextAlignment(Qt.AlignCenter)  # 居中显示
        self.requests_table.setItem(row, 3, type_item)
        
        size = self.format_size(request.get("size", 0))
        size_item = QTableWidgetItem(size)
        size_item.setTextAlignment(Qt.AlignCenter)  # 居中显示
        self.requests_table.setItem(row, 4, size_item)
        
        time_str = f"{request.get('time', 0):.2f} ms"
        time_item = QTableWidgetItem(time_str)
        time_item.setTextAlignment(Qt.AlignCenter)  # 居中显示
        self.requests_table.setItem(row, 5, time_item)
        
        initiator = request.get("initiator", {}).get("type", "")
        initiator_item = QTableWidgetItem(initiator)
        initiator_item.setTextAlignment(Qt.AlignCenter)  # 居中显示
        self.requests_table.setItem(row, 6, initiator_item)
        
        # 添加请求时间列
        timestamp = request.get("timestamp", 0)
        time_str = self.format_timestamp(timestamp)
        timestamp_item = QTableWidgetItem(time_str)
        timestamp_item.setTextAlignment(Qt.AlignCenter)  # 居中显示
        self.requests_table.setItem(row, 7, timestamp_item)
        
        # 设置行的数据 - 只在第一列存储完整数据，减少内存占用
        method_item.setData(Qt.UserRole, request)
        
        # 如果是置顶项，设置背景色
        if is_pinned:
            for col in range(self.requests_table.columnCount()):
                item = self.requests_table.item(row, col)
                if item:
                    item.setBackground(Qt.lightGray)
    
    def format_timestamp(self, timestamp):
        """将时间戳格式化为可读的时间字符串"""
        if timestamp == 0:
            return ""
        
        try:
            # 时间戳是秒级的，需要转换为毫秒级
            timestamp_ms = timestamp
            
            # 转换为datetime对象
            dt = time.localtime(timestamp_ms / 1000)
            
            # 格式化为时:分:秒.毫秒
            ms = int((timestamp_ms % 1000))
            return f"{dt.tm_hour:02d}:{dt.tm_min:02d}:{dt.tm_sec:02d}.{ms:03d}"
        except Exception as e:
            # 如果转换失败，返回原始时间戳
            return f"时间戳: {timestamp}"
    
    def restore_selection(self):
        """恢复之前的选中状态"""
        self.requests_table.clearSelection()  # 先清除当前选择
        
        # 禁用信号，避免恢复选择时触发itemSelectionChanged信号
        self.requests_table.blockSignals(True)
        
        # 获取选择模型
        selection_model = self.requests_table.selectionModel()
        
        # 恢复所有之前选中的行
        for row in range(self.requests_table.rowCount()):
            request_data = self.requests_table.item(row, 0).data(Qt.UserRole)
            if request_data and request_data.get("requestId") in self.last_selected_request_ids:
                # 找到之前选中的请求，恢复选中状态
                # 不使用selectRow，因为它会清除之前的选择
                for col in range(self.requests_table.columnCount()):
                    index = self.requests_table.model().index(row, col)
                    selection_model.select(index, selection_model.Select | selection_model.Rows)
        
        # 重新启用信号
        self.requests_table.blockSignals(False)

    def show_request_details(self, row, column):
        # 保存当前选中行（单击时会触发）
        if row not in self.last_selected_rows:
            self.last_selected_rows.append(row)
        
        # 获取选中行的请求数据
        request_data = self.requests_table.item(row, 0).data(Qt.UserRole)
        if not request_data:
            return
            
        # 保存当前选中的请求ID
        request_id = request_data.get("requestId")
        if request_id and request_id not in self.last_selected_request_ids:
            self.last_selected_request_ids.append(request_id)
        
        # 显示Headers
        headers_text = "General:\n"
        headers_text += f"Request URL: {request_data.get('url', '')}\n"
        headers_text += f"Request Method: {request_data.get('method', '')}\n"
        headers_text += f"Status Code: {request_data.get('status', '')}\n\n"
        
        headers_text += "Request Headers:\n"
        for name, value in request_data.get("request_headers", {}).items():
            headers_text += f"{name}: {value}\n"
        
        headers_text += "\nResponse Headers:\n"
        for name, value in request_data.get("response_headers", {}).items():
            headers_text += f"{name}: {value}\n"
            
        self.headers_text.setPlainText(headers_text)
        
        # 显示Request
        request_body = request_data.get("request_body", "")
        if request_body:
            try:
                # 尝试格式化JSON
                if isinstance(request_body, dict) or (isinstance(request_body, str) and request_body.strip().startswith("{")):
                    if isinstance(request_body, str):
                        request_body = json.loads(request_body)
                    formatted_body = json.dumps(request_body, indent=2, ensure_ascii=False)
                    self.request_text.setPlainText(formatted_body)
                else:
                    self.request_text.setPlainText(str(request_body))
            except:
                self.request_text.setPlainText(str(request_body))
        else:
            self.request_text.setPlainText("无请求体或请求体无法显示")
        
        # 显示Response
        response_body = request_data.get("response_body", "")
        if response_body:
            try:
                # 尝试格式化JSON
                if isinstance(response_body, dict) or (isinstance(response_body, str) and response_body.strip().startswith("{")):
                    if isinstance(response_body, str):
                        response_body = json.loads(response_body)
                    formatted_body = json.dumps(response_body, indent=2, ensure_ascii=False)
                    self.response_text.setPlainText(formatted_body)
                else:
                    self.response_text.setPlainText(str(response_body))
            except:
                self.response_text.setPlainText(str(response_body))
        else:
            self.response_text.setPlainText("无响应体或响应体无法显示")
        
        # 显示Cookies
        cookies_text = "Request Cookies:\n"
        for cookie in request_data.get("request_cookies", []):
            cookies_text += f"{cookie.get('name')}: {cookie.get('value')}\n"
        
        cookies_text += "\nResponse Cookies:\n"
        for cookie in request_data.get("response_cookies", []):
            cookies_text += f"{cookie.get('name')}: {cookie.get('value')}\n"
            
        self.cookies_text.setPlainText(cookies_text)
    
    def clear_requests(self):
        """清除请求记录，根据设置决定是否保留置顶项"""
        keep_pinned = self.keep_pinned_cb.isChecked()
        
        if keep_pinned and self.pinned_requests:
            # 保留置顶项
            pinned_requests_data = []
            for request in self.requests:
                if request.get("requestId") in self.pinned_requests:
                    pinned_requests_data.append(request)
            
            # 只保留置顶项
            self.requests = pinned_requests_data
        else:
            # 清空所有请求
            self.requests = []
            self.pinned_requests = []
            
        # 清空待更新列表
        self.pending_updates = []
        
        # 更新表格
        self.apply_filter()
        
        # 清空详情区域
        self.headers_text.clear()
        self.request_text.clear()
        self.response_text.clear()
        self.cookies_text.clear()
    
    def format_size(self, size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes/1024:.1f} KB"
        else:
            return f"{size_bytes/(1024*1024):.1f} MB"

    def save_selection(self):
        """保存当前选中的所有行"""
        # 如果表格正在更新，不保存选择状态
        if not self.requests_table.updatesEnabled() or self.requests_table.signalsBlocked():
            return
            
        self.last_selected_rows = []
        self.last_selected_request_ids = []
        
        # 获取所有选中的行
        selected_rows = set()
        for index in self.requests_table.selectedIndexes():
            row = index.row()
            if row not in selected_rows:
                selected_rows.add(row)
                self.last_selected_rows.append(row)
                
                # 获取请求ID
                request_data = self.requests_table.item(row, 0).data(Qt.UserRole)
                if request_data:
                    request_id = request_data.get("requestId")
                    if request_id and request_id not in self.last_selected_request_ids:
                        self.last_selected_request_ids.append(request_id)

    def adjust_url_column_width(self):
        """调整URL列宽度，使其获得最大可用空间"""
        # 计算其他列的总宽度
        total_width = self.requests_table.width()
        other_columns_width = 0
        for col in range(self.requests_table.columnCount()):
            if col != 2:  # 排除URL列
                other_columns_width += self.requests_table.columnWidth(col)
        
        # 计算URL列应该获得的宽度
        scrollbar_width = 20  # 估计滚动条宽度
        url_width = total_width - other_columns_width - scrollbar_width
        
        # 设置URL列宽度
        if url_width > 100:  # 确保URL列至少有一定宽度
            self.requests_table.setColumnWidth(2, url_width)
            
    def resizeEvent(self, event):
        """窗口大小改变时调整URL列宽度"""
        super().resizeEvent(event)
        self.adjust_url_column_width()

    def export_requests(self, export_type):
        """导出请求数据到JSON文件"""
        from PyQt5.QtWidgets import QFileDialog
        import json
        import os
        from datetime import datetime
        
        # 获取当前时间作为文件名的一部分
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 根据导出类型确定文件名
        if export_type == "pinned":
            filename = f"pinned_requests_{timestamp}.json"
            title = "导出置顶请求"
            description = "置顶的请求"
        elif export_type == "displayed":
            filename = f"displayed_requests_{timestamp}.json"
            title = "导出显示请求"
            description = "当前显示的请求"
        else:  # all
            filename = f"all_requests_{timestamp}.json"
            title = "导出所有请求"
            description = "所有请求"
        
        # 打开文件保存对话框
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            title,
            filename,
            "JSON Files (*.json)"
        )
        
        if not filepath:  # 用户取消了操作
            return
            
        try:
            # 根据导出类型收集要导出的请求
            requests_to_export = []
            
            if export_type == "pinned":
                # 只导出置顶的请求
                for request in self.requests:
                    if request.get("requestId") in self.pinned_requests:
                        requests_to_export.append(request)
                        
            elif export_type == "displayed":
                # 导出当前表格中显示的请求
                for row in range(self.requests_table.rowCount()):
                    request_data = self.requests_table.item(row, 0).data(Qt.UserRole)
                    if request_data:
                        requests_to_export.append(request_data)
                        
            else:  # all
                # 导出所有请求，包括待处理的
                requests_to_export = self.requests.copy()
                requests_to_export.extend(self.pending_updates)
            
            # 准备导出数据
            export_data = {
                "timestamp": datetime.now().isoformat(),
                "type": description,
                "count": len(requests_to_export),
                "requests": requests_to_export
            }
            
            # 写入文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
                
            # 显示成功消息
            QMessageBox.information(
                self,
                "导出成功",
                f"成功导出 {len(requests_to_export)} 条{description}到文件:\n{os.path.basename(filepath)}"
            )
                
        except Exception as e:
            # 显示错误消息
            QMessageBox.critical(
                self,
                "导出失败",
                f"导出请求时发生错误:\n{str(e)}"
            )

    def toggle_profiler(self, state):
        """切换性能监控器状态"""
        if profiler:
            profiler.enable(state == Qt.Checked)
            if state == Qt.Checked:
                print("性能监控已启用")
            else:
                print("性能监控已禁用")


class NetworkMonitorThread(QThread):
    request_received = pyqtSignal(dict)
    connection_status = pyqtSignal(str)
    
    def __init__(self, ws_url):
        super().__init__()
        self.ws_url = ws_url
        self.running = True
        self.ws = None
        self.request_data = {}
    
    def run(self):
        try:
            # 连接到Chrome DevTools Protocol
            websocket.enableTrace(False)  # 启用跟踪以便调试
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close,
                on_open=self.on_open
            )
            
            self.connection_status.emit("正在连接...")
            
            # 修改：确保run_forever在线程中正确运行
            # 添加ping_timeout和ping_interval参数以保持连接活跃
            # 确保ping_interval > ping_timeout
            # 增加重连选项和超时设置
            self.ws.run_forever(
                ping_timeout=10, 
                ping_interval=20,
                reconnect=5,  # 5秒后自动重连
                sslopt={"cert_reqs": None},  # 忽略SSL证书验证
                # http_proxy_host=None,  # 不使用代理
                suppress_origin=True  # 抑制Origin头，可能有助于解决跨域问题
            )
            
        except Exception as e:
            self.connection_status.emit(f"连接错误: {str(e)}")
    
    def on_open(self, ws):
        self.connection_status.emit("已连接")
        
        # 启用网络事件
        ws.send(json.dumps({
            "id": 1,
            "method": "Network.enable"
        }))
        
        # 设置要捕获的事件
        events = [
            "Network.requestWillBeSent",
            "Network.responseReceived",
            "Network.loadingFinished",
            "Network.loadingFailed",
            "Network.responseReceivedExtraInfo"
        ]
        
        for i, event in enumerate(events):
            ws.send(json.dumps({
                "id": i + 2,
                "method": "Network.enable",
                "params": {
                    "events": [event]
                }
            }))
    
    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            
            if "method" in data:
                method = data["method"]
                params = data.get("params", {})
                
                if method == "Network.requestWillBeSent":
                    request_id = params.get("requestId")
                    request = params.get("request", {})
                    
                    # 使用当前本地时间而不是CDP提供的时间戳
                    timestamp = time.time() * 1000  # 转换为毫秒
                    
                    self.request_data[request_id] = {
                        "requestId": request_id,
                        "url": request.get("url"),
                        "method": request.get("method"),
                        "request_headers": request.get("headers", {}),
                        "request_body": request.get("postData"),
                        "initiator": params.get("initiator", {}),
                        "type": params.get("type", "Other"),
                        "timestamp": timestamp,  # 使用本地时间
                        "request_cookies": self.parse_cookies(request.get("headers", {}).get("Cookie", ""))
                    }
                    
                elif method == "Network.responseReceived":
                    request_id = params.get("requestId")
                    response = params.get("response", {})
                    
                    if request_id in self.request_data:
                        self.request_data[request_id].update({
                            "status": response.get("status"),
                            "response_headers": response.get("headers", {}),
                            "mime_type": response.get("mimeType"),
                            "response_cookies": response.get("cookies", [])
                        })
                        
                        # 获取响应体
                        ws.send(json.dumps({
                            "id": 1000 + hash(request_id) % 10000,  # 生成一个唯一ID
                            "method": "Network.getResponseBody",
                            "params": {
                                "requestId": request_id
                            }
                        }))
                
                elif method == "Network.loadingFinished":
                    request_id = params.get("requestId")
                    
                    if request_id in self.request_data:
                        # 计算请求时间
                        end_time = time.time() * 1000  # 使用当前本地时间作为结束时间
                        start_time = self.request_data[request_id].get("timestamp", end_time)
                        request_time = end_time - start_time
                        
                        self.request_data[request_id]["time"] = request_time
                        self.request_data[request_id]["size"] = params.get("encodedDataLength", 0)
                        
                        # 发送完整的请求数据
                        self.request_received.emit(self.request_data[request_id])
                
                elif method == "Network.loadingFailed":
                    request_id = params.get("requestId")
                    
                    if request_id in self.request_data:
                        self.request_data[request_id]["error"] = params.get("errorText")
                        
                        # 发送失败的请求数据
                        self.request_received.emit(self.request_data[request_id])
            
            # 处理响应体
            elif "id" in data and data.get("id", 0) >= 1000:
                result = data.get("result", {})
                if "body" in result:
                    # 找到对应的请求ID
                    for request_id, req_data in self.request_data.items():
                        if hash(request_id) % 10000 == data.get("id") - 1000:
                            body = result.get("body", "")
                            is_base64 = result.get("base64Encoded", False)
                            
                            if is_base64:
                                req_data["response_body"] = "[Base64 编码的二进制数据]"
                            else:
                                try:
                                    # 尝试解析为JSON
                                    if body.strip().startswith("{") or body.strip().startswith("["):
                                        req_data["response_body"] = json.loads(body)
                                    else:
                                        req_data["response_body"] = body
                                except:
                                    req_data["response_body"] = body
                            break
            
        except Exception as e:
            print(f"处理消息错误: {str(e)}")
    
    def on_error(self, ws, error):
        self.connection_status.emit(f"WebSocket错误: {str(error)}")
    
    def on_close(self, ws, close_status_code, close_msg):
        self.connection_status.emit("连接已关闭")
    
    def stop(self):
        self.running = False
        if self.ws:
            self.ws.close()
    
    def parse_cookies(self, cookie_str):
        if not cookie_str:
            return []
            
        cookies = []
        for cookie in cookie_str.split(";"):
            if "=" in cookie:
                name, value = cookie.split("=", 1)
                cookies.append({
                    "name": name.strip(),
                    "value": value.strip()
                })
        return cookies


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    window = NetworkMonitor()
    window.show()
    sys.exit(app.exec_())
