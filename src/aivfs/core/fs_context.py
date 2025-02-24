from pathlib import Path
from typing import Optional
from .fs import AIVFS
from .types import PathLike

class AIVFSContext:
    """AIVFS文件系统上下文管理器"""
    
    def __init__(self, path: Optional[PathLike] = None, force: bool = False):
        """初始化上下文管理器
        
        Args:
            path: 文件系统路径
            force: 是否强制创建
        """
        self.path = Path(path or 'aivfs_root')
        self.force = force
        self.fs: Optional[AIVFS] = None
    
    def __enter__(self) -> AIVFS:
        """进入上下文"""
        self.fs = AIVFS.create(self.path, self.force)
        return self.fs
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """退出上下文"""
        if self.fs:
            self._cleanup()
            self.fs = None
    
    def _cleanup(self):
        """清理资源"""
        if hasattr(self.fs, '_path_cache'):
            self.fs._path_cache.clear()
        self.fs.metadata = None
        self.fs.fs_ops = None