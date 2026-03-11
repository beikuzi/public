#!/usr/bin/env python3
"""
SVN 自动更新脚本
当本地仓库版本不高于远程版本时，自动执行 svn update
"""

import json
import subprocess
import sys
import os
import io
from pathlib import Path

# Windows 控制台 UTF-8 输出支持
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


def get_svn_revision(path: str, revision_type: str = "BASE") -> int | None:
    """
    获取 SVN 版本号
    
    Args:
        path: 本地工作副本路径或远程 URL
        revision_type: 版本类型 - "BASE"(本地基础版本), "HEAD"(远程最新版本)
    
    Returns:
        版本号，失败返回 None
    """
    try:
        cmd = ["svn", "info", "--show-item", "revision", "-r", revision_type, path]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
        else:
            print(f"获取 {revision_type} 版本失败: {result.stderr}")
            return None
    except subprocess.TimeoutExpired:
        print(f"获取版本号超时: {path}")
        return None
    except Exception as e:
        print(f"获取版本号异常: {e}")
        return None


def check_local_modifications(path: str) -> bool:
    """检查本地是否有未提交的修改"""
    try:
        result = subprocess.run(
            ["svn", "status", path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30
        )
        if result.returncode == 0:
            # 如果有输出，说明有修改
            return bool(result.stdout.strip())
        return False
    except Exception as e:
        print(f"检查本地修改异常: {e}")
        return False


def svn_update(path: str) -> bool:
    """执行 svn update"""
    try:
        print(f"正在更新: {path}")
        result = subprocess.run(
            ["svn", "update", path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=300
        )
        if result.returncode == 0:
            print(f"更新成功:\n{result.stdout}")
            return True
        else:
            print(f"更新失败: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("更新超时")
        return False
    except Exception as e:
        print(f"更新异常: {e}")
        return False


def process_repo(local_path: str, remote_url: str | None = None) -> bool:
    """
    处理单个仓库的更新逻辑
    
    Args:
        local_path: 本地工作副本路径
        remote_url: 远程仓库 URL（可选，不提供则从本地工作副本获取）
    
    Returns:
        是否成功处理
    """
    print(f"\n{'='*50}")
    print(f"处理仓库: {local_path}")
    print(f"{'='*50}")
    
    # 检查路径是否存在
    if not os.path.exists(local_path):
        print(f"错误: 路径不存在 - {local_path}")
        return False
    
    # 获取本地 BASE 版本
    local_rev = get_svn_revision(local_path, "BASE")
    if local_rev is None:
        print("无法获取本地版本号，可能不是有效的 SVN 工作副本")
        return False
    print(f"本地版本 (BASE): {local_rev}")
    
    # 获取远程 HEAD 版本
    # 如果没有提供远程 URL，使用本地路径查询 HEAD
    target = remote_url if remote_url else local_path
    remote_rev = get_svn_revision(target, "HEAD")
    if remote_rev is None:
        print("无法获取远程版本号")
        return False
    print(f"远程版本 (HEAD): {remote_rev}")
    
    # 检查本地修改
    has_modifications = check_local_modifications(local_path)
    if has_modifications:
        print("警告: 本地有未提交的修改")
    
    # 比较版本
    if local_rev >= remote_rev:
        print(f"本地版本 ({local_rev}) >= 远程版本 ({remote_rev})，无需更新")
        return True
    
    # 本地版本低于远程，执行更新
    print(f"本地版本 ({local_rev}) < 远程版本 ({remote_rev})，开始更新...")
    return svn_update(local_path)


def load_config(config_path: str) -> dict | None:
    """加载配置文件"""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"配置文件不存在: {config_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"配置文件格式错误: {e}")
        return None
    except Exception as e:
        print(f"读取配置文件异常: {e}")
        return None


def create_sample_config(config_path: str):
    """创建示例配置文件"""
    sample_config = {
        "repositories": [
            {
                "local_path": "D:/svn/project1",
                "remote_url": "https://svn.example.com/repo/project1"
            },
            {
                "local_path": "D:/svn/project2",
                "remote_url": ""
            }
        ]
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(sample_config, f, indent=4, ensure_ascii=False)
    print(f"已创建示例配置文件: {config_path}")
    print("请编辑配置文件后重新运行脚本")


def main():
    # 配置文件路径（与脚本同目录）
    script_dir = Path(__file__).parent
    config_path = script_dir / "svn_config.json"
    
    # 如果配置文件不存在，创建示例配置
    if not config_path.exists():
        create_sample_config(str(config_path))
        return 1
    
    # 加载配置
    config = load_config(str(config_path))
    if config is None:
        return 1
    
    repositories = config.get("repositories", [])
    if not repositories:
        print("配置文件中没有仓库配置")
        return 1
    
    # 处理每个仓库
    success_count = 0
    fail_count = 0
    
    for repo in repositories:
        local_path = repo.get("local_path", "")
        remote_url = repo.get("remote_url", "") or None
        
        if not local_path:
            print("警告: 跳过空的 local_path 配置")
            continue
        
        if process_repo(local_path, remote_url):
            success_count += 1
        else:
            fail_count += 1
    
    # 输出统计
    print(f"\n{'='*50}")
    print(f"处理完成: 成功 {success_count}, 失败 {fail_count}")
    print(f"{'='*50}")
    
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
