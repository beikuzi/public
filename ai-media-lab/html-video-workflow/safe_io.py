"""Local single-writer path guards. Not a sandbox for hostile concurrent filesystem mutation."""
import os,pathlib,stat,tempfile

def checked_path(path, *, allow_missing=False):
    path=pathlib.Path(os.path.abspath(path))
    for part in reversed([path,*path.parents]):
        try: info=part.lstat()
        except FileNotFoundError:
            if allow_missing:continue
            raise ValueError(f'Missing path: {part.name}')
        if stat.S_ISLNK(info.st_mode):raise ValueError(f'Symlink path is forbidden: {part.name}')
        if part!=path and not stat.S_ISDIR(info.st_mode):raise ValueError('Non-directory path ancestor')
        if part==path and not(stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
            raise ValueError('Special files are forbidden')
        if part==path and stat.S_ISREG(info.st_mode) and info.st_nlink!=1:
            raise ValueError('Hard-linked files are forbidden')
    return path

def guard_directory(path):
    root=checked_path(path)
    if not root.is_dir():raise ValueError('Expected directory')
    # Reject all existing descendants before writes, including dangling links and marker files.
    for current,dirs,files in os.walk(root,followlinks=False):
        for name in dirs+files:checked_path(pathlib.Path(current)/name)
    return root

def safe_target(path):
    path=pathlib.Path(path);guard_directory(path.parent)
    checked_path(path,allow_missing=True)
    if path.exists() and not path.is_file():raise ValueError('Output target must be a regular file')
    return path

def write_text(path,text):
    path=safe_target(path)
    fd,tmp=tempfile.mkstemp(prefix='.write-',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:f.write(text)
        checked_path(path,allow_missing=True)
        os.replace(tmp,path)  # Replaces a directory entry; never follows a target link.
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
