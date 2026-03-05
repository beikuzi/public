"""
监控所有 cmd.exe / powershell.exe / conhost.exe 等控制台进程的创建，
记录谁拉起了它们、命令行参数、时间戳等信息。

用法:
    以管理员权限运行（否则部分系统进程信息无法读取）:
        python monitor_cmd.py

日志输出到同目录下的 cmd_monitor.log，同时在终端实时打印。
按 Ctrl+C 停止监控。

依赖: pip install psutil wmi
"""

import os
import sys
import time
import logging
import datetime
import ctypes
from collections import defaultdict

try:
    import psutil
except ImportError:
    print("请先安装 psutil: pip install psutil")
    sys.exit(1)

try:
    import wmi
except ImportError:
    print("请先安装 wmi: pip install wmi")
    sys.exit(1)

MONITOR_NAMES = {
    "cmd.exe",
    "powershell.exe",
    "pwsh.exe",
    "conhost.exe",
    "wscript.exe",
    "cscript.exe",
    "mshta.exe",
}

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cmd_monitor.log")

logger = logging.getLogger("CmdMonitor")
logger.setLevel(logging.INFO)

fmt = logging.Formatter(
    "[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
fh.setFormatter(fmt)
logger.addHandler(fh)

ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(fmt)
logger.addHandler(ch)


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def get_process_info(pid: int) -> dict | None:
    """安全地获取进程详细信息，进程可能随时消失。"""
    try:
        p = psutil.Process(pid)
        info = p.as_dict(attrs=[
            "pid", "name", "exe", "cmdline", "username",
            "create_time", "ppid", "status",
        ])
        info["cmdline_str"] = " ".join(info.get("cmdline") or [])
        ct = info.get("create_time")
        if ct:
            info["create_time_str"] = datetime.datetime.fromtimestamp(ct).strftime(
                "%Y-%m-%d %H:%M:%S.%f"
            )[:-3]
        return info
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return None


def format_process(info: dict, label: str = "") -> str:
    prefix = f"  [{label}] " if label else "  "
    lines = [
        f"{prefix}PID: {info.get('pid')}",
        f"{prefix}名称: {info.get('name')}",
        f"{prefix}路径: {info.get('exe', '无法获取')}",
        f"{prefix}命令行: {info.get('cmdline_str', '无法获取')}",
        f"{prefix}用户: {info.get('username', '无法获取')}",
        f"{prefix}创建时间: {info.get('create_time_str', '未知')}",
    ]
    return "\n".join(lines)


def get_ancestor_chain(pid: int, max_depth: int = 5) -> list[dict]:
    """向上追溯进程链，最多 max_depth 层。"""
    chain = []
    current_pid = pid
    for _ in range(max_depth):
        info = get_process_info(current_pid)
        if not info:
            break
        chain.append(info)
        ppid = info.get("ppid")
        if not ppid or ppid == current_pid or ppid == 0:
            break
        current_pid = ppid
    return chain


def monitor_with_wmi():
    """使用 WMI 事件订阅来监控进程创建，能捕获瞬间消失的进程。"""
    logger.info("=" * 60)
    logger.info("CMD 窗口监控已启动 (WMI 模式)")
    logger.info(f"管理员权限: {'是' if is_admin() else '否 (建议以管理员运行)'}")
    logger.info(f"监控目标进程: {', '.join(sorted(MONITOR_NAMES))}")
    logger.info(f"日志文件: {LOG_FILE}")
    logger.info("按 Ctrl+C 停止监控...")
    logger.info("=" * 60)

    c = wmi.WMI()

    watcher = c.Win32_Process.watch_for("creation")

    counter = 0
    while True:
        try:
            new_proc = watcher(timeout_ms=500)
        except wmi.x_wmi_timed_out:
            continue

        proc_name = (new_proc.Name or "").lower()
        if proc_name not in MONITOR_NAMES:
            continue

        counter += 1
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        pid = int(new_proc.ProcessId)
        ppid = int(new_proc.ParentProcessId) if new_proc.ParentProcessId else None

        logger.info("")
        logger.info(f"{'=' * 60}")
        logger.info(f"*** 检测到第 {counter} 个控制台进程 ***")
        logger.info(f"时间: {now}")
        logger.info(f"----- 新进程 -----")
        logger.info(f"  PID: {pid}")
        logger.info(f"  名称: {new_proc.Name}")
        logger.info(f"  命令行: {new_proc.CommandLine or '无法获取'}")
        logger.info(f"  路径: {new_proc.ExecutablePath or '无法获取'}")

        if ppid:
            logger.info(f"----- 父进程链 (谁拉起的) -----")
            chain = get_ancestor_chain(ppid)
            if chain:
                for i, ancestor in enumerate(chain):
                    depth_label = "直接父进程" if i == 0 else f"第{i+1}层祖先"
                    logger.info(format_process(ancestor, depth_label))
            else:
                logger.info(f"  父进程 PID={ppid} 已退出，无法获取信息")
        logger.info(f"{'=' * 60}")


def monitor_with_polling():
    """轮询模式作为后备方案，当 WMI 不可用时使用。"""
    logger.info("=" * 60)
    logger.info("CMD 窗口监控已启动 (轮询模式)")
    logger.info(f"管理员权限: {'是' if is_admin() else '否 (建议以管理员运行)'}")
    logger.info(f"监控目标进程: {', '.join(sorted(MONITOR_NAMES))}")
    logger.info(f"日志文件: {LOG_FILE}")
    logger.info("按 Ctrl+C 停止监控...")
    logger.info("=" * 60)

    known_pids: dict[int, float] = {}
    counter = 0
    POLL_INTERVAL = 0.3

    while True:
        current_pids = set()
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                name = (proc.info["name"] or "").lower()
                pid = proc.info["pid"]
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

            if name not in MONITOR_NAMES:
                continue

            current_pids.add(pid)

            if pid in known_pids:
                continue

            known_pids[pid] = time.time()
            counter += 1

            info = get_process_info(pid)
            if not info:
                continue

            logger.info("")
            logger.info(f"{'=' * 60}")
            logger.info(f"*** 检测到第 {counter} 个控制台进程 ***")
            logger.info(f"----- 新进程 -----")
            logger.info(format_process(info, "目标"))

            ppid = info.get("ppid")
            if ppid:
                logger.info(f"----- 父进程链 (谁拉起的) -----")
                chain = get_ancestor_chain(ppid)
                if chain:
                    for i, ancestor in enumerate(chain):
                        depth_label = "直接父进程" if i == 0 else f"第{i+1}层祖先"
                        logger.info(format_process(ancestor, depth_label))
                else:
                    logger.info(f"  父进程 PID={ppid} 已退出，无法获取信息")
            logger.info(f"{'=' * 60}")

        expired = [pid for pid in known_pids if pid not in current_pids]
        for pid in expired:
            del known_pids[pid]

        time.sleep(POLL_INTERVAL)


def main():
    if not is_admin():
        logger.warning("⚠ 当前不是管理员权限，部分进程信息可能无法获取。")
        logger.warning("  建议: 右键 -> 以管理员身份运行此脚本。")
        logger.info("")

    try:
        monitor_with_wmi()
    except ImportError:
        logger.warning("WMI 模块不可用，回退到轮询模式 (可能漏掉一闪而过的进程)")
        monitor_with_polling()
    except Exception as e:
        logger.warning(f"WMI 模式异常 ({e})，回退到轮询模式")
        monitor_with_polling()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n监控已停止。")
        sys.exit(0)
