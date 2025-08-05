# 自动生成的import头文件
import sys
_modules_backup = {}

def restore_modules():
    for module_name, original_module in _modules_backup.items():
        if original_module is None:
            if module_name in sys.modules:
                del sys.modules[module_name]
        else:
            sys.modules[module_name] = original_module
    print("已恢复原始sys.modules")
