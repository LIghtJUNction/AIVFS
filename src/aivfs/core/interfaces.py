from abc import ABC, abstractmethod

from typing import Optional, Protocol, List
from .types import FileMode, PathLike, FileMetadata, FileType
class IMetadataManager(Protocol):
    """元数据管理器接口
    
    主要职责：
    1. 管理文件和目录的元数据
    2. 提供元数据的查询和修改功能
    3. 支持目录列表功能
    """
    def upsert(self, metadata: FileMetadata) -> None:
        """添加或更新元数据"""
        ...
        
    def get(self, path: PathLike) -> Optional[FileMetadata]:
        """获取元数据，如果不存在则继承父目录元数据"""
        ...
        
    def remove(self, path: PathLike) -> None:
        """删除元数据"""
        ...
        
    def list_dir(self, path: PathLike) -> List[FileMetadata]:
        """列出目录内容的元数据"""
        ...
        
    def exists(self, path: PathLike) -> bool:
        """检查是否存在元数据"""
        ...

class IFSOperations(ABC):
    """文件系统操作接口"""
    # 基本文件操作
    @abstractmethod
    def write_file(self, path: PathLike, content: str, *, 
                  owner: str = "root", group: str = "root",
                  mode: FileMode = FileMode(6, 4, 4)) -> None: ...
    @abstractmethod
    def read_file(self, path: PathLike) -> str: ...
    @abstractmethod
    def append_file(self, path: PathLike, content: str) -> None: ...
    
    # 目录操作
    @abstractmethod
    def mkdir(self, path: PathLike, *, 
             owner: str = "root", group: str = "root",
             mode: FileMode = FileMode(7, 5, 5),
             parents: bool = False, exist_ok: bool = False) -> None: ...
    
    # 路径操作
    @abstractmethod
    def remove(self, path: PathLike, recursive: bool = False) -> None: ...
    @abstractmethod
    def copy(self, src: PathLike, dst: PathLike, 
            recursive: bool = False) -> None: ...
    @abstractmethod
    def move(self, src: PathLike, dst: PathLike) -> None: ...
    
    # 信息查询
    @abstractmethod
    def get_metadata(self, path: PathLike) -> Optional[FileMetadata]: ...
    @abstractmethod
    def list_dir(self, path: PathLike) -> List[str]: ...
    @abstractmethod
    def exists(self, path: PathLike) -> bool: ...
    @abstractmethod
    def get_type(self, path: PathLike) -> FileType: ...
    @abstractmethod
    def chmod(self, path: PathLike, mode: FileMode) -> None:
        """修改文件或目录的权限模式"""
        pass

    @abstractmethod
    def chown(self, path: PathLike, owner: str, group: str) -> None:
        """修改文件或目录的所有者和组"""
        pass