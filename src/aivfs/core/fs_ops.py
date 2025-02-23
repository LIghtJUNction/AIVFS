from pathlib import Path
import shutil
import os
from datetime import datetime
from typing import Optional, Union, List
from ..metadata.manager import MetadataManager
from .interfaces import IMetadataManager
from .types import FileType, Permission, FileMetadata

class FSOperations:
    """文件系统操作类"""
    
    def __init__(self, root: Path, metadata: IMetadataManager):
        self.root = root
        self.metadata = metadata
        if isinstance(metadata, MetadataManager):
            metadata.set_fs_ops(self)

    def _normalize_path(self, path: str) -> Path:
        """规范化路径"""
        return self.root / path.lstrip('/')

    def create_file(self, path: str, content: str = "", 
                   owner: str = "root", group: str = "root", 
                   mode: tuple = (6, 4, 4)) -> None:
        """创建文件并更新元数据"""
        real_path = self._normalize_path(path)
        real_path.parent.mkdir(parents=True, exist_ok=True)
        real_path.write_text(content, encoding='utf-8')
        
        self._update_metadata(path, FileType.REGULAR, owner, group, mode)

    def append_file(self, path: str, content: str) -> None:
        """在文件末尾追加内容
        
        Args:
            path: 文件路径
            content: 要追加的内容
            
        Raises:
            FileNotFoundError: 文件不存在
            IsADirectoryError: 目标是目录
        """
        real_path = self._normalize_path(path)
        
        if not real_path.exists():
            raise FileNotFoundError(f"文件不存在: {path}")
            
        if real_path.is_dir():
            raise IsADirectoryError(f"目标是目录: {path}")
        
        # 追加内容
        with real_path.open('a', encoding='utf-8') as f:
            f.write(content)
        
        # 更新元数据中的文件大小和修改时间
        metadata = self.metadata.get_file(path)
        if metadata:
            metadata.size = real_path.stat().st_size
            metadata.modified_at = datetime.now()
            self.metadata.add_file(metadata)

    def mkdir(self, path: str, owner: str = "root", group: str = "root",
             mode: tuple = (7, 5, 5), parents: bool = False, 
             exist_ok: bool = False) -> None:
        """创建目录"""
        real_path = self._normalize_path(path)
        
        if real_path.exists() and not exist_ok:
            raise FileExistsError(f"目录已存在: {path}")
            
        real_path.mkdir(parents=parents, exist_ok=exist_ok)
        self._update_metadata(path, FileType.DIRECTORY, owner, group, mode)

    def makedirs(self, path: str, owner: str = "root", group: str = "root",
                mode: tuple = (7, 5, 5), exist_ok: bool = False) -> None:
        """递归创建目录"""
        self.mkdir(path, owner, group, mode, parents=True, exist_ok=exist_ok)

    def copy(self, src: str, dst: str, follow_symlinks: bool = True) -> None:
        """复制文件"""
        src_path = self._normalize_path(src)
        dst_path = self._normalize_path(dst)
        
        if not src_path.exists():
            raise FileNotFoundError(f"源文件不存在: {src}")
            
        if src_path.is_file():
            shutil.copy2(src_path, dst_path, follow_symlinks=follow_symlinks)
        else:
            raise IsADirectoryError(f"源路径是目录，请使用copytree: {src}")
            
        self._copy_metadata(src, dst)

    def copytree(self, src: str, dst: str, symlinks: bool = False, 
                ignore=None, dirs_exist_ok: bool = False) -> None:
        """递归复制目录"""
        src_path = self._normalize_path(src)
        dst_path = self._normalize_path(dst)
        
        if not src_path.is_dir():
            raise NotADirectoryError(f"源路径不是目录: {src}")
            
        shutil.copytree(src_path, dst_path, symlinks=symlinks,
                       ignore=ignore, dirs_exist_ok=dirs_exist_ok)
                       
        # 递归复制元数据
        for root, dirs, files in os.walk(src_path):
            rel_root = os.path.relpath(root, src_path)
            for name in dirs + files:
                src_rel = os.path.join(rel_root, name)
                dst_rel = os.path.join(dst, os.path.relpath(src_rel, src))
                self._copy_metadata(src_rel, dst_rel)

    def move(self, src: str, dst: str) -> None:
        """移动文件或目录"""
        src_path = self._normalize_path(src)
        dst_path = self._normalize_path(dst)
        
        if not src_path.exists():
            raise FileNotFoundError(f"源文件不存在: {src}")
            
        shutil.move(src_path, dst_path)
        self._move_metadata(src, dst)

    def remove(self, path: str) -> None:
        """删除文件"""
        real_path = self._normalize_path(path)
        
        if not real_path.exists():
            raise FileNotFoundError(f"文件不存在: {path}")
            
        if real_path.is_dir():
            raise IsADirectoryError(f"目标是目录，请使用rmtree: {path}")
            
        real_path.unlink()
        self.metadata.remove_file(path)

    def rmtree(self, path: str, ignore_errors: bool = False) -> None:
        """递归删除目录"""
        real_path = self._normalize_path(path)
        
        if not real_path.is_dir():
            raise NotADirectoryError(f"目标不是目录: {path}")
            
        # 先删除所有相关元数据
        for root, dirs, files in os.walk(real_path):
            rel_root = os.path.relpath(root, self.root)
            for name in dirs + files:
                rel_path = os.path.join(rel_root, name)
                self.metadata.remove_file(rel_path)
                
        shutil.rmtree(real_path, ignore_errors=ignore_errors)
        self.metadata.remove_file(path)

    def _update_metadata(self, path: str, file_type: FileType,
                        owner: str, group: str, mode: tuple) -> None:
        """更新文件元数据"""
        real_path = self._normalize_path(path)
        now = datetime.now()
        
        metadata = FileMetadata(
            path=path,
            file_type=file_type,
            owner=owner,
            group=group,
            size=real_path.stat().st_size if real_path.is_file() else None,
            created_at=now,
            modified_at=now,
            user_perm=Permission.from_mode(mode[0]),
            group_perm=Permission.from_mode(mode[1]),
            other_perm=Permission.from_mode(mode[2])
        )
        self.metadata.add_file(metadata)

    def _copy_metadata(self, src: str, dst: str) -> None:
        """复制元数据"""
        src_meta = self.metadata.get_file(src)
        if src_meta:
            dst_meta = FileMetadata(
                path=dst,
                file_type=src_meta.file_type,
                owner=src_meta.owner,
                group=src_meta.group,
                size=self._normalize_path(dst).stat().st_size 
                     if self._normalize_path(dst).is_file() else None,
                created_at=datetime.now(),
                modified_at=datetime.now(),
                user_perm=src_meta.user_perm,
                group_perm=src_meta.group_perm,
                other_perm=src_meta.other_perm
            )
            self.metadata.add_file(dst_meta)

    def _move_metadata(self, src: str, dst: str) -> None:
        """移动元数据"""
        self._copy_metadata(src, dst)
        self.metadata.remove_file(src)

    def get_metadata(self, path: str) -> Optional[FileMetadata]:
        """获取文件或目录的元数据
        
        Args:
            path: 文件或目录路径
            
        Returns:
            FileMetadata: 如果存在则返回元数据对象，否则返回None
        """
        return self.metadata.get_file(path)
    
    