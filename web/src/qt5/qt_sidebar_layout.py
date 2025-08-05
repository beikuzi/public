from PyQt5.QtWidgets import (
    QApplication, QWidget, QSplitter, QListWidget, QStackedWidget, QVBoxLayout, QLabel
)
from PyQt5.QtCore import Qt

class SidebarLayout(QWidget):
    def __init__(self, sidebar_items):
        super().__init__()
        self.sidebar_items = sidebar_items
        self.init_ui()

    def init_ui(self):
        self.sidebar = QListWidget()
        self.stack = QStackedWidget()
        for item in self.sidebar_items:
            self.sidebar.addItem(item["name"])
            # 支持传入widget类或widget实例
            widget = item["widget"]
            if callable(widget):
                widget = widget()
            self.stack.addWidget(widget)
        self.sidebar.setMaximumWidth(150)
        self.sidebar.setMinimumWidth(60)
        self.sidebar.setTextElideMode(Qt.ElideRight)
        self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.sidebar.setCurrentRow(0)
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.sidebar)
        splitter.addWidget(self.stack)
        splitter.setStretchFactor(1, 1)
        splitter.setHandleWidth(10)
        # splitter.setStyleSheet("""
        #     QSplitter::handle {
        #         background: #0078d7;
        #     }
        # """)
        splitter.setSizes([150, 650])
        layout = QVBoxLayout(self)
        layout.addWidget(splitter)
        self.setLayout(layout)

class MainWindow(SidebarLayout):
    def __init__(self, sidebar_items):
        super().__init__(sidebar_items)

if __name__ == "__main__":
    import sys
    import os
    # 示例注册表
    sidebar_items = [
        # {"name": "资源管理器", "widget": lambda: ConfigurableFileExplorer(root_path=os.getcwd())},
        {"name": "搜索", "widget": lambda: QLabel("搜索界面")},
        {"name": "源代码管理", "widget": lambda: QLabel("源代码管理界面")},
        {"name": "运行和调试", "widget": lambda: QLabel("运行和调试界面")},
        {"name": "扩展", "widget": lambda: QLabel("扩展界面")},
        {"name": "非常非常长的标签名测试", "widget": lambda: QLabel("长标签界面")},
    ]
    # 传递sidebar_items参数
    app = QApplication(sys.argv)
    win = MainWindow(sidebar_items)
    win.resize(900, 600)
    win.show()
    sys.exit(app.exec_())
