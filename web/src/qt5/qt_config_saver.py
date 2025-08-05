import json
import os
from functools import wraps
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QCheckBox, QLineEdit, QTextEdit, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QColorDialog, QComboBox, QSlider, QDoubleSpinBox, QSpinBox, QGroupBox, QWidget

# 全局注册表
SERIALIZE_MAP = {}
DESERIALIZE_MAP = {}
APPLY_MAP = {}


def register_serializer(cls, serializer, deserializer, applier=None):
    SERIALIZE_MAP[cls] = serializer
    DESERIALIZE_MAP[cls.__name__] = deserializer
    if applier:
        APPLY_MAP[cls.__name__] = applier

# 注册QColor
register_serializer(
    QColor,
    lambda v: {'__type__': 'QColor', 'value': v.name()},
    lambda v: QColor(v['value']),
    lambda obj, val: val  # 直接返回QColor对象
)
# 注册QCheckBox
register_serializer(
    QCheckBox,
    lambda v: {'__type__': 'QCheckBox', 'checked': v.isChecked()},
    lambda v: v['checked'],
    lambda obj, val: obj.setChecked(val)
)
# 注册QLineEdit
register_serializer(
    QLineEdit,
    lambda v: {'__type__': 'QLineEdit', 'text': v.text()},
    lambda v: v['text'],
    lambda obj, val: obj.setText(val)
)
# 注册QTextEdit
register_serializer(
    QTextEdit,
    lambda v: {'__type__': 'QTextEdit', 'text': v.toPlainText()},
    lambda v: v['text'],
    lambda obj, val: obj.setPlainText(val)
)
# 注册QLabel
register_serializer(
    QLabel,
    lambda v: {'__type__': 'QLabel', 'text': v.text()},
    lambda v: v['text'],
    lambda obj, val: obj.setText(val)
)
# 注册QComboBox
register_serializer(
    QComboBox,
    lambda v: {'__type__': 'QComboBox', 'text': v.currentText()},
    lambda v: v['text'],
    lambda obj, val: obj.setCurrentText(val)
)
# 注册QSlider
register_serializer(
    QSlider,
    lambda v: {'__type__': 'QSlider', 'value': v.value()},
    lambda v: v['value'],
    lambda obj, val: obj.setValue(val)
)
# 注册QDoubleSpinBox
register_serializer(
    QDoubleSpinBox,
    lambda v: {'__type__': 'QDoubleSpinBox', 'value': v.value()},
    lambda v: v['value'],
    lambda obj, val: obj.setValue(val)
)
# 注册QSpinBox
register_serializer(
    QSpinBox,
    lambda v: {'__type__': 'QSpinBox', 'value': v.value()},
    lambda v: v['value'],
    lambda obj, val: obj.setValue(val)
)
# 注册QGroupBox（保存勾选状态）
register_serializer(
    QGroupBox,
    lambda v: {'__type__': 'QGroupBox', 'checked': v.isChecked()},
    lambda v: v['checked'],
    lambda obj, val: obj.setChecked(val)
)
# # 注册QWidget窗口大小
# register_serializer(
#     QWidget,
#     lambda v: {'__type__': 'QWidget', 'size': (v.width(), v.height()), 'pos': (v.x(), v.y())},
#     lambda v: (v['size'], v.get('pos', (None, None))),
#     lambda obj, val: (
#         obj.resize(*val[0]) if val[0][0] and val[0][1] else None,
#         obj.move(*val[1]) if val[1][0] is not None and val[1][1] is not None else None
#     )
# )

class QtConfigSaver:
    """
    # 配置保存装饰器
    # interval: 保存间隔，单位为毫秒，默认使用default_interval
    # save_on_close: 是否在关闭时保存配置，默认保存
    # config_prefix: 配置文件前缀，默认使用"autosave_"
    # config_dir: 配置文件保存目录，默认使用当前目录
    # config_id: 配置文件ID，默认使用类名
    """
    def __init__(self, default_interval=10000):
        self.default_interval = default_interval

    
    def config_saver(self, interval=None, save_on_close=True, config_prefix="autosave_", 
                    config_dir=".", config_id=None):
        def decorator(cls):
            orig_init = cls.__init__
            default_interval = self.default_interval
            @wraps(orig_init)
            def __config_saver_init__(self, *args, **kwargs):
                orig_init(self, *args, **kwargs)
                if type(self) is not cls:
                    return  # 只在直接实例化本类时生效，子类实例化时父类装饰器失效
                _config_id = config_id
                if _config_id is None:
                    _config_id = getattr(self, 'config_id', None)
                if _config_id is None:
                    _config_id = cls.__name__
                config_dir_path = os.path.abspath(config_dir)
                if not os.path.exists(config_dir_path):
                    os.makedirs(config_dir_path, exist_ok=True)
                config_file = os.path.join(config_dir_path, f"{config_prefix}{_config_id}_config.json")
                self.__config_saver_config_file__ = config_file
                self.__config_saver_default_config__ = self.__config_saver_collect_config__()
                self.__config_saver_timer__ = QTimer()
                self.__config_saver_timer__.timeout.connect(self.__config_saver_save_config__)
                self.__config_saver_timer__.start(interval or default_interval)
                self.__config_saver_load_config__()
            def __config_saver_collect_config__(self):
                config = {}
                for k, v in self.__dict__.items():
                    if not k.startswith('_'):
                        try:
                            serialized = self.__config_saver_serialize__(v)
                            json.dumps(serialized)
                            config[k] = serialized
                        except Exception:
                            pass  # 不能序列化的变量自动跳过
                # 保存窗口默认大小
                if hasattr(self, 'width') and hasattr(self, 'height'):
                    try:
                        config['__window_size__'] = (self.width(), self.height())
                    except Exception:
                        pass
                return config
            def __config_saver_serialize__(self, v):
                # 优先用类级别的注册表
                serializers = getattr(self, '__config_saver_serializers__', None)
                if serializers:
                    for cls_, val in serializers.items():
                        if isinstance(v, cls_):
                            if isinstance(val, tuple):
                                return val[0](v)  # 三元组的第一个是序列化器
                            else:
                                return val(v)
                # 再用全局
                for cls_, func in SERIALIZE_MAP.items():
                    if isinstance(v, cls_):
                        return func(v)
                return v
            def __config_saver_deserialize__(self, k, v):
                # 优先用类级别的注册表
                deserializers = None
                serializers = getattr(self, '__config_saver_serializers__', None)
                if serializers:
                    deserializers = {}
                    for cls, val in serializers.items():
                        if isinstance(val, tuple):
                            deserializers[cls.__name__] = val[1]  # 三元组的第二个是反序列化器
                        else:
                            deserializers[cls.__name__] = val
                if isinstance(v, dict) and '__type__' in v:
                    type_name = v['__type__']
                    if deserializers and type_name in deserializers:
                        return deserializers[type_name](v)
                    if type_name in DESERIALIZE_MAP:
                        return DESERIALIZE_MAP[type_name](v)
                return v
            def __config_saver_save_config__(self):
                config = self.__config_saver_collect_config__()
                # 自动保存窗口size（仅限有width/height/resize方法的类）
                if hasattr(self, 'width') and hasattr(self, 'height'):
                    try:
                        config['__window_size__'] = (self.width(), self.height())
                    except Exception:
                        pass
                with open(self.__config_saver_config_file__, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
            def __config_saver_load_config__(self):
                if not os.path.exists(self.__config_saver_config_file__):
                    return
                try:
                    with open(self.__config_saver_config_file__, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    # 自动恢复窗口size（仅限有resize方法的类）
                    if '__window_size__' in config and hasattr(self, 'resize'):
                        try:
                            w, h = config['__window_size__']
                            self.resize(w, h)
                        except Exception:
                            pass
                    for k, v in config.items():
                        if k == '__window_size__':
                            continue
                        try:
                            self.__config_saver_apply_deserialized__(k, v)
                        except Exception:
                            pass
                except Exception:
                    pass
            def __config_saver_restore_default__(self):
                for k, v in self.__config_saver_default_config__.items():
                    if k == '__window_size__' and hasattr(self, 'resize'):
                        try:
                            w, h = v
                            self.resize(w, h)
                        except Exception:
                            pass
                        continue
                    self.__config_saver_apply_deserialized__(k, v)
            def __config_saver_apply_deserialized__(self, k, v):
                obj = getattr(self, k, None)
                deserialized = self.__config_saver_deserialize__(k, v)
                # 类型检查
                if isinstance(v, dict) and '__type__' in v:
                    config_type = v['__type__']
                    actual_type = type(obj).__name__
                    if config_type != actual_type:
                        return  # 类型不一致，跳过
                # 优先用类级别的applier
                appliers = None
                serializers = getattr(self, '__config_saver_serializers__', None)
                if serializers:
                    appliers = {}
                    for cls, val in serializers.items():
                        if isinstance(val, tuple) and len(val) > 2:
                            appliers[cls.__name__] = val[2]  # 三元组的第三个是applier
                type_name = type(obj).__name__
                if appliers and type_name in appliers:
                    try:
                        result = appliers[type_name](obj, deserialized)
                        if result is not None and not hasattr(obj, 'setParent'):
                            setattr(self, k, result)
                    except Exception:
                        pass
                elif type_name in APPLY_MAP:
                    try:
                        result = APPLY_MAP[type_name](obj, deserialized)
                        if result is not None and not hasattr(obj, 'setParent'):
                            setattr(self, k, result)
                    except Exception:
                        pass
                else:
                    try:
                        setattr(self, k, deserialized)
                    except Exception:
                        pass
            cls.__init__ = __config_saver_init__
            cls.__config_saver_save_config__ = __config_saver_save_config__
            cls.__config_saver_load_config__ = __config_saver_load_config__
            cls.__config_saver_restore_default__ = __config_saver_restore_default__
            cls.__config_saver_collect_config__ = __config_saver_collect_config__
            cls.__config_saver_serialize__ = __config_saver_serialize__
            cls.__config_saver_deserialize__ = __config_saver_deserialize__
            cls.__config_saver_apply_deserialized__ = __config_saver_apply_deserialized__
            # 自动保存功能
            if save_on_close:
                orig_close = getattr(cls, "closeEvent", None)
                def __config_saver_closeEvent__(self, event):
                    if hasattr(self, "__config_saver_save_config__") and hasattr(self, "__config_saver_config_file__"):
                        try:
                            self.__config_saver_save_config__()
                        except Exception:
                            pass
                    if orig_close:
                        orig_close(self, event)
                    else:
                        event.accept()
                cls.closeEvent = __config_saver_closeEvent__
            return cls
        return decorator

if __name__ == "__main__":
    from PyQt5.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QPushButton, QLineEdit, QLabel, QHBoxLayout
    )
    import sys
    app = QApplication(sys.argv)

    class WindowSizeTest(QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("窗口大小保存测试")
            self.resize(500, 400)  # 默认大小
            layout = QVBoxLayout()
            self.info_label = QLabel()
            self.update_info()
            btn_row = QHBoxLayout()
            btn_save = QPushButton("保存配置")
            btn_load = QPushButton("加载配置")
            btn_default = QPushButton("恢复默认")
            btn_show_size = QPushButton("显示当前窗口大小")
            btn_save.clicked.connect(self.__config_saver_save_config__)
            btn_load.clicked.connect(self.__config_saver_load_config__)
            btn_default.clicked.connect(self.__config_saver_restore_default__)
            btn_show_size.clicked.connect(self.update_info)
            btn_row.addWidget(btn_save)
            btn_row.addWidget(btn_load)
            btn_row.addWidget(btn_default)
            btn_row.addWidget(btn_show_size)
            layout.addWidget(self.info_label)
            layout.addLayout(btn_row)
            self.setLayout(layout)
        def update_info(self):
            self.info_label.setText(f"当前窗口大小: {self.width()} x {self.height()}")

    # 用装饰器包装
    @QtConfigSaver().config_saver()
    class WindowSizeTestWithConfig(WindowSizeTest):
        pass

    # 非Qt类测试
    @QtConfigSaver().config_saver()
    class PureDataClass:
        def __init__(self):
            self.value = 123
            self.name = "hello"
            self.flag = True

    class MainTestWindow(QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("窗口大小/非Qt类保存测试主窗口")
            layout = QVBoxLayout()
            self.btn_show_test = QPushButton("显示窗口大小测试窗口")
            self.btn_show_data = QPushButton("显示非Qt类测试结果")
            layout.addWidget(self.btn_show_test)
            layout.addWidget(self.btn_show_data)
            self.setLayout(layout)
            self.test_win = WindowSizeTestWithConfig()
            self.data_obj = PureDataClass()
            self.btn_show_test.clicked.connect(self.show_test)
            self.btn_show_data.clicked.connect(self.show_data)
        def show_test(self):
            self.test_win.show()
        def show_data(self):
            # 修改变量，保存，重置，加载，显示
            self.data_obj.value = 456
            self.data_obj.name = "world"
            self.data_obj.flag = False
            self.data_obj.__config_saver_save_config__()
            # 恢复默认
            self.data_obj.value = 999
            self.data_obj.name = "reset"
            self.data_obj.flag = True
            self.data_obj.__config_saver_restore_default__()
            msg = f"PureDataClass\nvalue: {self.data_obj.value}\nname: {self.data_obj.name}\nflag: {self.data_obj.flag}"
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(self, "非Qt类测试", msg)

    main_win = MainTestWindow()
    main_win.show()
    sys.exit(app.exec_())

