# 自动生成的import头文件
import sys
_modules_backup = {}
try:
    import src.qt5.qt_style_helper as qt_style_helper
    if 'qt_style_helper' not in _modules_backup:
        _modules_backup['qt_style_helper'] = sys.modules.get('qt_style_helper')
    sys.modules['qt_style_helper'] = qt_style_helper
except Exception as e: print(f"导入 src.qt5.qt_style_helper 失败: {e}")
try:
    import src.qt5.qt_sidebar_layout as qt_sidebar_layout
    if 'qt_sidebar_layout' not in _modules_backup:
        _modules_backup['qt_sidebar_layout'] = sys.modules.get('qt_sidebar_layout')
    sys.modules['qt_sidebar_layout'] = qt_sidebar_layout
except Exception as e: print(f"导入 src.qt5.qt_sidebar_layout 失败: {e}")
try:
    import src.qt5.qt_log_viewer as qt_log_viewer
    if 'qt_log_viewer' not in _modules_backup:
        _modules_backup['qt_log_viewer'] = sys.modules.get('qt_log_viewer')
    sys.modules['qt_log_viewer'] = qt_log_viewer
except Exception as e: print(f"导入 src.qt5.qt_log_viewer 失败: {e}")
try:
    import src.qt5.qt_config_saver as qt_config_saver
    if 'qt_config_saver' not in _modules_backup:
        _modules_backup['qt_config_saver'] = sys.modules.get('qt_config_saver')
    sys.modules['qt_config_saver'] = qt_config_saver
except Exception as e: print(f"导入 src.qt5.qt_config_saver 失败: {e}")

def restore_modules():
    for module_name, original_module in _modules_backup.items():
        if original_module is None:
            if module_name in sys.modules:
                del sys.modules[module_name]
        else:
            sys.modules[module_name] = original_module
    print("已恢复原始sys.modules")
