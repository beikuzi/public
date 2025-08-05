from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, 
    QListWidgetItem, QCheckBox, QTextEdit, QMessageBox, QLineEdit
)
from PyQt5.QtCore import Qt
import requests
import json

class TabsManager(QWidget):
    def __init__(self, port=9222):
        super().__init__()
        self.port = port
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 端口设置
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("远程调试端口:"))
        self.port_edit = QLineEdit("9222")
        port_layout.addWidget(self.port_edit)
        self.refresh_btn = QPushButton("刷新标签页")
        self.refresh_btn.clicked.connect(self.refresh_tabs)
        port_layout.addWidget(self.refresh_btn)
        layout.addLayout(port_layout)
        
        # 过滤选项
        filter_layout = QHBoxLayout()
        self.hide_extensions_cb = QCheckBox("隐藏扩展页面")
        self.hide_extensions_cb.setChecked(True)
        self.hide_extensions_cb.stateChanged.connect(self.refresh_tabs)
        filter_layout.addWidget(self.hide_extensions_cb)
        
        self.hide_empty_cb = QCheckBox("隐藏空标题页面")
        self.hide_empty_cb.setChecked(True)
        self.hide_empty_cb.stateChanged.connect(self.refresh_tabs)
        filter_layout.addWidget(self.hide_empty_cb)
        
        self.hide_service_cb = QCheckBox("隐藏Service Worker")
        self.hide_service_cb.setChecked(True)
        self.hide_service_cb.stateChanged.connect(self.refresh_tabs)
        filter_layout.addWidget(self.hide_service_cb)
        layout.addLayout(filter_layout)
        
        # 标签页列表
        self.tabs_list = QListWidget()
        self.tabs_list.setAlternatingRowColors(True)
        layout.addWidget(self.tabs_list)
        
        self.setLayout(layout)
        self.refresh_tabs()
        
    def refresh_tabs(self):
        try:
            port = int(self.port_edit.text().strip())
            self.tabs_list.clear()
            tabs = self.get_chrome_tabs(port)
            
            if not tabs:
                self.tabs_list.addItem("未获取到标签页")
                return
                
            for tab in tabs:
                title = tab.get('title', '')
                url = tab.get('url', '')
                tab_id = tab.get('id', '')
                
                # 根据过滤条件决定是否显示
                if self.hide_extensions_cb.isChecked() and url.startswith('chrome-extension://'):
                    continue
                if self.hide_empty_cb.isChecked() and not title.strip():
                    continue
                if self.hide_service_cb.isChecked() and title.startswith('Service Worker'):
                    continue
                    
                item = QListWidgetItem(f"{title} - {url}")
                item.setData(Qt.UserRole, tab)  # 存储完整tab信息
                self.tabs_list.addItem(item)
                
        except Exception as e:
            self.tabs_list.clear()
            self.tabs_list.addItem(f"获取标签页失败: {e}")
    
    def get_chrome_tabs(self, port=9222):
        """获取指定端口下Chrome所有标签页信息"""
        try:
            resp = requests.get(f'http://127.0.0.1:{port}/json')
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"获取标签页失败: {e}")
            return []

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    window = TabsManager()
    window.setWindowTitle("Chrome标签页管理器")
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec_())
