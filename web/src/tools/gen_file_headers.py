# @desc: 生成import头文件

import os, sys
import importlib
import time
import concurrent.futures
work_dir = os.getcwd()
sys.path.append(work_dir)

# ====== 宏定义区 ======
SRC_DIR = os.path.join(work_dir, 'src')  # 要检测的目录
INCLUDE_DIR = os.path.join(work_dir, 'myhead')  # 头文件输出目录
MAX_WORKERS = 4  # 最大并行工作线程数
# =====================

src_root_name = os.path.basename(SRC_DIR)

def get_all_packages(base_dir):
    """返回base_dir下所有一级子文件夹（包）绝对路径"""
    return [os.path.join(base_dir, d) for d in os.listdir(base_dir)
            if os.path.isdir(os.path.join(base_dir, d)) and not d.startswith('__')]

def get_py_files_in_dir(dir_path):
    """返回dir_path下所有py文件（不递归），不含__init__"""
    return [os.path.join(dir_path, f) for f in os.listdir(dir_path)
            if f.endswith('.py') and not f.startswith('__init__') and os.path.isfile(os.path.join(dir_path, f))]

def extract_file_header_comment(pyfile):
    comments = []
    with open(pyfile, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip() == '':
                continue  # 空行也继续
            if line.strip().startswith('# @desc:'):
                comments.append(line.strip())
            elif line.strip().startswith('#'):
                continue  # 其它注释行跳过
            else:
                break  # 遇到非注释、非空行，停止
    return comments

def try_import_module(stmt, original_modules):
    """尝试导入单个模块，用于并发执行"""
    module_start_time = time.time()
    result = {
        'stmt': stmt,
        'success': False,
        'module': None,
        'error': None,
        'elapsed': 0
    }
    
    try:
        # 备份原始模块（如果存在）
        if stmt['alias'] not in original_modules:
            original_modules[stmt['alias']] = sys.modules.get(stmt['alias'])
        
        # 使用importlib导入模块
        module = importlib.import_module(stmt['import_path'])
        # 将模块添加到sys.modules
        sys.modules[stmt['alias']] = module
        result['success'] = True
        result['module'] = module
    except Exception as e:
        result['error'] = str(e)
    
    result['elapsed'] = time.time() - module_start_time
    return result

def gen_header_with_dependency_resolution(pkg_dir, base_dir, out_dir):
    """考虑依赖关系的头文件生成"""
    pkg_name = os.path.basename(pkg_dir)
    py_files = get_py_files_in_dir(pkg_dir)
    
    # 备份原始的sys.modules
    original_modules = {}
    
    # 第一步：生成所有导入语句（不执行）
    import_statements = []
    for pyfile in py_files:
        comments = extract_file_header_comment(pyfile)
        rel_path = os.path.relpath(pyfile, SRC_DIR).replace('\\', '/').replace('/', '.')
        if rel_path.endswith('.py'):
            rel_path = rel_path[:-3]
        import_path = f"{src_root_name}.{rel_path}"
        alias = os.path.splitext(os.path.basename(pyfile))[0]
        
        import_statements.append({
            'alias': alias,
            'import_path': import_path,
            'comments': comments,
            'success': False
        })
    
    # 第二步：并发尝试导入，失败的后置
    Len = len(import_statements) + 1
    max_attempts = Len * Len   # 防止无限循环
    attempts = 0
    successful_imports = []
    
    # 开始计时
    step2_start_time = time.time()
    
    while import_statements and attempts < max_attempts:
        attempts += 1
        failed_imports = []
        
        print(f"  第{attempts}轮开始，剩余{len(import_statements)}个模块")
        
        # 使用线程池并发导入
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # 提交所有导入任务
            future_to_stmt = {
                executor.submit(try_import_module, stmt, original_modules): stmt 
                for stmt in import_statements
            }
            
            # 处理结果
            for future in concurrent.futures.as_completed(future_to_stmt):
                result = future.result()
                stmt = result['stmt']
                
                if result['success']:
                    stmt['success'] = True
                    successful_imports.append(stmt)
                    # print(f"    ✓ {stmt['alias']}: {result['elapsed']:.2f}秒")
                else:
                    failed_imports.append(stmt)
                    # print(f"    ✗ {stmt['alias']}: {result['elapsed']:.2f}秒 - {result['error']}")
        
        # 如果这一轮没有成功导入任何模块，说明有循环依赖
        if len(failed_imports) == len(import_statements):
            print(f"    警告：可能存在循环依赖，强制导入剩余模块")
            successful_imports.extend(failed_imports)
            break
            
        import_statements = failed_imports
        # print(f"  第{attempts}轮结束，成功{len(successful_imports)}个，失败{len(failed_imports)}个")
    
    # 第二步结束，计算耗时
    step2_elapsed = time.time() - step2_start_time
    print(f"{pkg_name}: 导入耗时 {step2_elapsed:.2f}秒")
    
    # 第三步：生成头文件
    import_lines = []
    import_lines.append("import sys")
    import_lines.append("_modules_backup = {}")
    
    for stmt in successful_imports:
        # 添加注释
        for comment in stmt['comments']:
            import_lines.append(comment)
        
        # 添加导入和备份代码
        import_lines.append(f"try:")
        import_lines.append(f"    import {stmt['import_path']} as {stmt['alias']}")
        import_lines.append(f"    if '{stmt['alias']}' not in _modules_backup:")
        import_lines.append(f"        _modules_backup['{stmt['alias']}'] = sys.modules.get('{stmt['alias']}')")
        import_lines.append(f"    sys.modules['{stmt['alias']}'] = {stmt['alias']}")
        import_lines.append(f"except Exception as e: print(f\"导入 {stmt['import_path']} 失败: {{e}}\")")
    
    # 添加恢复函数
    import_lines.append("\ndef restore_modules():")
    import_lines.append("    for module_name, original_module in _modules_backup.items():")
    import_lines.append("        if original_module is None:")
    import_lines.append("            if module_name in sys.modules:")
    import_lines.append("                del sys.modules[module_name]")
    import_lines.append("        else:")
    import_lines.append("            sys.modules[module_name] = original_module")
    import_lines.append("    print(\"已恢复原始sys.modules\")")
    
    # 写入文件
    header_path = os.path.join(out_dir, f"{pkg_name}_h.py")
    with open(header_path, 'w', encoding='utf-8') as f:
        f.write("# 自动生成的import头文件\n")
        for line in import_lines:
            f.write(line + '\n')
    
    # 第四步：还原sys.modules
    # print(f"还原sys.modules...")
    for module_name, original_module in original_modules.items():
        if original_module is None:
            if module_name in sys.modules:
                del sys.modules[module_name]
        else:
            sys.modules[module_name] = original_module
    # print(f"已还原原始sys.modules")
    
    print(f"已生成头文件: {header_path}，成功导入{len(successful_imports)}个模块")

def main():
    os.makedirs(INCLUDE_DIR, exist_ok=True)
    # 先处理src下所有一级包
    pkgs = get_all_packages(SRC_DIR)
    for pkg_dir in pkgs:
        gen_header_with_dependency_resolution(pkg_dir, SRC_DIR, INCLUDE_DIR)
        # 移除生成__init__.py的代码
        
        # 处理该包下的子包
        sub_pkgs = get_all_packages(pkg_dir)
        for sub_pkg_dir in sub_pkgs:
            gen_header_with_dependency_resolution(sub_pkg_dir, SRC_DIR, INCLUDE_DIR)
            # 移除生成__init__.py的代码

if __name__ == '__main__':
    main()