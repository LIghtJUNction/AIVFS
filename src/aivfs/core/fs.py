from pathlib import Path
from typing import Optional, List, Set, Dict, Union, Iterator, Tuple
from datetime import datetime
from fnmatch import fnmatch

from .types import FileMetadata, FileMode, PathLike, FileType, Permission
from .interfaces import IMetadataManager, IFSOperations
from .exceptions import *

# 推迟导入具体实现类
from ..metadata.manager import MetadataManager
from .fs_ops import FSOperations

class AIVFS:
    """AIVFS文件系统实例
    
    提供高层文件系统操作接口，支持：
    1. 文件和目录的基本操作（创建、读写、复制、移动、删除）
    2. 元数据管理（权限、所有者、时间戳）
    3. 文件系统初始化和挂载
    4. 权限控制和安全检查
    5. 文件系统遍历和搜索
    6. 磁盘使用情况统计
    """
    
    # 文件系统默认配置
    DEFAULT_ROOT_MODE = FileMode(7, 5, 5)  # rwxr-xr-x
    DEFAULT_FILE_MODE = FileMode(6, 4, 4)  # rw-r--r--
    
    # 基本目录结构配置
    DIRECTORY_STRUCTURE = {
        'bin':  ('root', 'root',  FileMode(7, 5, 5)),  # 可执行文件目录
        'etc':  ('root', 'root',  FileMode(7, 4, 4)),  # 系统配置目录
        'home': ('root', 'users', FileMode(7, 5, 5)),  # 用户目录
        'var':  ('root', 'root',  FileMode(7, 5, 0)),  # 可变数据目录
        'tmp':  ('root', 'users', FileMode(7, 7, 7)),  # 临时文件目录
        'usr':  ('root', 'root',  FileMode(7, 5, 5)),  # 用户程序目录
        'lib':  ('root', 'root',  FileMode(7, 5, 5)),  # 库文件目录
        'mnt':  ('root', 'root',  FileMode(7, 5, 5)),  # 挂载点目录
        'opt':  ('root', 'root',  FileMode(7, 5, 5)),  # 可选程序目录
    }
    
    def __init__(self, root: Path):
        """初始化文件系统实例
        
        Args:
            root: 文件系统根目录路径
        
        Raises:
            FileSystemError: 初始化失败
        """
        try:
            self.root = root.absolute()
            # 先创建元数据管理器
            self.metadata: IMetadataManager = MetadataManager(self.root)
            # 再创建文件系统操作实例
            self.fs_ops: IFSOperations = FSOperations(self.root, self.metadata)
            self._path_cache: Dict[str, Path] = {}
        except Exception as e:
            raise FileSystemError(f"初始化文件系统失败: {e}")

    @classmethod
    def create(cls, root: Path, force: bool = False) -> 'AIVFS':
        """创建新的文件系统
        
        Args:
            root: 文件系统根目录路径
            force: 是否强制创建（如果目录已存在则覆盖）
            
        Returns:
            AIVFS: 新创建的文件系统实例
            
        Raises:
            InvalidPathError: 路径无效
            FileSystemError: 创建失败
        """
        if not isinstance(root, Path):
            raise InvalidPathError(str(root), "路径必须是 Path 对象")
            
        try:
            fs = cls(root)
            fs._init_fs_structure()
            return fs
        except Exception as e:
            raise FileSystemError(f"创建文件系统失败: {e}")

    @classmethod
    def mount(cls, root: Path) -> 'AIVFS':
        """挂载已存在的文件系统
        
        Args:
            root: 文件系统根目录路径
            
        Returns:
            AIVFS: 挂载的文件系统实例
            
        Raises:
            ValueError: 不是有效的文件系统
            FileSystemError: 挂载失败
        """
        try:
            if not (root / '.aivroot').exists():
                raise ValueError(f"不是有效的AIVFS文件系统: {root}")
            return cls(root)
        except Exception as e:
            raise FileSystemError(f"挂载文件系统失败: {e}")

    def _init_fs_structure(self) -> None:
        """初始化文件系统结构
        
        创建基本目录结构和系统文件。
        
        Raises:
            FileSystemError: 初始化失败
        """
        try:
            # 创建根目录和.aivroot文件
            self.fs_ops.mkdir('/', owner="root", group="root",
                            mode=self.DEFAULT_ROOT_MODE, parents=True, exist_ok=True)
            self.fs_ops.write_file('/.aivroot', "", owner="root", group="root",
                                mode=self.DEFAULT_FILE_MODE)
            
            # 创建基本目录结构
            for dir_name, (owner, group, mode) in self.DIRECTORY_STRUCTURE.items():
                self.fs_ops.mkdir(f'/{dir_name}', owner=owner, group=group,
                                mode=mode, exist_ok=True)
        except Exception as e:
            raise FileSystemError(f"初始化文件系统结构失败: {e}")

    def walk(self, path: PathLike = '/') -> Iterator[tuple[str, List[str], List[str]]]:
        """遍历目录树
        
        Args:
            path: 起始目录路径
            
        Yields:
            tuple: (当前目录路径, [子目录列表], [文件列表])
        """
        real_path = self.root / str(path).lstrip('/')
        for root, dirs, files in os.walk(real_path):
            rel_root = str(Path(root).relative_to(self.root))
            yield f'/{rel_root}', dirs, files
    
    def find(self, path: PathLike = '/', pattern: str = '*') -> Iterator[str]:
        """搜索文件或目录
        
        Args:
            path: 搜索起始目录
            pattern: 匹配模式（支持通配符）
            
        Yields:
            str: 匹配的文件或目录路径
        """
        for root, dirs, files in self.walk(path):
            for name in dirs + files:
                if fnmatch(name, pattern):
                    yield str(Path(root) / name)
    
    def get_disk_usage(self, path: PathLike = '/') -> tuple[int, int, int]:
        """获取磁盘使用情况
        
        Args:
            path: 目标路径
            
        Returns:
            tuple: (总大小, 已用空间, 可用空间)
        """
        import shutil
        real_path = self.root / str(path).lstrip('/')
        total, used, free = shutil.disk_usage(real_path)
        return total, used, free
    
    # 文件操作
    def write_file(self, path: PathLike, content: str = "", *, 
                  owner: str = "root", group: str = "root",
                  mode: FileMode = FileMode(6, 4, 4)) -> None:
        """写入文件内容"""
        if not self._check_path(path):
            raise InvalidPathError(str(path), "包含非法字符")
            
        try:
            self.fs_ops.write_file(path, content, owner=owner, group=group, mode=mode)
        except Exception as e:
            raise FileSystemError(f"写入文件失败: {e}")
    
    def append_file(self, path: PathLike, content: str) -> None:
        """在文件末尾追加内容"""
        self.fs_ops.append_file(path, content)
    
    def read_file(self, path: PathLike) -> str:
        """读取文件内容"""
        return self.fs_ops.read_file(path)
    
    # 目录操作
    def mkdir(self, path: PathLike, *, owner: str = "root", group: str = "root",
             mode: FileMode = FileMode(7, 5, 5), parents: bool = False,
             exist_ok: bool = False) -> None:
        """创建目录"""
        self.fs_ops.mkdir(path, owner=owner, group=group, mode=mode,
                         parents=parents, exist_ok=exist_ok)
    
    # 通用操作
    def copy(self, src: PathLike, dst: PathLike, recursive: bool = False) -> None:
        """复制文件或目录"""
        self.fs_ops.copy(src, dst, recursive=recursive)
    
    def remove(self, path: PathLike, recursive: bool = False) -> None:
        """删除文件或目录"""
        self.fs_ops.remove(path, recursive=recursive)
    
    def move(self, src: PathLike, dst: PathLike) -> None:
        """移动文件或目录"""
        self.fs_ops.move(src, dst)
    
    def exists(self, path: PathLike) -> bool:
        """检查路径是否存在
        
        Args:
            path: 要检查的路径
            
        Returns:
            bool: 路径是否存在
        """
        return self.fs_ops.exists(path)
    
    def chmod(self, path: PathLike, mode: FileMode) -> None:
        """修改文件或目录的权限模式
        
        Args:
            path: 目标路径
            mode: 新的权限模式
        """
        self.fs_ops.chmod(path, mode)
    
    def chown(self, path: PathLike, owner: str, group: str) -> None:
        """修改文件或目录的所有者和组
        
        Args:
            path: 目标路径
            owner: 新的所有者
            group: 新的组
        """
        self.fs_ops.chown(path, owner, group)

    def list_dir(self, path: PathLike) -> List[str]:
        """列出目录内容
        
        Args:
            path: 目录路径
            
        Returns:
            List[str]: 目录下的文件和子目录名称列表
        """
        return self.fs_ops.list_dir(path)

    # 元数据操作
    def get_metadata(self, path: PathLike) -> Optional[FileMetadata]:
        """获取文件或目录的元数据
    
        Args:
            path: 目标路径
        
        Returns:
            Optional[FileMetadata]: 元数据对象，如果路径不存在则返回 None
        """
        return self.metadata.get(path)
    
    def _check_permission(self, path: PathLike, required_perm: Permission,
                         username: str = "root", groups: Set[str] = None) -> bool:
        """检查权限
        
        Args:
            path: 检查路径
            required_perm: 所需权限
            username: 用户名
            groups: 用户组列表
            
        Returns:
            bool: 是否有权限
            
        Raises:
            FileNotFoundError: 路径不存在
            PermissionError: 权限不足
        """
        metadata = self.get_metadata(path)
        if not metadata:
            raise FileNotFoundError(str(path))
            
        if not metadata.has_permission(username, groups or {"root"}, required_perm):
            raise PermissionError(
                str(path),
                str(required_perm),
                f"用户 {username} 没有足够权限"
            )
        return True

    def _check_path(self, path: PathLike) -> bool:
        """验证路径合法性"""
        try:
            path_str = str(path)
            if not path_str.startswith('/'):
                raise InvalidPathError(path_str, "必须使用绝对路径")
                
            # 检查路径中的非法字符
            invalid_chars = set('<>:"|?*\\')
            if any(c in path_str for c in invalid_chars):
                raise InvalidPathError(path_str, "包含非法字符")
                
            return True
        except Exception as e:
            raise InvalidPathError(str(path), str(e))

