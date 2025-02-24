from pathlib import Path
import shutil
import os
from datetime import datetime
from typing import Optional, List, Dict, Union, Callable
from functools import wraps
from ..metadata.manager import MetadataManager
from .interfaces import IMetadataManager, IFSOperations
from .types import FileType, FileMetadata, PathLike, FileMode
from .exceptions import (
    FileNotFoundError, FileExistsError, IsADirectoryError, MetadataError,
    NotADirectoryError, PermissionError, InvalidPathError,
    FileSystemError
)

def validate_path(func: Callable) -> Callable:
    """路径验证装饰器"""
    @wraps(func)
    def wrapper(self, path: PathLike, *args, **kwargs):
        if not path:
            raise InvalidPathError("路径不能为空")
        path_str = str(path)
        if not path_str.startswith('/'):
            raise InvalidPathError(path_str, "必须使用绝对路径")
        return func(self, path, *args, **kwargs)
    return wrapper

class FSOperations(IFSOperations):
    """文件系统操作类
    
    提供基本的文件系统操作，包括：
    - 文件读写
    - 目录管理
    - 元数据操作
    - 权限控制
    """
    
    def __init__(self, root: Path, metadata: IMetadataManager):
        """初始化文件系统操作
        
        Args:
            root: 文件系统根目录
            metadata: 元数据管理器实例
        """
        self.root = root.absolute()
        self.metadata = metadata
        # 使用接口类型而不是具体实现
        metadata.set_fs_ops(self)
        
        # 缓存常用路径的真实路径
        self._path_cache: Dict[str, Path] = {}

    def _normalize_path(self, path: PathLike) -> Path:
        """规范化路径并使用缓存
        
        Args:
            path: 原始路径
            
        Returns:
            Path: 规范化后的绝对路径
        """
        path_str = str(path)
        if path_str in self._path_cache:
            return self._path_cache[path_str]
        
        normalized = self.root / path_str.lstrip('/')
        self._path_cache[path_str] = normalized
        return normalized

    @validate_path
    def write_file(self, path: PathLike, content: str, *, 
                  owner: str = "root", group: str = "root",
                  mode: FileMode = FileMode(6, 4, 4)) -> None:
        """写入文件内容"""
        real_path = self._normalize_path(path)
        if real_path.exists():
            if real_path.is_dir():
                raise IsADirectoryError(str(path))
            # 检查是否有写权限
            if not os.access(real_path, os.W_OK):
                raise PermissionError(str(path), "write", "没有写入权限")
        
        try:
            # 确保父目录存在
            real_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 使用临时文件写入
            temp_path = real_path.with_suffix('.tmp')
            temp_path.write_text(content, encoding='utf-8')
            temp_path.replace(real_path)
            
            # 更新元数据
            self._update_metadata(path, FileType.REGULAR, owner, group, mode)
        except OSError as e:
            raise FileSystemError(f"写入文件失败: {e}")
        finally:
            # 清理临时文件
            if temp_path.exists():
                temp_path.unlink()

    @validate_path
    def read_file(self, path: PathLike) -> str:
        """读取文件内容"""
        real_path = self._normalize_path(path)
        if not real_path.exists():
            raise FileNotFoundError(str(path))
        if real_path.is_dir():
            raise IsADirectoryError(str(path))
        if not os.access(real_path, os.R_OK):
            raise PermissionError(str(path), "read", "没有读取权限")
            
        try:
            return real_path.read_text(encoding='utf-8')
        except OSError as e:
            raise FileSystemError(f"读取文件失败: {e}")

    def append_file(self, path: PathLike, content: str) -> None:
        """在文件末尾追加内容"""
        real_path = self._normalize_path(path)
        if not real_path.exists():
            raise FileNotFoundError(f"文件不存在: {path}")
        if real_path.is_dir():
            raise IsADirectoryError(f"目标是目录: {path}")
        
        with real_path.open('a', encoding='utf-8') as f:
            f.write(content)
        
        metadata = self.get_metadata(path)
        if metadata:
            metadata.size = real_path.stat().st_size
            metadata.modified_at = datetime.now()
            self.metadata.upsert(metadata)

    # 目录操作
    def mkdir(self, path: PathLike, *, 
             owner: str = "root", group: str = "root",
             mode: FileMode = FileMode(7, 5, 5),
             parents: bool = False, exist_ok: bool = False) -> None:
        """创建目录"""
        real_path = self._normalize_path(path)
        if real_path.exists():
            if not exist_ok:
                raise FileExistsError(str(path))
            if not real_path.is_dir():
                raise NotADirectoryError(str(path))
        real_path.mkdir(parents=parents, exist_ok=exist_ok)
        self._update_metadata(path, FileType.DIRECTORY, owner, group, mode)

    # 路径操作
    def remove(self, path: PathLike, recursive: bool = False) -> None:
        """删除文件或目录"""
        real_path = self._normalize_path(path)
        if not real_path.exists():
            raise FileNotFoundError(f"路径不存在: {path}")
        if real_path.is_dir():
            if not recursive:
                raise IsADirectoryError(f"目标是目录，需要设置recursive=True: {path}")
            self._remove_tree(real_path)
        else:
            real_path.unlink()
            self.metadata.remove(str(path))

    def copy(self, src: PathLike, dst: PathLike, recursive: bool = False) -> None:
        """复制文件或目录"""
        src_path = self._normalize_path(src)
        dst_path = self._normalize_path(dst)
        
        if not src_path.exists():
            raise FileNotFoundError(f"源路径不存在: {src}")
        if src_path.is_dir():
            if not recursive:
                raise IsADirectoryError(f"源是目录，需要设置recursive=True: {src}")
            shutil.copytree(src_path, dst_path)
            self._copy_metadata(str(src), str(dst))
        else:
            shutil.copy2(src_path, dst_path)
            self._copy_metadata(str(src), str(dst))

    def move(self, src: PathLike, dst: PathLike) -> None:
        """移动文件或目录"""
        src_path = self._normalize_path(src)
        dst_path = self._normalize_path(dst)
        if not src_path.exists():
            raise FileNotFoundError(f"源路径不存在: {src}")
        shutil.move(src_path, dst_path)
        metadata = self.get_metadata(src)
        if metadata:
            metadata.path = str(dst)
            self.metadata.upsert(metadata)
            self.metadata.remove(str(src))

    # 信息查询
    def get_metadata(self, path: PathLike) -> Optional[FileMetadata]:
        """获取文件或目录的元数据"""
        return self.metadata.get(str(path))

    def list_dir(self, path: PathLike) -> List[str]:
        """列出目录内容"""
        real_path = self._normalize_path(path)
        if not real_path.exists():
            raise FileNotFoundError(f"目录不存在: {path}")
        if not real_path.is_dir():
            raise NotADirectoryError(f"不是目录: {path}")
        
        try:
            return [item.name for item in real_path.iterdir()]
        except PermissionError:
            raise PermissionError(str(path), "read", "没有读取权限")
        except OSError as e:
            raise FileSystemError(f"列出目录内容失败: {e}")

    def exists(self, path: PathLike) -> bool:
        """检查路径是否存在"""
        real_path = self._normalize_path(path)
        return real_path.exists()

    def chmod(self, path: PathLike, mode: FileMode) -> None:
        """修改文件或目录的权限模式"""
        metadata = self.get_metadata(path)
        if not metadata:
            raise FileNotFoundError(str(path))
        
        metadata.user_perm = mode.user
        metadata.group_perm = mode.group
        metadata.other_perm = mode.other
        self.metadata.upsert(metadata)

    def chown(self, path: PathLike, owner: str, group: str) -> None:
        """修改文件或目录的所有者和组"""
        metadata = self.get_metadata(path)
        if not metadata:
            raise FileNotFoundError(str(path))
        
        metadata.owner = owner
        metadata.group = group
        self.metadata.upsert(metadata)

    def get_type(self, path: PathLike) -> FileType:
        """获取文件类型"""
        real_path = self._normalize_path(path)
        if not real_path.exists():
            raise FileNotFoundError(f"路径不存在: {path}")
        return FileType.DIRECTORY if real_path.is_dir() else FileType.REGULAR

    # 辅助方法
    def _remove_tree(self, path: Path) -> None:
        """递归删除目录及其元数据
        
        使用深度优先遍历，确保先删除子项再删除父项
        """
        try:
            # 收集所有需要删除的路径
            paths_to_remove = []
            for root, dirs, files in os.walk(path, topdown=False):
                rel_root = os.path.relpath(root, self.root)
                for name in files + dirs:
                    paths_to_remove.append(os.path.join(rel_root, name))
            
            # 批量删除元数据
            for p in paths_to_remove:
                self.metadata.remove(p)
            
            # 删除文件系统内容
            shutil.rmtree(path)
            
        except OSError as e:
            raise FileSystemError(f"删除目录失败: {e}")

    def _copy_metadata(self, src: str, dst: str) -> None:
        """复制元数据，保持文件属性"""
        try:
            if metadata := self.get_metadata(src):
                new_metadata = FileMetadata(
                    path=dst,
                    file_type=metadata.file_type,
                    owner=metadata.owner,
                    group=metadata.group,
                    size=metadata.size,
                    created_at=datetime.now(),
                    modified_at=datetime.now(),
                    user_perm=metadata.user_perm,
                    group_perm=metadata.group_perm,
                    other_perm=metadata.other_perm
                )
                self.metadata.upsert(new_metadata)
        except Exception as e:
            raise MetadataError(f"复制元数据失败: {e}")

    def _update_metadata(self, path: PathLike, file_type: FileType,
                        owner: str, group: str, mode: FileMode) -> None:
        """更新文件元数据"""
        real_path = self._normalize_path(path)
        now = datetime.now()
        metadata = FileMetadata(
            path=str(path),
            file_type=file_type,
            owner=owner,
            group=group,
            size=real_path.stat().st_size if real_path.is_file() else None,
            created_at=now,
            modified_at=now,
            user_perm=mode.user,
            group_perm=mode.group,
            other_perm=mode.other
        )
        self.metadata.upsert(metadata)

    def __enter__(self) -> 'FSOperations':
        """支持上下文管理器"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """清理资源"""
        self._path_cache.clear()