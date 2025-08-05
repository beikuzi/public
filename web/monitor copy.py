import sys
import os
import psutil
import subprocess
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QHBoxLayout, QHeaderView
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QMetaObject, Q_ARG

class DropLabel(QLabel):
    file_dropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("将可执行文件拖拽到这里")
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("QLabel { border: 2px dashed #aaa; font-size: 18px; min-height: 80px; }")
        self.setAcceptDrops(True)

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
                self.setText(f"已选择: {file_path}")
                self.file_dropped.emit(file_path)
            else:
                self.setText("请拖入exe文件")

class MonitorThread(QThread):
    update_signal = pyqtSignal(list)
    finished_signal = pyqtSignal()

    def __init__(self, exe_path):
        super().__init__()
        self.exe_path = exe_path
        self.proc = None
        self._running = True

    def run(self):
        self.proc = subprocess.Popen([self.exe_path])
        last_pids = set()
        while self._running:
            if self.proc.poll() is not None:
                self.update_signal.emit([])  # 主进程退出时清空表格
                self.finished_signal.emit()
                break
            procs = self.get_process_tree(self.proc.pid)
            current_pids = set(p.pid for p in procs)
            if current_pids != last_pids:
                proc_info = []
                for p in procs:
                    try:
                        proc_info.append((p.pid, p.name(), p.exe()))
                    except Exception:
                        proc_info.append((p.pid, "未知", "未知"))
                self.update_signal.emit(proc_info)
                last_pids = current_pids
            time.sleep(2)

    def get_process_tree(self, root_pid):
        try:
            parent = psutil.Process(root_pid)
        except psutil.NoSuchProcess:
            return []
        children = parent.children(recursive=True)
        return [parent] + children

    def stop(self):
        self._running = False

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("进程树监控器（拖拽启动）")
        self.resize(900, 500)
        layout = QVBoxLayout()

        self.drop_label = DropLabel()
        self.drop_label.file_dropped.connect(self.on_file_dropped)
        layout.addWidget(self.drop_label)

        self.start_btn = QPushButton("启动并监控")
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start_monitor)
        layout.addWidget(self.start_btn)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["PID", "进程名", "路径", "打开文件夹", "结束进程"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)
        # 设置路径列自适应拉伸和最小宽度
        header = self.table.horizontalHeader()
        try:
            header.setSectionResizeMode(2, QHeaderView.Stretch)
        except AttributeError:
            try:
                header.setResizeMode(2, QHeaderView.Stretch)
            except AttributeError:
                pass  # 兼容性处理，若都不可用则跳过
        self.table.setColumnWidth(2, 350)
        self.table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        self.table.setWordWrap(False)

        self.setLayout(layout)
        self.exe_path = None
        self.monitor_thread = None

    def on_file_dropped(self, file_path):
        self.exe_path = file_path
        self.start_btn.setEnabled(True)
        self.table.setRowCount(0)

    def start_monitor(self):
        # 启动前彻底回收旧线程
        if self.monitor_thread and self.monitor_thread.isRunning():
            self.monitor_thread.stop()
            self.monitor_thread.wait()
            self.monitor_thread = None
        if not self.exe_path or not os.path.exists(self.exe_path):
            return
        self.start_btn.setEnabled(False)
        self.monitor_thread = MonitorThread(self.exe_path)
        self.monitor_thread.update_signal.connect(self.update_table)
        self.monitor_thread.finished_signal.connect(self.on_monitor_finished)
        self.monitor_thread.start()

    def update_table(self, proc_info):
        self.table.setRowCount(len(proc_info))
        for row, (pid, name, path) in enumerate(proc_info):
            self.table.setItem(row, 0, QTableWidgetItem(str(pid)))
            self.table.setItem(row, 1, QTableWidgetItem(name))
            # 路径列：自适应宽度+悬停显示完整路径+左对齐
            item = QTableWidgetItem(path)
            item.setToolTip(path)
            item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setItem(row, 2, item)
            # 打开文件夹按钮
            btn_open = QPushButton("打开文件夹")
            btn_open.clicked.connect(lambda _, p=path: self.open_folder(p))
            self.table.setCellWidget(row, 3, btn_open)
            # 结束进程按钮
            btn_kill = QPushButton("结束进程")
            btn_kill.clicked.connect(lambda _, pid=pid: self.kill_process(pid))
            self.table.setCellWidget(row, 4, btn_kill)

    def open_folder(self, path):
        if path and os.path.exists(path):
            folder = os.path.dirname(path)
            if os.path.exists(folder):
                os.startfile(folder)

    def kill_process(self, pid):
        try:
            p = psutil.Process(pid)
            p.terminate()
        except Exception as e:
            print(f"结束进程失败: {e}")

    def on_monitor_finished(self):
        self.start_btn.setEnabled(True)
        self.table.setRowCount(0)  # 清空表格
        self.monitor_thread = None  # 清理引用

    def closeEvent(self, event):
        if self.monitor_thread and self.monitor_thread.isRunning():
            self.monitor_thread.stop()
            self.monitor_thread.wait()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
