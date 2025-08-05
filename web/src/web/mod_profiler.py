import time
import functools
import inspect
import os
from collections import defaultdict
from typing import Dict, List, Callable, Any, Optional
import datetime
import threading

try:
    from PyQt5.QtCore import QTimer, QCoreApplication
    HAS_QT = True
except ImportError:
    HAS_QT = False


class PerformanceMonitor:
    """性能监控类，用于追踪和记录方法执行时间"""
    
    def __init__(self, output_file: str = None, print_interval: int = None):
        # 存储每个方法的执行时间
        self._time_records: Dict[str, float] = defaultdict(float)
        # 存储方法调用计数
        self._call_counts: Dict[str, int] = defaultdict(int)
        # 存储调用栈信息
        self._call_stack: List[Dict] = []
        # 是否启用装饰器
        self._enabled: bool = True
        # 输出文件路径
        self.output_file = output_file
        # 定时器对象
        self._timer = None
        # 线程定时器对象
        self._thread_timer = None
        # 是否停止线程定时器
        self._stop_thread_timer = False
        # 上次打印时间
        self._last_print_time = 0
        # 打印间隔（秒）
        self._print_interval_sec = None
        
        # 如果指定了打印间隔，设置定时器
        if print_interval is not None:
            self._setup_timer(print_interval)
    
    def _setup_timer(self, interval: int):
        """
        设置定时器，定期打印性能统计
        
        Args:
            interval: 打印间隔，单位为毫秒
        """
        # 停止现有的定时器
        self._stop_existing_timers()
        
        # 保存打印间隔（秒）
        self._print_interval_sec = interval / 1000
        
        # 优先使用Qt定时器（如果在Qt事件循环中）
        if HAS_QT and QCoreApplication.instance() is not None:
            self._timer = QTimer()
            self._timer.timeout.connect(self._timed_print_stats)
            self._timer.setInterval(interval)
            self._timer.start()
            print(f"[{self._get_timestamp()}] 已设置Qt性能统计定时打印，间隔: {interval}毫秒")
        else:
            # 使用线程定时器作为备选
            self._stop_thread_timer = False
            self._thread_timer = threading.Thread(target=self._thread_timer_func, args=(interval/1000,))
            self._thread_timer.daemon = True  # 设置为守护线程，这样主程序退出时线程会自动结束
            self._thread_timer.start()
            print(f"[{self._get_timestamp()}] 已设置线程性能统计定时打印，间隔: {interval}毫秒")
    
    def _thread_timer_func(self, interval: float):
        """
        线程定时器函数
        
        Args:
            interval: 打印间隔，单位为秒
        """
        while not self._stop_thread_timer:
            time.sleep(interval)
            if not self._stop_thread_timer:
                self._timed_print_stats()
    
    def _timed_print_stats(self):
        """定时器触发的性能统计打印函数，包含时间戳检查"""
        now = time.time()
        # 检查是否距离上次打印已经过了足够的时间
        if self._last_print_time == 0 or (now - self._last_print_time >= self._print_interval_sec * 0.9):
            self._last_print_time = now
            self.print_stats()
    
    def _get_timestamp(self):
        """获取当前时间戳和格式化的日期时间"""
        now = datetime.datetime.now()
        timestamp = time.time()
        return f"{now.strftime('%Y-%m-%d %H:%M:%S')}.{now.microsecond//1000:03d} ({timestamp:.3f})"
    
    def _stop_existing_timers(self):
        """停止所有现有的定时器"""
        # 停止Qt定时器
        if self._timer is not None:
            try:
                self._timer.stop()
                self._timer = None
            except:
                pass
        
        # 停止线程定时器
        if self._thread_timer is not None:
            self._stop_thread_timer = True
            try:
                self._thread_timer.join(0.1)  # 等待线程结束，最多等待0.1秒
            except:
                pass
            self._thread_timer = None
        
    def set_print_interval(self, interval: int = None):
        """
        设置或更新定时打印间隔
        
        Args:
            interval: 打印间隔，单位为毫秒，None表示停止定时打印
        """
        # 停止现有的定时器
        self._stop_existing_timers()
        
        # 重置上次打印时间
        self._last_print_time = 0
        
        # 如果指定了新的间隔，创建新的定时器
        if interval is not None:
            self._setup_timer(interval)
        else:
            self._print_interval_sec = None
            print(f"[{self._get_timestamp()}] 已停止性能统计定时打印")
        
    def profile(self, error_message: str = None) -> Callable:
        """
        性能监控装饰器，可以应用于类或方法
        
        Args:
            error_message: 可选的错误消息
            
        Returns:
            装饰后的类或方法
        """
        def decorator(func_or_class: Callable) -> Callable:
            if isinstance(func_or_class, type):
                # 如果是类，则装饰所有方法
                for attr_name, attr_value in func_or_class.__dict__.items():
                    if callable(attr_value) and not attr_name.startswith('__'):
                        # 为每个方法创建性能监控
                        setattr(func_or_class, attr_name, 
                                self._monitor_method(attr_value))
                return func_or_class
            else:
                # 如果是函数，则直接装饰
                return self._monitor_method(func_or_class)
        return decorator
    
    def _monitor_method(self, func: Callable) -> Callable:
        """
        监控单个方法的性能
        
        Args:
            func: 要监控的方法
            
        Returns:
            装饰后的方法
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if not self._enabled:
                return func(*args[:func.__code__.co_argcount], **kwargs)
            
            # 获取方法的全名
            if inspect.ismethod(func):
                # 如果是类实例方法
                method_name = f"{func.__self__.__class__.__name__}.{func.__name__}"
            else:
                # 如果是函数或类方法
                if len(args) > 0 and hasattr(args[0], "__class__"):
                    method_name = f"{args[0].__class__.__name__}.{func.__name__}"
                else:
                    method_name = func.__name__
            
            # 创建栈帧记录
            stack_frame = {
                'name': method_name,
                'start_time': time.time(),
                'total_time': 0,
                'children': []
            }
            
            # 添加到调用栈
            parent_frame = None
            if self._call_stack:
                parent_frame = self._call_stack[-1]
                parent_frame['children'].append(stack_frame)
                
            self._call_stack.append(stack_frame)
            
            start_time = time.time()
            try:
                # 执行原始方法
                return func(*args[:func.__code__.co_argcount], **kwargs)
                return result
            finally:
                end_time = time.time()
                elapsed_time = end_time - start_time
                
                # 更新时间记录
                self._time_records[method_name] += elapsed_time
                self._call_counts[method_name] += 1
                
                # 更新栈帧信息
                stack_frame['total_time'] = elapsed_time
                self._call_stack.pop()
                
        return wrapper
    
    def print_stats(self) -> None:
        """打印方法执行时间的统计信息"""
        if not self._time_records:
            print(f"[{self._get_timestamp()}] No performance data collected yet.")
            return
        
        # 计算总执行时间
        total_time = sum(self._time_records.values())
        
        # 对方法按执行时间降序排序
        sorted_methods = sorted(
            self._time_records.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        timestamp = self._get_timestamp()
        print(f"\n===== Performance Statistics [{timestamp}] =====")
        print(f"{'Method':<40} {'Time (s)':<10} {'Calls':<10} {'Avg Time (s)':<15} {'Percentage':<10}")
        print("-" * 85)
        
        for method_name, elapsed_time in sorted_methods:
            call_count = self._call_counts[method_name]
            avg_time = elapsed_time / call_count
            percentage = (elapsed_time / total_time * 100) if total_time > 0 else 0
            
            print(f"{method_name:<40} {elapsed_time:.6f}  {call_count:<10} {avg_time:.6f}      {percentage:.2f}%")
        
        print("-" * 85)
        print(f"{'Total':<40} {total_time:.6f}")
        print("================================\n")
        
        # 如果设置了输出文件，也写入文件
        if self.output_file:
            self.export_stats(self.output_file)
    
    def export_stats(self, file_path: str) -> None:
        """
        将性能统计信息导出到文件
        
        Args:
            file_path: 输出文件路径
        """
        if not self._time_records:
            return
            
        # 确保目录存在
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            
        # 计算总执行时间
        total_time = sum(self._time_records.values())
        
        # 对方法按执行时间降序排序
        sorted_methods = sorted(
            self._time_records.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        with open(file_path, 'w') as f:
            timestamp = self._get_timestamp()
            f.write(f"Performance Statistics - {timestamp}\n")
            f.write("=" * 80 + "\n")
            f.write(f"{'Method':<40} {'Time (s)':<10} {'Calls':<10} {'Avg Time (s)':<15} {'Percentage':<10}\n")
            f.write("-" * 80 + "\n")
            
            for method_name, elapsed_time in sorted_methods:
                call_count = self._call_counts[method_name]
                avg_time = elapsed_time / call_count
                percentage = (elapsed_time / total_time * 100) if total_time > 0 else 0
                
                f.write(f"{method_name:<40} {elapsed_time:.6f}  {call_count:<10} {avg_time:.6f}      {percentage:.2f}%\n")
            
            f.write("-" * 80 + "\n")
            f.write(f"{'Total':<40} {total_time:.6f}\n\n")
            
            # 导出调用树
            f.write("Call Tree Hierarchy\n")
            f.write("=" * 80 + "\n")
            
            # 创建根节点
            root = {
                'name': 'ROOT',
                'total_time': total_time,
                'children': self._call_stack
            }
            
            f.write(self._format_tree(root))
    
    def _format_tree(self, node, indent_level=0, parent_time=None):
        """
        格式化调用树为文本
        
        Args:
            node: 树节点
            indent_level: 缩进级别
            parent_time: 父节点时间
            
        Returns:
            格式化后的文本
        """
        # 计算时间占比
        time_percent = ""
        if parent_time is not None and parent_time > 0:
            percent = (node['total_time'] / parent_time) * 100
            time_percent = f" - {percent:.2f}%"
        
        # 格式化输出行
        prefix = "│   " * (indent_level - 1) + "├── " if indent_level > 0 else ""
        line = f"{prefix}{node['name']}: {node['total_time']:.6f}s{time_percent}\n"
        
        # 递归处理子节点
        child_lines = []
        for child in sorted(node.get('children', []), key=lambda x: x['total_time'], reverse=True):
            child_lines.append(self._format_tree(child, indent_level + 1, node['total_time']))
        
        return line + "".join(child_lines)
    
    def reset(self) -> None:
        """重置所有性能统计数据"""
        self._time_records.clear()
        self._call_counts.clear()
        self._call_stack = []
    
    def enable(self, enabled: bool = True) -> None:
        """启用或禁用性能跟踪"""
        self._enabled = enabled
    
    def set_output_file(self, file_path: str) -> None:
        """设置输出文件路径"""
        self.output_file = file_path
        
    def __del__(self):
        """析构函数，确保清理定时器资源"""
        self._stop_existing_timers()

# 示例用法
if __name__ == "__main__":
    import time
    
    # 创建一个性能监控器实例，并设置输出文件和定时打印间隔(3000毫秒)
    monitor = PerformanceMonitor("performance_stats.txt", print_interval=3000)
    
    # 示例1：装饰整个类
    @monitor.profile()
    class Calculator:
        def add(self, a, b):
            time.sleep(0.1)  # 模拟耗时操作
            return a + b
        
        def multiply(self, a, b):
            time.sleep(0.2)  # 模拟耗时操作
            return a * b
        
        def complex_operation(self, a, b):
            self.add(a, b)
            return self.multiply(a, b)
    
    # 使用示例
    calc = Calculator()
    
    print("开始性能测试，每3秒将自动打印性能统计...")
    
    # 循环执行一些操作
    for i in range(10):
        calc.add(2, 3)
        calc.multiply(2, 3)
        if i % 3 == 0:
            calc.complex_operation(2, 3)
        time.sleep(1)  # 暂停1秒，让定时器有机会触发
    
    # 更改定时打印间隔为5秒
    print("\n更改定时打印间隔为5秒...")
    monitor.set_print_interval(5000)
    
    # 继续执行一些操作
    for i in range(5):
        calc.add(2, 3)
        calc.multiply(2, 3)
        time.sleep(1)
    
    # 停止定时打印
    print("\n停止定时打印...")
    monitor.set_print_interval(None)
    
    # 最后手动打印一次性能统计
    print("\n最终性能统计:")
    monitor.print_stats() 