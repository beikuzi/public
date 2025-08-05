import os
import sys
from functools import wraps
from typing import Any, Callable, List, Set
import datetime
import traceback

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (QApplication, QLabel, QPlainTextEdit, QPushButton,
                             QVBoxLayout, QWidget)

QSS_ERROR = f'''
    QLabel {{
        background: #ffcccc;
        color: #b20000;
        font-weight: bold;
        border: 1px solid #b20000;
        border-radius: 4px;
        font-family: 'Microsoft YaHei, sans-serif';
        font-size: 12px;
    }}
    QPlainTextEdit {{
        background: #ffcccc;
        color: #b20000;
        font-weight: bold;
        border: 1px solid #b20000;
        border-radius: 4px;
        font-family: 'Microsoft YaHei, sans-serif';
        font-size: 12px;
    }}
'''
class ErrorHandler:
    def __init__(self, qss = QSS_ERROR):
        self.qss = qss
        self.error_qt_output = None
        self.error_log_dir = None

    def set_error_qt_output(self, error_qt_output):
        self.error_qt_output = error_qt_output

    def set_error_log_dir(self, error_log_dir):
        self.error_log_dir = error_log_dir

    def handle_error(self, error_message: str = None) -> Callable:
        """错误处理装饰器"""
        def decorator(func_or_class: Callable) -> Callable:
            if isinstance(func_or_class, type):
                # 如果是类，则装饰所有方法
                for attr_name, attr_value in func_or_class.__dict__.items():
                    if callable(attr_value) and not attr_name.startswith('__'):
                        # 为每个方法创建错误处理
                        setattr(func_or_class, attr_name, self.handle_method_error(attr_value, error_message or f"{attr_name}执行失败"))
                return func_or_class
            else:
                # 如果是函数，则直接装饰
                return self.handle_method_error(func_or_class, error_message or "操作执行失败")
        return decorator
    
    def handle_method_error(self, func: Callable, error_message: str) -> Callable:
        """处理单个方法的错误"""
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                # 直接传递所有参数给原函数
                return func(*args[:func.__code__.co_argcount], **kwargs)
            except Exception as e:
                now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                tb_str = traceback.format_exc()
                # 如果存在error_qt_output，则界面显示错误
                if self.error_qt_output is not None:
                    def show_error(err=e, tb=tb_str):
                        msg = f"[{now}] {error_message}, \n {err}\n{tb}"
                        if isinstance(self.error_qt_output, QLabel):
                            self.error_qt_output.setText(msg)
                            self.error_qt_output.setStyleSheet(self.qss)
                        elif self.error_qt_output.__class__.__name__ == 'QPlainTextEdit':
                            self.error_qt_output.setPlainText(msg)
                            self.error_qt_output.setStyleSheet(self.qss)
                    QTimer.singleShot(0, show_error)

                # 如果存在error_log_dir，则文件追加输出错误
                if self.error_log_dir is not None:
                    with open(self.error_log_dir, 'a', encoding='utf-8') as f:
                        f.write(f"[{now}] {error_message}, \n {e}\n{tb_str}\n")

                # 在终端也做打印输出
                print(f"[{now}] {error_message}, \n {e}\n{tb_str}")

                return None
        return wrapper

def error_handler(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # 在这里可以添加更复杂的日志记录逻辑，比如写入文件
            print(f"An error occurred in function '{func.__name__}': {e}")
            # 根据需要，可以选择性地重新抛出异常，或者返回一个默认值
            # raise e
            return None
    return wrapper

if __name__ == "__main__":
    import sys

    from PyQt5.QtWidgets import (QApplication, QPlainTextEdit, QPushButton,
                                 QVBoxLayout, QWidget)

    error_handler = ErrorHandler()
    print(error_handler.qss)

    @error_handler.handle_error()
    class TestWidget(QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("ErrorHandler 调试窗口")
            self.resize(400, 300)
            layout = QVBoxLayout()
            self.text_edit = QPlainTextEdit()
            self.text_edit.setPlaceholderText("这里会显示错误信息")
            layout.addWidget(self.text_edit)
            # self.__error_qt_output = self.text_edit  # 让error_handler能找到
            self.btn = QPushButton("触发错误")
            self.btn.clicked.connect(self.raise_error)
            layout.addWidget(self.btn)
            self.setLayout(layout)

        def raise_error(self):
            raise ValueError("这是一个测试错误！")

    app = QApplication(sys.argv)
    w = TestWidget()
    error_handler.set_error_qt_output(w.text_edit)
    error_handler.set_error_log_dir(os.path.join(os.getcwd(), 'error_log'))
    w.show()
    sys.exit(app.exec_())
