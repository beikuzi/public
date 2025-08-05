from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, 
    QListWidgetItem, QCheckBox, QTextEdit, QMessageBox, QLineEdit
)
from PyQt5.QtCore import Qt
import requests
import json
import websocket

class CookieManager(QWidget):
    def __init__(self, port=9222):
        super().__init__()
        self.port = port
        self.all_cookies = []  # 存储所有cookie的变量
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 端口设置
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("远程调试端口:"))
        self.port_edit = QLineEdit(str(self.port))
        port_layout.addWidget(self.port_edit)
        layout.addLayout(port_layout)
        
        # 操作按钮
        actions_layout = QHBoxLayout()
        self.get_cookies_btn = QPushButton("获取所有Cookie")
        self.get_cookies_btn.clicked.connect(self.get_all_cookies)
        actions_layout.addWidget(self.get_cookies_btn)
        layout.addLayout(actions_layout)
        
        # Cookie筛选选项
        filter_cookie_layout = QHBoxLayout()
        filter_cookie_layout.addWidget(QLabel("筛选域名:"))
        self.domain_filter_edit = QLineEdit()
        self.domain_filter_edit.setPlaceholderText("输入域名关键词 (例如: baidu.com)")
        filter_cookie_layout.addWidget(self.domain_filter_edit)
        self.filter_cookies_btn = QPushButton("筛选Cookie")
        self.filter_cookies_btn.clicked.connect(self.filter_cookies)
        filter_cookie_layout.addWidget(self.filter_cookies_btn)
        layout.addLayout(filter_cookie_layout)
        
        # 关键词搜索
        keyword_search_layout = QHBoxLayout()
        keyword_search_layout.addWidget(QLabel("关键词搜索:"))
        self.keyword_search_edit = QLineEdit()
        self.keyword_search_edit.setPlaceholderText("搜索cookie中的任何字段 (例如: BDUSS)")
        keyword_search_layout.addWidget(self.keyword_search_edit)
        self.search_cookies_btn = QPushButton("搜索")
        self.search_cookies_btn.clicked.connect(self.search_cookies)
        keyword_search_layout.addWidget(self.search_cookies_btn)
        layout.addLayout(keyword_search_layout)
        
        # Cookie显示区域
        self.cookie_text = QTextEdit()
        self.cookie_text.setReadOnly(False)  # 允许复制
        layout.addWidget(self.cookie_text)
        
        self.setLayout(layout)
    
    def get_chrome_tabs(self, port=9222):
        """获取指定端口下Chrome所有标签页信息"""
        try:
            resp = requests.get(f'http://127.0.0.1:{port}/json')
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"获取标签页失败: {e}")
            return []
            
    def get_all_cookies(self):
        """获取所有cookie，不依赖于选中的标签页"""
        try:
            port = int(self.port_edit.text().strip())
            
            # 获取所有标签页
            tabs = self.get_chrome_tabs(port)
            if not tabs:
                QMessageBox.warning(self, "提示", "未获取到标签页")
                return
                
            # 选择第一个标签页来获取cookie（任何标签页都可以获取所有cookie）
            tab = None
            for t in tabs:
                if 'webSocketDebuggerUrl' in t:
                    tab = t
                    break
                    
            if not tab:
                QMessageBox.warning(self, "提示", "未找到可用的标签页")
                return
                
            # 使用websocket获取所有cookie
            ws = websocket.create_connection(tab['webSocketDebuggerUrl'])
            ws.send(json.dumps({"id": 1, "method": "Network.getAllCookies"}))
            result = json.loads(ws.recv())
            self.all_cookies = result.get('result', {}).get('cookies', [])
            ws.close()
            
            # 格式化显示cookie
            cookie_text = json.dumps(self.all_cookies, indent=2)
            message = "获取到 " + str(len(self.all_cookies)) + " 个Cookie。\n"
            message += "如需筛选，请在上方输入域名关键词并点击'筛选Cookie'按钮。\n\n"
            message += cookie_text
            self.cookie_text.setPlainText(message)
                
        except Exception as e:
            self.cookie_text.setPlainText(f"获取Cookie失败: {e}")

    def filter_cookies(self):
        if not self.all_cookies:
            QMessageBox.warning(self, "提示", "请先获取Cookie")
            return
            
        filter_text = self.domain_filter_edit.text().strip().lower()
        if not filter_text:
            # 如果没有输入筛选条件，显示所有cookie
            filtered_cookies = self.all_cookies
            message = (
                f"显示所有 {len(filtered_cookies)} 个Cookie:\n\n"
                f"{json.dumps(filtered_cookies, indent=2)}"
            )
            self.cookie_text.setPlainText(message)
        else:
            # 根据域名筛选cookie
            filtered_cookies = [c for c in self.all_cookies if filter_text in c.get('domain', '').lower()]
            
            if filtered_cookies:
                cookie_text = json.dumps(filtered_cookies, indent=2)
                message = (
                    f"找到 {len(filtered_cookies)} 个包含 '{filter_text}' 的Cookie:\n\n"
                    f"{cookie_text}"
                )
                self.cookie_text.setPlainText(message)
                
                # 同时生成requests可用的cookie字典
                cookie_dict = {cookie['name']: cookie['value'] for cookie in filtered_cookies}
                self.cookie_text.append("\n\n# Requests可用的cookie字典:\n")
                self.cookie_text.append(json.dumps(cookie_dict, indent=2))
            else:
                self.cookie_text.setPlainText(f"未找到包含 '{filter_text}' 的Cookie")

    def search_cookies(self):
        if not self.all_cookies:
            QMessageBox.warning(self, "提示", "请先获取Cookie")
            return
            
        keyword = self.keyword_search_edit.text().strip().lower()
        if not keyword:
            QMessageBox.warning(self, "提示", "请输入搜索关键词")
            return
        
        # 搜索cookie中任何字段包含关键词的项
        matched_cookies = []
        for cookie in self.all_cookies:
            # 将cookie转换为字符串以便搜索
            cookie_str = json.dumps(cookie, ensure_ascii=False).lower()
            if keyword in cookie_str:
                matched_cookies.append(cookie)
        
        if matched_cookies:
            cookie_text = json.dumps(matched_cookies, indent=2)
            message = "找到 " + str(len(matched_cookies)) + " 个包含关键词 '" + keyword + "' 的Cookie:\n\n"
            message += cookie_text
            self.cookie_text.setPlainText(message)
            
            # 同时生成requests可用的cookie字典
            cookie_dict = {cookie['name']: cookie['value'] for cookie in matched_cookies}
            self.cookie_text.append("\n\n# Requests可用的cookie字典:\n")
            self.cookie_text.append(json.dumps(cookie_dict, indent=2))
        else:
            self.cookie_text.setPlainText("未找到包含关键词 '" + keyword + "' 的Cookie")

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    window = CookieManager()
    window.setWindowTitle("Chrome Cookie管理器")
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec_())
