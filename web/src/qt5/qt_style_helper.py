import string

# 全局默认
QSS_DEFAULTS = {
    'font_size': 12,
    'font_family': 'Microsoft YaHei, sans-serif',
}

QSS_COMMON = '''
QSplitter::handle {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #0078d7, stop:1 #005499);
    border: 1px solid #003366;
    width: 8px;
    border-radius: 4px;
}}
QWidget {{
    background: #f7f7fa;
    font-size: {font_size}px;
    font-family: {font_family};
}}
QPushButton {{
    background: #e6f0fa;
}}
QPushButton:hover {{
    background: #d0e7ff;
}}
QLineEdit, QComboBox {{
    background: white;
}}
QPushButton, QLineEdit, QComboBox {{
    border: 1px solid #ccc;
    border-radius: 3px;
    padding: 2px 5px;
    color: #333;
    padding-left: 8px;
    font-family: {font_family};
}}
QLineEdit:focus {{
    border-color: #0078D7;
}}
QPlainTextEdit {{
    background: #f4f4f4;
    border: 1px solid #b0c4de;
    border-radius: 6px;
    font-family: {font_family};
    font-size: {font_size}px;
}}
QLabel {{
    font-weight: bold;
    color: #333;
}}
'''

QSS_ERROR = '''
    QLabel {{
        background: #ffcccc;
        color: #b20000;
        font-weight: bold;
        border: 1px solid #b20000;
        border-radius: 4px;
        font-family: {font_family};
        font-size: {font_size}px;
    }}
    QPlainTextEdit {{
        background: #ffcccc;
        color: #b20000;
        font-weight: bold;
        border: 1px solid #b20000;
        border-radius: 4px;
        font-family: {font_family};
        font-size: {font_size}px;
    }}
'''

name_map = {
    'error': QSS_ERROR,
    'common': QSS_COMMON,
}

def get_qss(type='common', arg_dict = {}):
    QSS = name_map[type]
    params = QSS_DEFAULTS.copy()
    params.update(arg_dict)
    # 检查模板中所有变量，补全缺失项
    formatter = string.Formatter()
    needed_keys = {fname for _, fname, _, _ in formatter.parse(QSS) if fname}
    for key in needed_keys:
        if key not in params:
            params[key] = ''
    return QSS.format(**params)

if __name__ == '__main__':
    print('--- 默认QSS ---')
    print(get_qss())
    print('\n--- 自定义字体和字号 ---')
    print(get_qss(arg_dict={'font_family': 'Arial', 'font_size': 18}))
    print('\n--- 错误样式QSS ---')
    print(get_qss(arg_dict={'font_family': 'Consolas', 'font_size': 14}, type='error'))

