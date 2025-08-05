import sys
import os
import subprocess
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt

class DropLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("将可执行文件拖拽到这里")
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("QLabel { border: 2px dashed #aaa; font-size: 18px; min-height: 100px; }")
        self.setAcceptDrops(True)
        self.exe_path = None

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].toLocalFile().lower().endswith('.exe'):
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path.lower().endswith('.exe'):
                self.exe_path = file_path
                self.setText(f"已选择: {file_path}\n正在以禁网方式启动...")
                self.start_exe_with_no_network(file_path)
            else:
                self.setText("请拖入exe文件")

    def start_exe_with_no_network(self, exe_path):
        rule_name = f"block_{os.path.basename(exe_path)}"
        exe_path_win = os.path.abspath(exe_path)
        exe_path_win = os.path.normpath(exe_path_win)
        exe_path_win = f'"{exe_path_win}"'  # 加双引号
        add_rule_cmd = [
            "netsh", "advfirewall", "firewall", "add", "rule",
            f'name={rule_name}',
            "dir=out",
            "action=block",
            f'program={exe_path_win}',
            "enable=yes"
        ]
        try:
            subprocess.run(" ".join(add_rule_cmd), check=True, shell=True)
            subprocess.Popen([exe_path])
            self.setText(f"已以禁网方式启动:\n{exe_path}\n\n关闭程序后可手动移除防火墙规则：\nnetsh advfirewall firewall delete rule name={rule_name}")
        except Exception as e:
            self.setText(f"启动失败: {e}")

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("拖拽启动（禁网）工具")
        layout = QVBoxLayout()
        self.drop_label = DropLabel()
        layout.addWidget(self.drop_label)
        self.setLayout(layout)
        self.resize(500, 200)

    def closeEvent(self, event):
        # 关闭窗口时自动移除防火墙规则
        if self.drop_label.exe_path:
            rule_name = f"block_{os.path.basename(self.drop_label.exe_path)}"
            del_rule_cmd = [
                "netsh", "advfirewall", "firewall", "delete", "rule",
                f'name={rule_name}'
            ]
            subprocess.run(" ".join(del_rule_cmd), shell=True)
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
