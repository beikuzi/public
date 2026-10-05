"""Private local runtime paths; the owner must also review Windows account ACLs."""
import os
from pathlib import Path
from .providers import TranslationError


def reject_links(path):
    path = Path(path).absolute()
    for candidate in (path, *path.parents):
        if candidate.is_symlink() or (hasattr(candidate, "is_junction") and candidate.is_junction()):
            raise TranslationError("Runtime paths must not contain symlinks or junctions")
    return path


def private_dir(path):
    path = reject_links(path)
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name == "posix":
        path.chmod(0o700)
    return path


def private_file(path):
    path = reject_links(path)
    if path.exists() and os.name == "posix":
        if path.stat().st_nlink != 1:
            raise TranslationError("Runtime files must not be hard-linked")
        path.chmod(0o600)
    return path
