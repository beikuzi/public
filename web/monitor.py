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
            print("正在执行run")
            if self.proc.poll() is not None:
                self.update_signal.emit([])  # 主进程退出时清空表格
                self.finished_signal.emit()
                break
            procs = self.get_process_tree(self.proc.pid)
            # 只保留真实存在的进程
            filtered_procs = []
            for p in procs:
                try:
                    if psutil.pid_exists(p.pid):
                        filtered_procs.append(p)
                except Exception:
                    pass
            print(filtered_procs)
            current_pids = set(p.pid for p in filtered_procs)
            if current_pids != last_pids:
                proc_info = []
                for p in filtered_procs:
                    try:
                        proc_info.append((p.pid, p.name(), p.exe()))
                    except Exception:
                        proc_info.append((p.pid, "未知", "未知"))
                self.update_signal.emit(proc_info)
                last_pids = current_pids
            time.sleep(2)
        # 如果存在的进程数量为0，则stop
        if len(filtered_procs) == 0:
            self.stop()
        # 线程退出前确保进程已结束
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
            except Exception:
                pass

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

        self.refresh_btn = QPushButton("手动刷新")
        self.refresh_btn.clicked.connect(self.manual_refresh)
        layout.addWidget(self.refresh_btn)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["PID", "进程名", "路径", "CPU(%)", "内存(MB)", "打开文件夹", "结束进程"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)
        # 总网络占用和进程数统计
        self.stats_label = QLabel()
        layout.addWidget(self.stats_label)
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
        self.proc_obj_map = {}  # 缓存psutil.Process对象

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
        # 先过滤掉已不存在的进程
        filtered_info = []
        for pid, name, path in proc_info:
            if psutil.pid_exists(pid):
                filtered_info.append((pid, name, path))
        if not filtered_info:
            self.table.setRowCount(0)
            # 统计信息清空
            self.stats_label.setText("")
            # 清理缓存
            self.proc_obj_map.clear()
            return
        self.table.setRowCount(len(filtered_info))
        # 统计总网络占用和进程数（注意：此为全局总流量，不是进程级）
        try:
            net = psutil.net_io_counters()
            net_str = f"总网络: 收{net.bytes_recv/1024/1024:.2f}MB 发{net.bytes_sent/1024/1024:.2f}MB"
        except Exception:
            net_str = "总网络: 获取失败"
        proc_count = len(filtered_info)
        self.stats_label.setText(f"当前监控进程数: {proc_count}  {net_str}")
        for row, (pid, name, path) in enumerate(filtered_info):
            self.table.setItem(row, 0, QTableWidgetItem(str(pid)))
            self.table.setItem(row, 1, QTableWidgetItem(name))
            item = QTableWidgetItem(path)
            item.setToolTip(path)
            # item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setItem(row, 2, item)
            # CPU/内存
            try:
                if pid not in self.proc_obj_map:
                    self.proc_obj_map[pid] = psutil.Process(pid)
                    cpu = self.proc_obj_map[pid].cpu_percent(interval=0.1)  # 首次采样
                else:
                    cpu = self.proc_obj_map[pid].cpu_percent(interval=0)    # 后续采样
                mem = self.proc_obj_map[pid].memory_info().rss / 1024 / 1024
            except Exception:
                cpu = 0
                mem = 0
            self.table.setItem(row, 3, QTableWidgetItem(f"{cpu:.1f}"))
            self.table.setItem(row, 4, QTableWidgetItem(f"{mem:.1f}"))
            btn_open = QPushButton("打开文件夹")
            btn_open.clicked.connect(lambda _, p=path: self.open_folder(p))
            self.table.setCellWidget(row, 5, btn_open)
            btn_kill = QPushButton("结束进程")
            btn_kill.clicked.connect(lambda _, pid=pid: self.kill_process(pid))
            self.table.setCellWidget(row, 6, btn_kill)
        # 清理已消失进程的缓存
        current_pids = set(pid for pid, _, _ in filtered_info)
        for pid in list(self.proc_obj_map.keys()):
            if pid not in current_pids:
                self.proc_obj_map.pop(pid)

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

    def manual_refresh(self):
        # 直接用当前表格内容的pid做一次psutil.pid_exists检测
        row_count = self.table.rowCount()
        proc_info = []
        for row in range(row_count):
            pid_item = self.table.item(row, 0)
            name_item = self.table.item(row, 1)
            path_item = self.table.item(row, 2)
            if pid_item and name_item and path_item:
                try:
                    pid = int(pid_item.text())
                except Exception:
                    continue
                name = name_item.text()
                path = path_item.text()
                proc_info.append((pid, name, path))
        self.update_table(proc_info)
        if self.table.rowCount() == 0:
            self.start_btn.setEnabled(True)

    def closeEvent(self, event):
        if self.monitor_thread and self.monitor_thread.isRunning():
            self.monitor_thread.stop()
            self.monitor_thread.wait()
            self.monitor_thread = None
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
