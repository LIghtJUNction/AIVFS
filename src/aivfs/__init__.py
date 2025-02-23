from pathlib import Path
from typing import Optional
from .core.fs import AIVFS

def init(path: Optional[str] = None, force: bool = False) -> AIVFS:
    """初始化AIVFS文件系统"""
    root = Path(path or 'aivfs_root')
    if force and root.exists():
        import shutil
        shutil.rmtree(root)
    return AIVFS.create(root, force)

def mount(path: Optional[str] = None) -> AIVFS:
    """挂载已存在的AIVFS文件系统"""
    root = Path(path or 'aivfs_root')
    return AIVFS.mount(root)


