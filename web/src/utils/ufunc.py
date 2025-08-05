import importlib
import os
import re
import subprocess
import sys




def ensure_packages_installed(packages, pip_index=None):
    """
    确保传入的所有包都已安装。未安装则自动pip install。
    :param packages: 包名列表（如 ['numpy', 'requests']）
    :param pip_index: pip源地址（如 'https://pypi.tuna.tsinghua.edu.cn/simple'），默认None用官方源
    :return: None
    """
    for pkg in packages:
        try:
            importlib.import_module(pkg)
            print(f"已安装: {pkg}")
            return True
        except ImportError:
            print(f"未检测到 {pkg}，尝试自动安装...")
            try:
                cmd = [sys.executable, '-m', 'pip', 'install', pkg]
                if pip_index:
                    cmd += ['-i', pip_index]
                subprocess.check_call(cmd)
                print(f"已成功安装: {pkg}")
                return True
            except Exception as e:
                print(f"自动安装 {pkg} 失败，请手动安装。错误信息: {e}")
                return False

def get_non_conflicting_path(dst_path):
    """
    如果dst_path已存在，则自动编号，返回一个不存在的路径。
    例：a.txt -> a (1).txt, a (2).txt ...
    支持绝对路径和相对路径，按传入路径判断。
    """
    if not os.path.exists(dst_path):
        return dst_path
    base, ext = os.path.splitext(dst_path)
    i = 1
    while True:
        new_path = f"{base} ({i}){ext}"
        if not os.path.exists(new_path):
            return new_path
        i += 1

if __name__ == '__main__':
    # 示例用法
    ensure_packages_installed(['numpy', 'requests'], pip_index='https://pypi.tuna.tsinghua.edu.cn/simple')