from pathlib import Path
import sqlite3
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime

from ..core.interfaces import IMetadataManager
from ..core.types import FileMetadata, FileType, Permission, PathLike
from ..core.exceptions import (
    DatabaseError, MetadataError, FileNotFoundError,
    InvalidPathError, FileExistsError
)

if TYPE_CHECKING:
    from ..core.fs_ops import FSOperations

class MetadataManager(IMetadataManager):
    """元数据管理器"""
    
    def __init__(self, root: Path):
        self.root = root
        self.db_path = root / 'etc' / 'aivfs' / 'metadata.db'
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.fs_ops = None
        self._init_db()

    def set_fs_ops(self, fs_ops: 'FSOperations') -> None:
        self.fs_ops = fs_ops

    def _init_db(self):
        """初始化数据库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS metadata (
                        path TEXT PRIMARY KEY,
                        type TEXT NOT NULL,
                        owner TEXT NOT NULL,
                        file_group TEXT NOT NULL,
                        size INTEGER,
                        created_at INTEGER NOT NULL,
                        modified_at INTEGER NOT NULL,
                        user_perm INTEGER NOT NULL,
                        group_perm INTEGER NOT NULL,
                        other_perm INTEGER NOT NULL
                    )
                """)
        except sqlite3.Error as e:
            raise DatabaseError(f"初始化数据库失败: {e}")
    
    def upsert(self, metadata: FileMetadata) -> None:
        """添加或更新元数据"""
        if not metadata.path:
            raise InvalidPathError("路径不能为空")
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO metadata
                    (path, type, owner, file_group, size, created_at, modified_at,
                     user_perm, group_perm, other_perm)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(metadata.path),
                    metadata.file_type.name,
                    metadata.owner,
                    metadata.group,
                    metadata.size,
                    int(metadata.created_at.timestamp()),
                    int(metadata.modified_at.timestamp()),
                    metadata.user_perm.to_mode(),
                    metadata.group_perm.to_mode(),
                    metadata.other_perm.to_mode()
                ))
        except sqlite3.IntegrityError:
            raise FileExistsError(str(metadata.path))
        except sqlite3.Error as e:
            raise DatabaseError(f"添加或更新元数据失败: {e}")
    
    def get(self, path: PathLike) -> Optional[FileMetadata]:
        """获取元数据，如果不存在则继承父目录元数据"""
        if not path:
            raise InvalidPathError("路径不能为空")
            
        path_str = str(path)
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT * FROM metadata WHERE path = ?",
                    (path_str,)
                )
                row = cursor.fetchone()
                
                if row:
                    return self._create_metadata_from_row(row)
                    
                # 继承父目录元数据
                parent_path = str(Path(path_str).parent)
                if parent_path == '.':
                    parent_path = '/'
                    
                while parent_path != '/':
                    cursor = conn.execute(
                        "SELECT * FROM metadata WHERE path = ?",
                        (parent_path,)
                    )
                    row = cursor.fetchone()
                    
                    if row:
                        return self._inherit_metadata(row, path_str)
                    
                    parent_path = str(Path(parent_path).parent)
                    if parent_path == '.':
                        parent_path = '/'
                
                # 使用根目录默认配置
                return self._create_default_metadata(path_str)
                
        except sqlite3.Error as e:
            raise DatabaseError(f"获取元数据失败: {e}")
        except OSError as e:
            raise MetadataError(f"获取元数据失败: {e}")
    
    def remove(self, path: PathLike) -> None:
        """删除元数据"""
        if not path:
            raise InvalidPathError("路径不能为空")
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM metadata WHERE path = ?", 
                    (str(path),)
                )
                if cursor.rowcount == 0:
                    raise FileNotFoundError(str(path))
        except sqlite3.Error as e:
            raise DatabaseError(f"删除元数据失败: {e}")
    
    def list_dir(self, path: PathLike) -> List[FileMetadata]:
        """列出目录内容的元数据"""
        if not path:
            raise InvalidPathError("路径不能为空")
            
        norm_path = str(path).rstrip('/') + '/'
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT * FROM metadata 
                    WHERE path LIKE ? || '%'
                    AND path != ?
                    AND path NOT LIKE ? || '%/%'
                """, (norm_path, norm_path, norm_path))
                
                return [self._create_metadata_from_row(row) for row in cursor]
        except sqlite3.Error as e:
            raise DatabaseError(f"列出目录内容失败: {e}")
    
    def exists(self, path: PathLike) -> bool:
        """检查是否存在元数据"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM metadata WHERE path = ?",
                (str(path),)
            )
            return cursor.fetchone()[0] > 0
    
    def _create_metadata_from_row(self, row) -> FileMetadata:
        """从数据库行创建元数据"""
        return FileMetadata(
            path=row[0],
            file_type=FileType[row[1]],
            owner=row[2],
            group=row[3],
            size=row[4],
            created_at=datetime.fromtimestamp(row[5]),
            modified_at=datetime.fromtimestamp(row[6]),
            user_perm=Permission.from_mode(row[7]),
            group_perm=Permission.from_mode(row[8]),
            other_perm=Permission.from_mode(row[9])
        )
    
    def _inherit_metadata(self, parent_row, path: str) -> FileMetadata:
        """基于父目录元数据创建继承的元数据"""
        real_path = self.root / path.lstrip('/')
        parent_meta = self._create_metadata_from_row(parent_row)
        
        return FileMetadata(
            path=path,
            file_type=FileType.DIRECTORY if real_path.is_dir() else FileType.REGULAR,
            owner=parent_meta.owner,
            group=parent_meta.group,
            size=real_path.stat().st_size if real_path.is_file() else None,
            created_at=datetime.fromtimestamp(real_path.stat().st_ctime),
            modified_at=datetime.fromtimestamp(real_path.stat().st_mtime),
            user_perm=parent_meta.user_perm,
            group_perm=parent_meta.group_perm,
            other_perm=parent_meta.other_perm
        )
    
    def _create_default_metadata(self, path: str) -> Optional[FileMetadata]:
        """创建默认的根目录元数据"""
        real_path = self.root / path.lstrip('/')
        if real_path.exists():
            return FileMetadata(
                path=path,
                file_type=FileType.DIRECTORY if real_path.is_dir() else FileType.REGULAR,
                owner="root",
                group="root",
                size=real_path.stat().st_size if real_path.is_file() else None,
                created_at=datetime.fromtimestamp(real_path.stat().st_ctime),
                modified_at=datetime.fromtimestamp(real_path.stat().st_mtime),
                user_perm=Permission.from_mode(7),
                group_perm=Permission.from_mode(5),
                other_perm=Permission.from_mode(5)
            )
        return None
    
    def _execute_query(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """执行数据库查询"""
        if not query:
            raise DatabaseError("查询语句不能为空")
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                return conn.execute(query, params)
        except sqlite3.Error as e:
            raise DatabaseError(f"数据库操作失败: {e}")