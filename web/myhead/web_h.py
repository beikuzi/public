# 自动生成的import头文件
import sys
_modules_backup = {}
try:
    import src.web.mod_profiler as mod_profiler
    if 'mod_profiler' not in _modules_backup:
        _modules_backup['mod_profiler'] = sys.modules.get('mod_profiler')
    sys.modules['mod_profiler'] = mod_profiler
except Exception as e: print(f"导入 src.web.mod_profiler 失败: {e}")
try:
    import src.web.web_func as web_func
    if 'web_func' not in _modules_backup:
        _modules_backup['web_func'] = sys.modules.get('web_func')
    sys.modules['web_func'] = web_func
except Exception as e: print(f"导入 src.web.web_func 失败: {e}")
try:
    import src.web.web_tabs as web_tabs
    if 'web_tabs' not in _modules_backup:
        _modules_backup['web_tabs'] = sys.modules.get('web_tabs')
    sys.modules['web_tabs'] = web_tabs
except Exception as e: print(f"导入 src.web.web_tabs 失败: {e}")
try:
    import src.web.web_chrome as web_chrome
    if 'web_chrome' not in _modules_backup:
        _modules_backup['web_chrome'] = sys.modules.get('web_chrome')
    sys.modules['web_chrome'] = web_chrome
except Exception as e: print(f"导入 src.web.web_chrome 失败: {e}")
try:
    import src.web.web_cookie as web_cookie
    if 'web_cookie' not in _modules_backup:
        _modules_backup['web_cookie'] = sys.modules.get('web_cookie')
    sys.modules['web_cookie'] = web_cookie
except Exception as e: print(f"导入 src.web.web_cookie 失败: {e}")
try:
    import src.web.web_network as web_network
    if 'web_network' not in _modules_backup:
        _modules_backup['web_network'] = sys.modules.get('web_network')
    sys.modules['web_network'] = web_network
except Exception as e: print(f"导入 src.web.web_network 失败: {e}")

def restore_modules():
    for module_name, original_module in _modules_backup.items():
        if original_module is None:
            if module_name in sys.modules:
                del sys.modules[module_name]
        else:
            sys.modules[module_name] = original_module
    print("已恢复原始sys.modules")
