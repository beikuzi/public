from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QPlainTextEdit
from PyQt5.QtGui import QTextCursor, QTextCharFormat, QColor

class LogViewerDialog(QDialog):
    def __init__(self, parent=None, log_plaintextedit=None):
        super().__init__(parent)
        self.setWindowTitle('详细日志')
        self.resize(900, 600)
        layout = QVBoxLayout(self)

        # 搜索栏
        search_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText('输入要查找的内容')
        self.btn_search_next = QPushButton('查找下一个')
        self.btn_search_prev = QPushButton('查找上一个')
        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(self.btn_search_prev)
        search_layout.addWidget(self.btn_search_next)
        layout.addLayout(search_layout)

        self.detail_log_text = QPlainTextEdit()
        self.detail_log_text.setReadOnly(True)
        layout.addWidget(self.detail_log_text)
        btn_close = QPushButton('关闭')
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

        # 查找功能
        self.last_search_pos = 0
        self.matches = []
        self.current_match_idx = -1

        self.btn_search_next.clicked.connect(self.search_next)
        self.btn_search_prev.clicked.connect(self.search_prev)
        self.search_edit.returnPressed.connect(self.search_next)

        # 新增：持有主日志区引用
        self._main_log_edit = log_plaintextedit
        if self._main_log_edit is not None:
            self._main_log_edit.textChanged.connect(self._sync_from_main_log)

    def _sync_from_main_log(self):
        # 只有在弹窗可见时才同步，避免没必要的刷新
        if self.isVisible():
            self.set_log(self._main_log_edit.toPlainText())

    def set_log(self, text):
        self.detail_log_text.setPlainText(text)
        self.last_search_pos = 0
        self.matches = []
        self.current_match_idx = -1
        self.clear_highlight()

    def search_all(self, keyword):
        """查找所有匹配项，返回起始位置列表"""
        text = self.detail_log_text.toPlainText()
        self.matches = []
        if not keyword:
            return
        pos = 0
        while True:
            pos = text.find(keyword, pos)
            if pos == -1:
                break
            self.matches.append(pos)
            pos += len(keyword)
        self.current_match_idx = -1

    def highlight_match(self, idx):
        """高亮第idx个匹配项"""
        self.clear_highlight()
        if not self.matches or idx < 0 or idx >= len(self.matches):
            return
        pos = self.matches[idx]
        keyword = self.search_edit.text()
        cursor = self.detail_log_text.textCursor()
        cursor.setPosition(pos)
        cursor.setPosition(pos + len(keyword), QTextCursor.KeepAnchor)
        self.detail_log_text.setTextCursor(cursor)
        # 高亮
        fmt = QTextCharFormat()
        fmt.setBackground(QColor('yellow'))
        cursor.mergeCharFormat(fmt)
        self.detail_log_text.setFocus()

    def clear_highlight(self):
        cursor = self.detail_log_text.textCursor()
        cursor.clearSelection()
        self.detail_log_text.setTextCursor(cursor)

    def search_next(self):
        keyword = self.search_edit.text()
        if not keyword:
            return
        if not self.matches or self.search_edit.text() != getattr(self, '_last_keyword', None):
            self.search_all(keyword)
        if not self.matches:
            return
        self._last_keyword = keyword
        self.current_match_idx = (self.current_match_idx + 1) % len(self.matches)
        self.highlight_match(self.current_match_idx)

    def search_prev(self):
        keyword = self.search_edit.text()
        if not keyword:
            return
        if not self.matches or self.search_edit.text() != getattr(self, '_last_keyword', None):
            self.search_all(keyword)
        if not self.matches:
            return
        self._last_keyword = keyword
        self.current_match_idx = (self.current_match_idx - 1) % len(self.matches)
        self.highlight_match(self.current_match_idx)

    def showEvent(self, event):
        # 每次弹出时自动同步主日志区内容
        if self._main_log_edit is not None:
            self.set_log(self._main_log_edit.toPlainText())
        super().showEvent(event)

if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QPlainTextEdit, QLabel
    import sys
    app = QApplication(sys.argv)
    win = QWidget()
    win.setWindowTitle('日志区测试')
    layout = QVBoxLayout(win)
    log_label = QLabel('日志区')
    layout.addWidget(log_label)
    log_output = QPlainTextEdit()
    log_output.setPlainText('这是第一行日志\n第二行日志\n第三行日志\n错误：something wrong\n警告：warning\n测试查找功能\n测试查找功能2')
    layout.addWidget(log_output)
    btn_row = QHBoxLayout()
    btn_detail = QPushButton('详细')
    btn_add_log = QPushButton('添加日志')
    btn_clear_log = QPushButton('清空日志')
    btn_row.addWidget(btn_detail)
    btn_row.addWidget(btn_add_log)
    btn_row.addWidget(btn_clear_log)
    layout.addLayout(btn_row)
    log_viewer = LogViewerDialog(win, log_plaintextedit=log_output)
    def show_detail():
        log_viewer.show()
    btn_detail.clicked.connect(show_detail)
    def add_log():
        log_output.appendPlainText('新日志：测试同步')
    btn_add_log.clicked.connect(add_log)
    def clear_log():
        log_output.clear()
    btn_clear_log.clicked.connect(clear_log)
    win.resize(600, 400)
    win.show()
    sys.exit(app.exec_())
