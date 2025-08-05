# 自动生成的import头文件
import sys
_modules_backup = {}
try:
    import src.utils.error_handler as error_handler
    if 'error_handler' not in _modules_backup:
        _modules_backup['error_handler'] = sys.modules.get('error_handler')
    sys.modules['error_handler'] = error_handler
except Exception as e: print(f"导入 src.utils.error_handler 失败: {e}")
try:
    import src.utils.dict_saver as dict_saver
    if 'dict_saver' not in _modules_backup:
        _modules_backup['dict_saver'] = sys.modules.get('dict_saver')
    sys.modules['dict_saver'] = dict_saver
except Exception as e: print(f"导入 src.utils.dict_saver 失败: {e}")
try:
    import src.utils.ufunc as ufunc
    if 'ufunc' not in _modules_backup:
        _modules_backup['ufunc'] = sys.modules.get('ufunc')
    sys.modules['ufunc'] = ufunc
except Exception as e: print(f"导入 src.utils.ufunc 失败: {e}")

def restore_modules():
    for module_name, original_module in _modules_backup.items():
        if original_module is None:
            if module_name in sys.modules:
                del sys.modules[module_name]
        else:
            sys.modules[module_name] = original_module
    print("已恢复原始sys.modules")
