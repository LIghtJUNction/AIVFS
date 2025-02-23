from pathlib import Path
from typing import Optional

from aivfs.core.types import FileMetadata
from ..metadata.manager import MetadataManager
from .fs_ops import FSOperations

class AIVFS:
    """AIVFS文件系统实例"""
    
    def __init__(self, root: Path):
        self.root = root.absolute()
        self.metadata = MetadataManager(self.root)
        self.fs_ops = FSOperations(self.root, self.metadata)
    
    @classmethod
    def create(cls, root: Path, force: bool = False) -> 'AIVFS':
        """创建新的文件系统"""
        if root.exists() and not force:
            raise ValueError(f"目录已存在: {root}")
        
        fs = cls(root)
        fs._init_fs_structure()
        return fs
    
    @classmethod
    def mount(cls, root: Path) -> 'AIVFS':
        """挂载已存在的文件系统"""
        if not (root / '.aivroot').exists():
            raise ValueError(f"不是有效的AIVFS文件系统: {root}")
        return cls(root)
    
    def _init_fs_structure(self):
        """初始化文件系统结构"""
        # 创建根目录
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / '.aivroot').touch()

        # 创建基本目录结构，使用fs_ops确保创建元数据
        dirs = ['bin', 'etc', 'home', 'var', 'tmp']
        for d in dirs:
            self.fs_ops.mkdir(d, 
                             owner="root", 
                             group="root", 
                             mode=(7, 5, 5),  # rwxr-xr-x
                             exist_ok=True)  # 添加 exist_ok=True
    
    def create_file(self, path: str, content: str = "", owner: str = "root", 
                   group: str = "root", mode: tuple = (6, 4, 4)) -> None:
        """创建文件"""
        self.fs_ops.create_file(path, content, owner, group, mode)
    
    def append_file(self, path: str, content: str) -> None:
        """在文件末尾追加内容"""
        self.fs_ops.append_file(path, content)

    def copy(self, src: str, dst: str) -> None:
        """复制文件或目录"""
        self.fs_ops.copy(src, dst)
    
    def remove(self, path: str) -> None:
        """删除文件或目录"""
        self.fs_ops.remove(path)

    def mkdir(self, path: str, owner: str = "root", group: str = "root",
              mode: tuple = (7, 5, 5), parents: bool = False,
              exist_ok: bool = False) -> None:
        """创建目录
        
        Args:
            path: 目录路径
            owner: 所有者，默认为root
            group: 组，默认为root
            mode: 权限元组(user,group,other)，默认为(7,5,5)
            parents: 是否创建父目录，默认False
            exist_ok: 是否允许目录已存在，默认False
        """
        self.fs_ops.mkdir(path, owner, group, mode, parents, exist_ok)

    def makedirs(self, path: str, owner: str = "root", group: str = "root",
                mode: tuple = (7, 5, 5), exist_ok: bool = False) -> None:
        """递归创建目录
        
        Args:
            path: 目录路径
            owner: 所有者，默认为root
            group: 组，默认为root
            mode: 权限元组(user,group,other)，默认为(7,5,5)
            exist_ok: 是否允许目录已存在，默认False
        """
        self.fs_ops.makedirs(path, owner, group, mode, exist_ok)

    def copytree(self, src: str, dst: str, symlinks: bool = False,
                ignore=None, dirs_exist_ok: bool = False) -> None:
        """递归复制目录
        
        Args:
            src: 源目录
            dst: 目标目录
            symlinks: 是否跟随符号链接
            ignore: 忽略函数
            dirs_exist_ok: 是否允许目标目录存在
        """
        self.fs_ops.copytree(src, dst, symlinks, ignore, dirs_exist_ok)

    def rmtree(self, path: str, ignore_errors: bool = False) -> None:
        """递归删除目录
        
        Args:
            path: 目录路径
            ignore_errors: 是否忽略错误
        """
        self.fs_ops.rmtree(path, ignore_errors)

    def get_metadata(self, path: str) -> Optional[FileMetadata]:
        """获取文件或目录的元数据
        
        Args:
            path: 文件或目录路径
            
        Returns:
            FileMetadata: 元数据对象，如果不存在返回None
        """
        return self.fs_ops.get_metadata(path)

    def close(self) -> None:
        """关闭文件系统"""
        self.metadata.close()