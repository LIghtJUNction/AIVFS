from pathlib import Path
import sqlite3
from typing import Optional, cast, List
from datetime import datetime
from ..core.interfaces import IFSOperations
from ..core.types import FileMetadata, FileType, Permission

class MetadataManager:
    """元数据管理器"""
    
    def __init__(self, root: Path):
        self.root = root
        self.db_path = root / 'etc' / 'aivfs' / 'metadata.db'
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.fs_ops: Optional[IFSOperations] = None
        self._init_db()
    
    def set_fs_ops(self, fs_ops: IFSOperations) -> None:
        """设置文件系统操作实例"""
        self.fs_ops = fs_ops
    
    def _init_db(self):
        """初始化数据库"""
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

    def add_file(self, metadata: FileMetadata) -> None:
        """添加或更新文件元数据"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO metadata
                (path, type, owner, file_group, size, created_at, modified_at,
                 user_perm, group_perm, other_perm)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metadata.path,
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

    def get_file(self, path: str) -> Optional[FileMetadata]:
        """获取文件元数据，如果没有则继承父目录的元数据
        
        Args:
            path: 文件路径
            
        Returns:
            Optional[FileMetadata]: 文件的元数据，如果文件和所有父目录都不存在则返回None
        """
        with sqlite3.connect(self.db_path) as conn:
            # 首先尝试获取文件自身的元数据
            cursor = conn.execute(
                "SELECT * FROM metadata WHERE path = ?",
                (path,)
            )
            row = cursor.fetchone()
            
            if row:
                return self._create_metadata_from_row(row)
            
            # 如果没有找到，尝试获取父目录的元数据
            parent_path = str(Path(path).parent)
            if parent_path == '.':
                parent_path = '/'
                
            while parent_path != '/':
                cursor = conn.execute(
                    "SELECT * FROM metadata WHERE path = ?",
                    (parent_path,)
                )
                row = cursor.fetchone()
                
                if row:
                    # 基于父目录的元数据创建新的元数据
                    parent_meta = self._create_metadata_from_row(row)
                    real_path = self.root / path.lstrip('/')
                    
                    # 创建继承的元数据
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
                
                # 继续向上查找父目录
                parent_path = str(Path(parent_path).parent)
                if parent_path == '.':
                    parent_path = '/'
            
            # 如果找到根目录，使用默认root配置
            if parent_path == '/':
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

    def _create_metadata_from_row(self, row) -> FileMetadata:
        """从数据库行创建元数据对象
        
        Args:
            row: 数据库查询结果行
            
        Returns:
            FileMetadata: 元数据对象
        """
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

    def remove_file(self, path: str) -> None:
        """删除文件元数据"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM metadata WHERE path = ?", (path,))

    def close(self) -> None:
        """关闭数据库连接"""
        # SQLite会自动管理连接
        pass

    def list_dir(self, path: str) -> List[FileMetadata]:
        """列出目录下所有文件和子目录的元数据
        
        Args:
            path: 目录路径
            
        Returns:
            List[FileMetadata]: 目录下所有项目的元数据列表
        """
        # 规范化路径，确保以 / 结尾
        norm_path = path.rstrip('/') + '/'
        
        with sqlite3.connect(self.db_path) as conn:
            # 查询以该路径开头的所有直接子项
            cursor = conn.execute("""
                SELECT * FROM metadata 
                WHERE path LIKE ? || '%'
                AND path != ?
                AND path NOT LIKE ? || '%/%'
            """, (norm_path, norm_path, norm_path))
            
            results = []
            for row in cursor:
                metadata = FileMetadata(
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
                results.append(metadata)
                
            return results
