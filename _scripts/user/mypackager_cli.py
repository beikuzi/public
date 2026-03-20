#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Python脚本打包器 - 命令行版本

功能：
    - 命令行操作PyInstaller打包Python脚本
    - 支持单个或批量打包多个Python脚本
    - 自动检测系统中安装的Python解释器
    - 默认不显示控制台窗口
    - 支持从配置文件读取默认设置

使用方法：
    # 打包单个脚本（默认无控制台窗口）
    python .pyscript/mypackager_cli.py script.py
    
    # 打包多个脚本
    python .pyscript/mypackager_cli.py script1.py script2.py script3.py
    
    # 显示控制台窗口
    python .pyscript/mypackager_cli.py script.py --console
    
    # 指定输出目录和应用名称
    python .pyscript/mypackager_cli.py script.py -o dist -n myapp
    
    # 使用目录模式而非单文件
    python .pyscript/mypackager_cli.py script.py --onedir
    
    # 查看帮助
    python .pyscript/mypackager_cli.py --help

配置说明：
    - 配置文件: .config/mypackager.json（与GUI版本共享）
    - 默认输出目录: dist
    - 默认构建目录: .misc/.build/build
    - 默认spec目录: .misc/.build/spec
"""

import sys
import os
import argparse
import subprocess
import json
import glob

# ==================== 配置常量 ====================

CONFIG_FILE = '.config/mypackager.json'

DEFAULT_CONFIG = {
    "build_output_dir": "dist",
    "build_temp_dir": ".misc/.build/build",
    "build_spec_dir": ".misc/.build/spec",
    "default_onefile": True,
    "default_console": False,  # CLI版本默认不显示控制台
    "default_clean": True,
    "extra_data": "",
    "extra_args": "",
    "venv_search_dirs": [
        ".misc/.venv",
        ".misc/venv",
        ".venv",
        "venv",
        "env",
        ".env",
    ],
}

# ==================== 配置常量结束 ====================


def load_config(config_path=None):
    """读取配置文件"""
    if config_path is None:
        config_path = CONFIG_FILE
    
    config = DEFAULT_CONFIG.copy()
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                config.update(file_config)
        except Exception as e:
            print(f"警告: 读取配置文件失败: {e}")
    
    return config


def find_python_interpreter(config):
    """查找合适的Python解释器"""
    # 优先使用当前目录的虚拟环境
    current_dir = os.path.normpath(os.path.abspath(os.getcwd()))
    venv_dirs = config.get('venv_search_dirs', ['.venv', 'venv'])
    
    for venv_dir in venv_dirs:
        venv_python = os.path.join(current_dir, venv_dir, 'Scripts', 'python.exe')
        if os.path.exists(venv_python):
            return venv_python
        # Linux/macOS 路径
        venv_python_unix = os.path.join(current_dir, venv_dir, 'bin', 'python')
        if os.path.exists(venv_python_unix):
            return venv_python_unix
    
    # 使用当前Python解释器
    return sys.executable


def check_pyinstaller(interpreter):
    """检查PyInstaller是否已安装"""
    try:
        result = subprocess.run(
            [interpreter, '-c', 'import PyInstaller; print(PyInstaller.__version__)'],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"PyInstaller 版本: {version}")
            return True
        else:
            return False
    except Exception as e:
        print(f"检查PyInstaller失败: {e}")
        return False


def install_pyinstaller(interpreter):
    """安装PyInstaller"""
    print("正在安装 PyInstaller...")
    try:
        result = subprocess.run(
            [interpreter, '-m', 'pip', 'install', 'pyinstaller'],
            timeout=300
        )
        return result.returncode == 0
    except Exception as e:
        print(f"安装PyInstaller失败: {e}")
        return False


def package_script(script_path, args, config):
    """打包单个脚本"""
    if not os.path.exists(script_path):
        print(f"错误: 脚本文件不存在: {script_path}")
        return False
    
    script_name = os.path.basename(script_path)
    script_basename = os.path.splitext(script_name)[0]
    
    print(f"\n{'='*60}")
    print(f"开始打包: {script_name}")
    print(f"{'='*60}")
    
    # 构建PyInstaller命令参数
    pyinstaller_args = []
    
    # 单文件/目录模式
    if args.onedir:
        pyinstaller_args.append("--onedir")
    else:
        pyinstaller_args.append("--onefile")
    
    # 控制台选项（默认不显示）
    if not args.console:
        pyinstaller_args.append("--noconsole")
    
    # 应用名称
    name = args.name if args.name else script_basename
    pyinstaller_args.append(f"--name={name}")
    
    # 输出目录
    output_dir = args.output if args.output else os.path.join(os.getcwd(), config.get('build_output_dir', 'dist'))
    output_dir = os.path.normpath(os.path.abspath(output_dir))
    pyinstaller_args.append(f"--distpath={output_dir}")
    
    # 构建目录
    build_dir = args.build_dir if args.build_dir else os.path.join(os.getcwd(), config.get('build_temp_dir', '.misc/.build/build'))
    build_dir = os.path.normpath(os.path.abspath(build_dir))
    pyinstaller_args.append(f"--workpath={build_dir}")
    
    # spec文件目录
    spec_dir = args.spec_dir if args.spec_dir else os.path.join(os.getcwd(), config.get('build_spec_dir', '.misc/.build/spec'))
    spec_dir = os.path.normpath(os.path.abspath(spec_dir))
    pyinstaller_args.append(f"--specpath={spec_dir}")
    
    # 清理选项
    if args.clean:
        pyinstaller_args.append("--clean")
    
    # 图标
    if args.icon:
        pyinstaller_args.append(f"--icon={args.icon}")
    
    # 额外数据
    if args.add_data:
        for data in args.add_data:
            pyinstaller_args.append(f"--add-data={data}")
    elif config.get('extra_data'):
        for line in config['extra_data'].strip().split('\n'):
            line = line.strip()
            if line:
                pyinstaller_args.append(line)
    
    # 隐藏导入
    if args.hidden_import:
        for hidden in args.hidden_import:
            pyinstaller_args.append(f"--hidden-import={hidden}")
    
    # 额外参数
    if args.extra_args:
        pyinstaller_args.extend(args.extra_args)
    elif config.get('extra_args'):
        for line in config['extra_args'].strip().split('\n'):
            line = line.strip()
            if line:
                pyinstaller_args.append(line)
    
    # 添加脚本路径
    pyinstaller_args.append(script_path)
    
    # 确保目录存在
    for dir_path in [output_dir, build_dir, spec_dir]:
        try:
            os.makedirs(dir_path, exist_ok=True)
        except OSError as e:
            print(f"警告: 无法创建目录 {dir_path}: {e}")
    
    # 构建完整命令
    interpreter = args.interpreter if args.interpreter else find_python_interpreter(config)
    cmd = [interpreter, '-m', 'PyInstaller'] + pyinstaller_args
    
    print(f"解释器: {interpreter}")
    print(f"输出目录: {output_dir}")
    print(f"命令: {' '.join(cmd)}")
    print()
    
    # 执行打包
    try:
        result = subprocess.run(cmd, timeout=args.timeout if args.timeout else 600)
        
        if result.returncode == 0:
            print(f"\n[OK] {script_name} 打包成功!")
            print(f"     输出位置: {output_dir}")
            return True
        else:
            print(f"\n[FAIL] {script_name} 打包失败!")
            return False
    except subprocess.TimeoutExpired:
        print(f"\n[FAIL] {script_name} 打包超时!")
        return False
    except Exception as e:
        print(f"\n[FAIL] {script_name} 打包出错: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Python脚本打包器 - 命令行版本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s script.py                    # 打包单个脚本（默认无控制台）
  %(prog)s script.py --console          # 打包并显示控制台窗口
  %(prog)s script.py -o dist -n myapp   # 指定输出目录和名称
  %(prog)s *.py                         # 打包当前目录所有Python脚本
  %(prog)s script.py --onedir           # 使用目录模式
  %(prog)s --check                      # 检查PyInstaller是否已安装
  %(prog)s --install                    # 安装PyInstaller
        """
    )
    
    # 位置参数
    parser.add_argument('scripts', nargs='*', help='要打包的Python脚本路径')
    
    # 基本选项
    parser.add_argument('-o', '--output', help='输出目录')
    parser.add_argument('-n', '--name', help='应用名称（仅对单个脚本有效）')
    parser.add_argument('-i', '--interpreter', help='Python解释器路径')
    
    # 打包模式
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('-F', '--onefile', action='store_true', default=True,
                           help='生成单个可执行文件（默认）')
    mode_group.add_argument('-D', '--onedir', action='store_true',
                           help='生成目录形式的可执行程序')
    
    # 控制台选项
    parser.add_argument('-c', '--console', action='store_true',
                       help='显示控制台窗口（默认不显示）')
    parser.add_argument('-w', '--noconsole', action='store_true', default=True,
                       help='不显示控制台窗口（默认）')
    
    # 高级选项
    parser.add_argument('--icon', help='应用图标路径 (.ico)')
    parser.add_argument('--clean', action='store_true', default=True,
                       help='打包前清理（默认启用）')
    parser.add_argument('--no-clean', action='store_true',
                       help='打包前不清理')
    parser.add_argument('--build-dir', help='构建临时文件目录')
    parser.add_argument('--spec-dir', help='spec文件目录')
    
    # 依赖选项
    parser.add_argument('--add-data', action='append',
                       help='添加数据文件 (格式: source;dest)')
    parser.add_argument('--hidden-import', action='append',
                       help='添加隐藏导入')
    parser.add_argument('--extra-args', nargs='*',
                       help='其他PyInstaller参数')
    
    # 工具选项
    parser.add_argument('--check', action='store_true',
                       help='检查PyInstaller是否已安装')
    parser.add_argument('--install', action='store_true',
                       help='安装PyInstaller')
    parser.add_argument('--timeout', type=int, default=600,
                       help='打包超时时间（秒，默认600）')
    parser.add_argument('--config', help='配置文件路径')
    parser.add_argument('-q', '--quiet', action='store_true',
                       help='静默模式，减少输出')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='详细模式，显示更多信息')
    
    args = parser.parse_args()
    
    # 处理clean选项
    if args.no_clean:
        args.clean = False
    
    # 加载配置
    config = load_config(args.config)
    
    # 获取解释器
    interpreter = args.interpreter if args.interpreter else find_python_interpreter(config)
    
    # 检查PyInstaller
    if args.check:
        print(f"使用解释器: {interpreter}")
        if check_pyinstaller(interpreter):
            print("PyInstaller 已安装")
            return 0
        else:
            print("PyInstaller 未安装")
            return 1
    
    # 安装PyInstaller
    if args.install:
        print(f"使用解释器: {interpreter}")
        if install_pyinstaller(interpreter):
            print("PyInstaller 安装成功")
            return 0
        else:
            print("PyInstaller 安装失败")
            return 1
    
    # 检查是否提供了脚本
    if not args.scripts:
        parser.print_help()
        print("\n错误: 请提供要打包的Python脚本")
        return 1
    
    # 展开通配符
    scripts = []
    for pattern in args.scripts:
        if '*' in pattern or '?' in pattern:
            matches = glob.glob(pattern)
            scripts.extend([f for f in matches if f.endswith('.py')])
        else:
            scripts.append(pattern)
    
    if not scripts:
        print("错误: 未找到匹配的Python脚本")
        return 1
    
    # 检查PyInstaller是否已安装
    if not args.quiet:
        print(f"使用解释器: {interpreter}")
    
    if not check_pyinstaller(interpreter):
        print("PyInstaller 未安装，正在安装...")
        if not install_pyinstaller(interpreter):
            print("PyInstaller 安装失败，请手动安装")
            return 1
    
    # 打包脚本
    success_count = 0
    fail_count = 0
    
    for script in scripts:
        if package_script(script, args, config):
            success_count += 1
        else:
            fail_count += 1
    
    # 输出统计
    print(f"\n{'='*60}")
    print(f"打包完成: 成功 {success_count} 个, 失败 {fail_count} 个")
    print(f"{'='*60}")
    
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
