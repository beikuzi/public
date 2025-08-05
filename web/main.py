import os
import sys
import json
import shutil

from PyQt5.QtWidgets import QApplication

sys.path.append(os.getcwd())
from myhead.qt5_h import *
from myhead.utils_h import *
from myhead.web_h import *

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 定义侧边栏项目
    sidebar_items = [
        {"name": "Chrome启动器", "widget": lambda: web_chrome.ChromeLauncher()},
        {"name": "标签页管理", "widget": lambda: web_tabs.TabsManager()},
        {"name": "Cookie管理", "widget": lambda: web_cookie.CookieManager()},
        {"name": "网络监控", "widget": lambda: web_network.NetworkMonitor()},
    ]
    
    # 创建主窗口
    # main_window = web_chrome.ChromeLauncher()
    main_window = qt_sidebar_layout.SidebarLayout(sidebar_items)
    main_window.setWindowTitle("Chrome调试工具")
    main_window.resize(1000, 700)
    main_window.show()
    
    sys.exit(app.exec_())
