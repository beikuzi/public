import os
import json
import hashlib
import threading

class DictSaver:
    def __init__(self, save_path='dict_cache.json', flush_interval=10):
        self.save_path = save_path
        self.cache = {}  # 内存缓存
        self._load()
        self.lock = threading.Lock()
        self.dirty = False
        self.flush_interval = flush_interval
        self._start_auto_flush()

    def _hash_key(self, key: str) -> str:
        return hashlib.md5(key.encode('utf-8')).hexdigest()

    def _load(self):
        if os.path.exists(self.save_path):
            try:
                with open(self.save_path, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}
        else:
            self.cache = {}

    def save_translation(self, key: str, val: str):
        hkey = self._hash_key(key)
        with self.lock:
            if self.cache.get(hkey) != val:
                self.cache[hkey] = val
                self.dirty = True

    def get_translation(self, key: str):
        hkey = self._hash_key(key)
        return self.cache.get(hkey)

    def flush(self):
        with self.lock:
            if self.dirty:
                with open(self.save_path, 'w', encoding='utf-8') as f:
                    json.dump(self.cache, f, ensure_ascii=False, indent=2)
                self.dirty = False

    def _start_auto_flush(self):
        def auto_flush():
            while True:
                threading.Event().wait(self.flush_interval)
                self.flush()
        t = threading.Thread(target=auto_flush, daemon=True)
        t.start()

    @staticmethod
    def merge_json_files(file_list, output_file):
        """
        合并多个翻译json文件为一个，后者覆盖前者
        :param file_list: 待合并的json文件路径列表
        :param output_file: 合并后输出的文件路径
        """
        merged = {}
        for file in file_list:
            if os.path.exists(file):
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        merged.update(data)
                except Exception as e:
                    print(f"合并文件 {file} 时出错: {e}")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)

    def switch_file(self, new_path):
        """
        切换当前使用的翻译文件，并自动加载内容
        :param new_path: 新的json文件路径
        """
        with self.lock:
            self.flush()  # 先保存当前内容
            self.save_path = new_path
            self._load()
            self.dirty = False

# 示例用法
if __name__ == '__main__':
    saver = DictSaver('dict_cache.json')
    key = '偶遇神人翻译，拼尽全力无法战胜'
    val = 'Encountering a divine translator by chance, I tried my best but couldn\'t overcome it'
    saver.save_translation(key, val)
    print('查找翻译：', saver.get_translation(key))
    saver.flush()
