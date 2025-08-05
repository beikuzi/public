import subprocess
from typing import Optional
import requests
import socket
import psutil
import sys
import os
import json
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QLineEdit, QPushButton, QMessageBox, QTextEdit, QCheckBox
)
from PyQt5.QtCore import Qt
import signal

import web_func

# 参数配置
CHROME_PARAMS = [
    {
        "desc": "远程调试端口",
        "default_checked": True,
        "default_text": "--remote-debugging-port={port}"
    },
    {
        "desc": "允许远程源",
        "default_checked": True,
        "default_text": "--remote-allow-origins=http://127.0.0.1:{port},http://localhost:{port}"
    },
    {
        "desc": "跳过首次运行",
        "default_checked": True,
        "default_text": "--no-first-run"
    },
    {
        "desc": "跳过默认浏览器检查",
        "default_checked": True,
        "default_text": "--no-default-browser-check"
    },
    {
        "desc": "用户数据目录",
        "default_checked": True,
        "default_text": "--user-data-dir=\"{user_data_dir}\""
    },
    {
        "desc": "Profile目录",
        "default_checked": True,
        "default_text": "--profile-directory=\"{profile_name}\""
    },
    # 你可以随意添加更多参数
]

def get_chrome_profiles():
    user_data_root = r'C:\chrome_debug_profile'
    profiles = []
    if os.path.exists(user_data_root):
        for name in os.listdir(user_data_root):
            path = os.path.join(user_data_root, name)
            if os.path.isdir(path) and (name == 'Default' or name.startswith('Profile')):
                profiles.append((name, path))
    return profiles

def start_chrome_with_remote_debugging(port: int, user_data_dir: Optional[str] = None, profile_directory: Optional[str] = None) -> subprocess.Popen:
    """
    启动 Chrome 并开启远程调试端口。
    :param port: 远程调试端口号
    :param user_data_dir: 可选，指定用户数据目录（应为User Data目录）
    :param profile_directory: 可选，指定profile目录名（如"Profile 1"、"Default"）
    :return: subprocess.Popen 对象
    """
    cmd = [
        'chrome.exe',
        f'--remote-debugging-port={port}',
        '--no-first-run',
        '--no-default-browser-check'
    ]
    if user_data_dir:
        cmd.append(f'--user-data-dir=\"{user_data_dir}\"')
    if profile_directory:
        cmd.append(f'--profile-directory=\"{profile_directory}\"')
    print("启动命令（列表）:", cmd)
    print("启动命令（字符串）:", ' '.join(cmd))
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def get_chrome_tabs(port: int = 9222):
    """
    获取指定端口下Chrome所有标签页信息。
    :param port: 远程调试端口号
    :return: 标签页信息列表
    """
    try:
        resp = requests.get(f'http://127.0.0.1:{port}/json')
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"获取标签页失败: {e}")
        return []

def find_available_port(port: int, min_port: int = 1024, max_port: int = 65535) -> int:
    """
    检查指定端口是否可用，不可用则返回一个可用端口。
    :param port: 首选端口
    :param min_port: 可选，搜索可用端口的起始范围
    :param max_port: 可选，搜索可用端口的结束范围
    :return: 可用端口号
    """
    def is_port_free(p):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", p))
                return True
            except OSError:
                return False
    if is_port_free(port):
        return port
    for p in range(min_port, max_port):
        if is_port_free(p):
            return p
    raise RuntimeError("没有可用端口")

def is_port_used_by_chrome(port: int) -> bool:
    """
    判断指定端口是否被chrome进程监听
    """
    for conn in psutil.net_connections(kind='inet'):
        if conn.status == psutil.CONN_LISTEN and conn.laddr.port == port and conn.pid:
            try:
                pname = psutil.Process(conn.pid).name().lower()
                if 'chrome' in pname:
                    return True
            except Exception:
                continue
    return False

def wait_for_chrome_debug_port(port, timeout=10):
    import time
    url = f'http://127.0.0.1:{port}/json'
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get(url, timeout=1)
            if resp.status_code == 200:
                return True
        except Exception:
            time.sleep(0.5)
    return False

def is_chrome_using_userdata(user_data_dir):
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            if proc.info['name'] and 'chrome' in proc.info['name'].lower():
                cmdline = ' '.join(proc.info['cmdline'])
                if user_data_dir.replace('/', '\\').lower() in cmdline.lower():
                    return True
        except Exception:
            continue
    return False

def kill_process_by_pid(pid: int):
    try:
        os.kill(pid, signal.SIGTERM)
        return True, f"已结束进程ID: {pid}"
    except Exception as e:
        return False, f"结束进程失败: {e}"

class ChromeLauncher(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chrome 远程调试启动器")
        self.setGeometry(300, 300, 700, 500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # 账户资料选择
        h1 = QHBoxLayout()
        h1.addWidget(QLabel("选择账户资料:"))
        self.profile_combo = QComboBox()
        self.profiles = get_chrome_profiles()
        for name, path in self.profiles:
            self.profile_combo.addItem(f"{name} ({path})", path)
        self.profile_combo.currentIndexChanged.connect(self.on_profile_changed)
        h1.addWidget(self.profile_combo)
        layout.addLayout(h1)

        # 账号信息显示和隐私模式复选框
        h_account = QHBoxLayout()
        self.account_label = QLabel("账号信息：")
        h_account.addWidget(self.account_label)
        self.privacy_mode_cb = QCheckBox("隐藏账号信息")
        self.privacy_mode_cb.setChecked(True)  # 默认勾选
        self.privacy_mode_cb.stateChanged.connect(self.update_account_info)
        h_account.addWidget(self.privacy_mode_cb)
        h_account.addStretch()  # 添加弹性空间，使复选框靠右
        layout.addLayout(h_account)
        
        self.on_profile_changed(0)  # 初始化时显示第一个

        # 端口输入
        h2 = QHBoxLayout()
        h2.addWidget(QLabel("远程调试端口:"))
        self.port_edit = QLineEdit("9222")
        h2.addWidget(self.port_edit)
        self.check_port_btn = QPushButton("检测端口占用")
        self.check_port_btn.clicked.connect(self.check_port)
        self.check_port_result = QLabel("")
        h2.addWidget(self.check_port_btn)
        h2.addWidget(self.check_port_result)
        layout.addLayout(h2)

        # 参数复选框
        self.param_widgets = []
        for param in CHROME_PARAMS:
            row = QHBoxLayout()
            cb = QCheckBox(param["desc"])
            cb.setChecked(param.get("default_checked", False))
            le = QLineEdit(param.get("default_text", ""))
            row.addWidget(cb)
            row.addWidget(le)
            self.param_widgets.append((cb, le))
            layout.addLayout(row)


        # 启动按钮
        self.launch_btn = QPushButton("启动 Chrome")
        self.launch_btn.clicked.connect(self.launch_chrome)
        layout.addWidget(self.launch_btn)

        # 命令显示
        self.cmd_label = QLabel("命令：")
        layout.addWidget(self.cmd_label)

        # 结果显示
        self.result_label = QLabel("")
        layout.addWidget(self.result_label)

        # 标签页显示按钮和文本框
        h3 = QHBoxLayout()
        self.tabs_btn = QPushButton("获取当前标签页")
        self.tabs_btn.clicked.connect(self.show_tabs)
        self.show_cmd_btn = QPushButton("仅输出最终指令")
        self.show_cmd_btn.clicked.connect(self.show_final_cmd)
        self.check_all_ports_btn = QPushButton("检测所有chrome监听端口")
        self.check_all_ports_btn.clicked.connect(self.check_all_chrome_ports)
        self.show_ports_btn = QPushButton("输出所有端口及进程名")
        self.show_ports_btn.clicked.connect(self.show_all_ports_info)
        h3.addWidget(self.tabs_btn)
        h3.addWidget(self.show_cmd_btn)
        h3.addWidget(self.check_all_ports_btn)
        h3.addWidget(self.show_ports_btn)
        layout.addLayout(h3)

        self.tabs_text = QTextEdit()
        self.tabs_text.setReadOnly(False)  # 允许复制
        layout.addWidget(self.tabs_text)

        # 添加新的 QLineEdit 用于显示可复制的 9222/json 链接
        self.json_url_label = QLineEdit("http://127.0.0.1:9222/json")
        self.json_url_label.setReadOnly(True)
        layout.addWidget(self.json_url_label)

        # 杀进程和杀端口按钮
        h4 = QHBoxLayout()
        self.kill_port_edit = QLineEdit()
        self.kill_port_edit.setPlaceholderText("输入端口号")
        self.kill_port_btn = QPushButton("杀掉占用端口的进程")
        self.kill_port_btn.clicked.connect(self.kill_port_action)
        h4.addWidget(self.kill_port_edit)
        h4.addWidget(self.kill_port_btn)
        layout.addLayout(h4)

        h5 = QHBoxLayout()
        self.kill_pid_edit = QLineEdit()
        self.kill_pid_edit.setPlaceholderText("输入进程ID")
        self.kill_pid_btn = QPushButton("杀掉指定进程ID")
        self.kill_pid_btn.clicked.connect(self.kill_pid_action)
        h5.addWidget(self.kill_pid_edit)
        h5.addWidget(self.kill_pid_btn)
        layout.addLayout(h5)

        self.setLayout(layout)

    def on_profile_changed(self, idx):
        path = self.profile_combo.currentData()
        self.current_profile_path = path
        self.update_account_info()

    def update_account_info(self):
        if self.privacy_mode_cb.isChecked():
            self.account_label.setText("账号信息：（隐藏模式已启用）")
            return
        
        path = self.current_profile_path
        info = "账号信息："
        if path:
            pref_path = os.path.join(path, "Preferences")
            if os.path.exists(pref_path):
                try:
                    with open(pref_path, "r", encoding="utf-8") as f:
                        prefs = json.load(f)
                    accounts = prefs.get("account_info", [])
                    if accounts:
                        info += "，".join([a.get("email", "") for a in accounts])
                    else:
                        info += "（未检测到账号）"
                except Exception as e:
                    info += f"（读取失败: {e}）"
            else:
                info += "（无 Preferences 文件）"
        self.account_label.setText(info)

    def launch_chrome(self):
        port = self.port_edit.text().strip()
        try:
            port = int(port)
        except ValueError:
            QMessageBox.warning(self, "错误", "端口号必须为整数！")
            return
        profile_path = self.profile_combo.currentData()
        user_data_dir = os.path.dirname(profile_path)
        profile_name = os.path.basename(profile_path)
        cmd = self.build_cmd(port, user_data_dir, profile_name)
        self.cmd_label.setText("命令：" + " ".join(cmd))
        print("实际运行命令：", " ".join(cmd))  # 统一打印
        try:
            cmd_str = " ".join(cmd)
            proc = subprocess.Popen(cmd_str, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if wait_for_chrome_debug_port(port):
                self.result_label.setText(f"Chrome 启动成功，端口: {port}，进程ID: {proc.pid}")
            else:
                self.result_label.setText(f"Chrome 启动失败，端口 {port} 未监听或未就绪")
        except Exception as e:
            self.result_label.setText(f"启动失败: {e}")

    def show_tabs(self):
        port = self.port_edit.text().strip()
        try:
            port = int(port)
        except ValueError:
            self.tabs_text.setPlainText("端口号无效")
            return
        try:
            tabs = get_chrome_tabs(port)
            if not tabs:
                self.tabs_text.setPlainText("未获取到标签页")
            else:
                lines = []
                for tab in tabs:
                    lines.append(f"标题: {tab.get('title')}\nURL: {tab.get('url')}\nID: {tab.get('id')}\n")
                self.tabs_text.setPlainText("\n".join(lines))
        except Exception as e:
            self.tabs_text.setPlainText(f"获取标签页失败: {e}")

    def show_final_cmd(self):
        port = self.port_edit.text().strip()
        try:
            port = int(port)
        except ValueError:
            self.tabs_text.setPlainText("端口号无效")
            return
        profile_path = self.profile_combo.currentData()
        user_data_dir = os.path.dirname(profile_path)
        profile_name = os.path.basename(profile_path)
        cmd = self.build_cmd(port, user_data_dir, profile_name)
        self.tabs_text.setPlainText(" ".join(cmd))

    def build_cmd(self, port, user_data_dir, profile_name):
        cmd = ['chrome.exe']
        context = {
            "port": port,
            "user_data_dir": user_data_dir,
            "profile_name": profile_name
        }
        for cb, le in self.param_widgets:
            if cb.isChecked():
                # 支持任意参数格式和占位符
                arg = le.text().format(**context)
                cmd.append(arg)
        return cmd

    def check_port(self):
        port = self.port_edit.text().strip()
        try:
            port = int(port)
        except ValueError:
            self.check_port_result.setText("端口号无效")
            return
        found = False
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr.port == port:
                info = f"端口: {port}\n状态: {conn.status}\n"
                if conn.pid:
                    try:
                        pname = psutil.Process(conn.pid).name()
                        info += f"进程ID: {conn.pid}\n进程名: {pname}\n"
                    except Exception:
                        info += f"进程ID: {conn.pid}\n进程名: 获取失败\n"
                else:
                    info += "无关联进程\n"
                self.check_port_result.setText(info)
                found = True
                break
        if not found:
            self.check_port_result.setText(f"端口 {port} 未被任何进程监听")

    def check_all_chrome_ports(self):
        chrome_ports = []
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == psutil.CONN_LISTEN and conn.pid:
                try:
                    pname = psutil.Process(conn.pid).name().lower()
                    if 'chrome' in pname:
                        chrome_ports.append(str(conn.laddr.port))
                except Exception:
                    continue
        if chrome_ports:
            self.tabs_text.setPlainText(f"被chrome监听的端口: {', '.join(chrome_ports)}")
        else:
            self.tabs_text.setPlainText("未检测到chrome监听的端口")

    def show_all_ports_info(self):
        ports = web_func.get_ports_info()
        if not ports:
            self.tabs_text.setPlainText("未检测到任何监听端口")
        else:
            lines = []
            for info in ports:
                lines.append(f"端口: {info.port}, 协议: {info.protocol}, 地址: {info.laddr}, 进程ID: {info.pid}, 进程名: {info.process_name}")
            self.tabs_text.setPlainText("\n".join(lines))

    def kill_port_action(self):
        port_text = self.kill_port_edit.text().strip()
        try:
            port = int(port_text)
        except ValueError:
            self.result_label.setText("端口号无效")
            return
        import web_func
        result = web_func.kill_process_on_port(port)
        if result:
            self.result_label.setText(f"已杀掉占用端口 {port} 的进程")
        else:
            self.result_label.setText(f"未找到占用端口 {port} 的进程")

    def kill_pid_action(self):
        pid_text = self.kill_pid_edit.text().strip()
        try:
            pid = int(pid_text)
        except ValueError:
            self.result_label.setText("进程ID无效")
            return
        ok, msg = web_func.kill_process_by_pid(pid)
        self.result_label.setText(msg)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ChromeLauncher()
    win.show()
    sys.exit(app.exec_())
