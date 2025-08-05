import psutil
import socket
import re
import subprocess
import os
import signal
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class PortInfo:
    port: int
    protocol: str
    pid: Optional[int]
    process_name: Optional[str]
    laddr: str

def get_ports_info() -> List[PortInfo]:
    ports = []
    for conn in psutil.net_connections(kind='inet'):
        if conn.status != psutil.CONN_LISTEN:
            continue
        port = conn.laddr.port
        laddr = f"{conn.laddr.ip}:{conn.laddr.port}"
        protocol = 'tcp' if conn.type == socket.SOCK_STREAM else 'udp'
        pid = conn.pid
        process_name = None
        if pid:
            try:
                process_name = psutil.Process(pid).name()
            except Exception:
                process_name = None
        ports.append(PortInfo(
            port=port,
            protocol=protocol,
            pid=pid,
            process_name=process_name,
            laddr=laddr
        ))
    return ports

def kill_process_on_port(port):
    """
    杀掉占用指定端口的进程（仅支持Windows）。
    返回True表示有进程被杀，False表示未找到。
    """
    try:
        result = subprocess.check_output(f'netstat -ano | findstr :{port}', shell=True, text=True)
        pids = set()
        for line in result.strip().split('\n'):
            parts = re.split(r'\s+', line)
            if len(parts) >= 5:
                pid = parts[-1]
                if pid.isdigit():
                    pids.add(pid)
        for pid in pids:
            subprocess.call(f'taskkill /F /PID {pid}', shell=True)
        return bool(pids)
    except Exception:
        return False

def kill_process_by_pid(pid: int):
    try:
        os.kill(pid, signal.SIGTERM)
        return True, f"已结束进程ID: {pid}"
    except Exception as e:
        return False, f"结束进程失败: {e}"

def print_ports_info():
    ports = get_ports_info()
    for info in ports:
        print(f"端口: {info.port}, 协议: {info.protocol}, 地址: {info.laddr}, 进程ID: {info.pid}, 进程名: {info.process_name}")

if __name__ == "__main__":
    print_ports_info()
