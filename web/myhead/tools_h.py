# 自动生成的import头文件
import sys
_modules_backup = {}
# @desc: 生成import头文件
try:
    import src.tools.gen_file_headers as gen_file_headers
    if 'gen_file_headers' not in _modules_backup:
        _modules_backup['gen_file_headers'] = sys.modules.get('gen_file_headers')
    sys.modules['gen_file_headers'] = gen_file_headers
except Exception as e: print(f"导入 src.tools.gen_file_headers 失败: {e}")

def restore_modules():
    for module_name, original_module in _modules_backup.items():
        if original_module is None:
            if module_name in sys.modules:
                del sys.modules[module_name]
        else:
            sys.modules[module_name] = original_module
    print("已恢复原始sys.modules")
